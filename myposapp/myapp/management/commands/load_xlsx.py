import os
from django.apps import apps
from django.db.models import *
from django.core.management.base import BaseCommand
from openpyxl import load_workbook
from myapp.models import *


class Command(BaseCommand):
    help = '''Load data from an Excel file into the database.
    Usage: python manage.py load_xlsx -i myapp/fixtures/DATA.xlsx
    '''

    def add_arguments(self, parser):
        parser.add_argument('-i', '--input', type=str, required=True, help='Path to the Excel file')
        parser.add_argument('-s', '--skip_id', action='store_true', help='Skip ID fields in data loading')

    def handle(self, *args, **options):
        # Validate and load the Excel file
        xlsx_path = options['input']
        if not os.path.exists(xlsx_path):
            self.stderr.write(f"Error: File '{xlsx_path}' not found.")
            return

        try:
            workbook = load_workbook(xlsx_path)
            self.stdout.write(f"Loaded workbook: {xlsx_path}")
        except Exception as e:
            self.stderr.write(f"Error loading Excel file: {e}")
            return

        # Specify the models to load data for
        target_models = ['Member', 'Product']
        app_config = apps.get_app_config('myapp')

        for model_name in target_models:
            if model_name not in workbook.sheetnames:
                self.stdout.write(f"Sheet '{model_name}' not found in the Excel file. Skipping.")
                continue

            model = app_config.get_model(model_name)
            sheet = workbook[model_name]
            headers = None

            for row_index, row in enumerate(sheet.iter_rows(values_only=True), start=1):
                if row_index == 1:
                    # Set headers from the first row
                    headers = [col.lower() for col in row]
                    self.stdout.write(f"Headers for '{model_name}': {headers}")
                    continue

                # Map row data to model fields
                data = {headers[i]: row[i] for i in range(len(headers)) if headers[i] in [f.name for f in model._meta.fields]}
                if options['skip_id']:
                    data.pop('id', None)

                # Clean and prepare data for insertion
                data = {k: (v.strip() if isinstance(v, str) else v) for k, v in data.items()}

                # Handle special field types
                for field_name, value in data.items():
                    field = model._meta.get_field(field_name)
                    try:
                        if isinstance(field, (OneToOneField, ForeignKey)) and value:
                            data[field_name] = field.related_model.objects.get(id=int(value))
                        elif isinstance(field, (DateTimeField, DateField)) and value:
                            data[field_name] = value.isoformat()
                        elif isinstance(field, FileField) and value:
                            img_path = os.path.join('media', 'img', value)
                            data[field_name] = f"img/{value}" if os.path.exists(img_path) else None
                        elif isinstance(field, DecimalField) and value:
                            data[field_name] = float(value)
                    except Exception as e:
                        self.stderr.write(f"Error processing field '{field_name}' in '{model_name}': {e}")
                        data[field_name] = None

                # Determine the unique field for this model
                unique_field = None
                if model_name == "Member":
                    unique_field = 'username'
                elif model_name == "Product":
                    unique_field = 'product_name'

                if not unique_field or unique_field not in data or not data[unique_field]:
                    self.stderr.write(
                        f"Skipping row {row_index} in '{model_name}' due to missing or empty unique identifier.")
                    self.stderr.write(f"Raw data for row {row_index}: {data}")
                    continue

                # Create or update the model instance
                condition = {unique_field: data[unique_field]}
                try:
                    obj, created = model.objects.update_or_create(defaults=data, **condition)
                    action = 'Created' if created else 'Updated'
                    self.stdout.write(f"{action} {model_name}: {obj}")
                except Exception as e:
                    self.stderr.write(f"Error saving {model_name} (Row {row_index}): {e}")

        self.stdout.write("Data import completed.")
