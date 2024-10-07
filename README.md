# Cafe Pos
# ติดตั้ง
pip install -r install.txt

# เข้าไปในโปรเจกต์
cd myposapp

# รันmysql
mysqld --console

# สร้าง ฐานข้อมูล
CREATE DATABASE POSDB CHARACTER SET utf8;

CREATE USER Got WITH PASSWORD '1234';

GRANT ALL PRIVILEGES ON POSDB.* TO 'Got'@'localhost';

SET GLOBAL transaction_isolation = 'READ-COMMITTED';

FLUSH PRIVILEGES;

# makemigrations
python manage.py makemigrations

python manage.py migrate

# โหลดข้อมูลเข้า
python manage.py load_xlsx -i myapp/fixtures/DATA.xlsx

ถ้าข้อมูลไม่เข้าให้ไปเพิ่มด้วยมือที่ admin เลยครับ http://127.0.0.1:8000/admin/

python manage.py createsuperuser
# รันtailwind
python manage.py tailwind start

python manage.py runserver
