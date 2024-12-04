# Cafe Pos
# ติดตั้ง
pip install -r install.txt

# เข้าไปในโปรเจกต์
cd myposapp

# makemigrations
python manage.py makemigrations

python manage.py migrate

# โหลดข้อมูลเข้า
python manage.py load_xlsx -i myapp/fixtures/DATA.xlsx

# รัน
python manage.py tailwind start

python manage.py runserver

