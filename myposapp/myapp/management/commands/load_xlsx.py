import os, traceback
from django.apps import apps
from django.db.models import *
from django.core.management.base import BaseCommand, CommandError
from openpyxl import load_workbook
from myapp.models import *


class Command(BaseCommand):
    help = '''โหลดข้อมูลจาก xlsx
    python manage.py load_xlsx -i myapp/fixtures/DATA.xlsx
    '''

    def add_arguments(self, parser):
        parser.add_argument('-i', '--input', type=str, default='myapp/fixtures/DATA.xlsx')
        parser.add_argument('-s', '--skip_id', type=bool, default=False)

    def handle(self, *args, **options):
        # กำหนดไฟล์ที่ต้องการอ่านข้อมูล
        if options['input']:
            xlsx = options['input']

        # โหลดไฟล์ Excel
        try:
            wb = load_workbook(xlsx)
            print(f"Loaded workbook: {xlsx}")
        except Exception as e:
            print(f"Error loading Excel file: {str(e)}")
            return

        # กำหนดโมเดลที่ต้องการโหลดข้อมูล
        models = ['Member', 'Product']
        app = apps.get_app_config('myapp')

        for name in models:
            print(f'Loading data for {name}')
            # ตรวจสอบว่า sheet ใน Excel มีข้อมูลโมเดลนั้นหรือไม่
            if name not in wb.sheetnames:
                print(f"Sheet {name} not found in {xlsx}")
                continue

            # ดึงข้อมูลโมเดล
            m = app.get_model(name)
            fields = [f.name for f in m._meta.fields]
            keys = []

            # เริ่มการอ่านข้อมูลในแต่ละแถวของ Sheet
            sheet = wb[name]
            for row_index, row in enumerate(sheet.iter_rows(values_only=True), start=1):
                print(f"Row {row_index}: {row}")

                # กำหนดหัวคอลัมน์ในแถวแรก
                if row_index == 1:  # กำหนดหัวคอลัมน์จากแถวแรก
                    keys = [key.lower() for key in row]  # ปรับชื่อคีย์ให้เป็นตัวพิมพ์เล็กทั้งหมด
                    print(f"Headers: {keys}")
                else:
                    # สร้าง dictionary สำหรับเก็บข้อมูลในแต่ละแถว
                    data = dict((keys[i], row[i]) for i in range(len(keys)) if keys[i] in fields)
                    if options['skip_id']:
                        data.pop('id', 0)

                    # ลบช่องว่างหรืออักขระพิเศษในฟิลด์ข้อมูล
                    data = {k: (v.strip() if isinstance(v, str) else v) for k, v in data.items()}

                    # ตรวจสอบข้อมูลก่อนดำเนินการใดๆ
                    print(f"Parsed Data (Before Processing): {data}")

                    # จัดการฟิลด์ต่างๆ ตามประเภทของข้อมูล
                    for k, value in data.items():
                        field = m._meta.get_field(k)
                        try:
                            if type(field) in [OneToOneField, ForeignKey] and value is not None:
                                # กรณีฟิลด์ความสัมพันธ์ (relationship)
                                data[k] = field.related_model.objects.get(id=int(value))
                            elif type(field) == DateTimeField and value is not None:
                                # กรณีฟิลด์วันเวลา
                                data[k] = value.isoformat()
                            elif type(field) == DateField and value is not None:
                                # กรณีฟิลด์วันที่
                                data[k] = f'{value.year:04}-{value.month:02}-{value.day:02}'
                            elif type(field) == FileField and value is not None:
                                # กรณีฟิลด์รูปภาพ (FileField หรือ ImageField)
                                img_path = os.path.join('media', 'img', value)
                                if os.path.exists(img_path):
                                    data[k] = f"img/{value}"  # ตั้งค่า path ของรูปภาพตามที่ระบบ Django กำหนด
                                else:
                                    print(f"Image not found: {img_path}")
                                    data[k] = None  # หรือสามารถตั้งค่า default ได้
                            elif type(field) == DecimalField and value is not None:
                                # กรณีฟิลด์ราคาที่เป็นตัวเลขทศนิยม
                                try:
                                    data[k] = float(value)
                                except ValueError:
                                    print(f"Error converting field {k} to float: {value}")
                                    data[k] = None
                        except Exception as e:
                            print(f"Error in field {k}: {str(e)}")
                            del data[k]

                    # ตรวจสอบข้อมูลหลังจัดการฟิลด์
                    print(f"Parsed Data (After Processing): {data}")

                    # ใช้ update_or_create แทน get_or_create พร้อมกำหนดเงื่อนไขที่แน่นอน
                    try:
                        # แก้ปัญหาการใช้เงื่อนไขที่ไม่เหมาะสมใน update_or_create
                        if 'product_name' in data and data['product_name']:  # แก้จาก product_Name เป็น product_name
                            condition = {'product_name': data['product_name']}
                        elif 'username' in data and data['username']:
                            condition = {'username': data['username']}
                        else:
                            print(f"Skipping row due to missing identifier field or empty value: {data}")
                            continue

                        print(f"Data to insert/update: {data}")
                        obj, created = m.objects.update_or_create(defaults=data, **condition)
                        if created:
                            print(f'Created {obj}')
                        else:
                            print(f'Updated {obj}')
                    except MultipleObjectsReturned:
                        print(f"Multiple entries found for {name} with {data}. Please check your data.")
                    except Exception as e:
                        print(f"Error in creating/updating {name}: {e}")

        # แสดงสถานะเมื่อสิ้นสุดการดำเนินการ
        print("Data import completed.")
