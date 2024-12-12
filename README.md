# Cafe Pos
# ติดตั้ง
pip install -r requirements.txt

# makemigrations
python manage.py makemigrations

python manage.py migrate

# โหลดข้อมูลเข้า
python manage.py load_xlsx -i myapp/fixtures/DATA.xlsx

# รัน
python manage.py runserver

