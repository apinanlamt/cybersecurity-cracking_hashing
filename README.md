# Password Cracking and Secure Hashing Lab

โปรเจกต์นี้เป็นเว็บสาธิตที่ใช้ **Python (Flask) เป็น backend** สำหรับคำนวณ hash, ทดลอง dictionary/brute-force และสร้าง salt ส่วน JavaScript ใช้ควบคุมแท็บ ส่งคำขอ และแสดงผลบนหน้าเว็บเท่านั้น ระหว่างทำงาน Flask จะ stream log แบบ NDJSON กลับมาเป็นเหตุการณ์ต่อเนื่อง แต่ละขั้นจึงแสดงลำดับและความคืบหน้าในหน้าเว็บได้โดยไม่ต้องรอผลลัพธ์สุดท้าย

## เริ่มใช้งาน

ต้องมี Python 3.9 ขึ้นไป จากโฟลเดอร์โปรเจกต์ให้ติดตั้ง dependency และเริ่ม server:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

จากนั้นเปิด <http://127.0.0.1:5000> ใน browser ตัว server bind เฉพาะ localhost สำหรับการนำเสนอในเครื่อง

## โครงสร้าง

- `app.py` — Flask routes และ logic การคำนวณฝั่ง Python
- `templates/index.html` — สไลด์สาธิต 4 ขั้น
- `static/css/styles.css` — รูปแบบหน้าเว็บ
- `static/js/app.js` — การโต้ตอบ รับ log ที่ stream มาจาก Python และแสดงผล โดยไม่มีการคำนวณ hash ฝั่ง browser
- `requirements.txt` — dependency ของ Python

แต่ละแท็บมี log panel ของตัวเอง แสดงเวลา เหตุการณ์เริ่ม/จบการคำนวณ จำนวน candidate ที่ลอง digest และผล match/mismatch โดย hash และการตรวจ candidate เกิดใน Python สำหรับ brute-force จะแสดงรายละเอียดราย candidate ไม่เกิน 2,000 รายการ แล้วเปลี่ยนเป็น log ความคืบหน้าเป็นช่วง เพื่อจำกัดปริมาณข้อมูลบนหน้าเว็บ

หน้าจอจัดตาม Low-Fi: หน้า 1–3 ใช้พื้นที่ทำงานเต็มความกว้างและความสูงของหน้าจอ โดยวางส่วนควบคุม/ผลลัพธ์ด้านซ้ายกับ Live Log ด้านขวา; หน้า 4 วางช่องทดลองกับผล hash 3 รอบสองคอลัมน์ และ Live Log เต็มความกว้างด้านล่าง หน้า Dictionary Attack เปิดรายการคำทั้งหมดใน Wordlist เป็น modal ก่อนเริ่มโจมตี

## ขอบเขตความปลอดภัย

- ใช้เฉพาะรหัสผ่านตัวอย่าง ห้ามกรอกรหัสผ่านจริง ข้อความที่กรอกจะถูกส่งจาก browser ไปยัง Python server บนเครื่องนี้
- Server ตั้งให้รับการเชื่อมต่อจาก localhost เท่านั้น และไม่บันทึกค่ารหัสผ่านลงไฟล์หรือฐานข้อมูล
- HTML, CSS และ JavaScript ที่ส่งไปยัง browser ยังเปิดดูได้ การแยกไฟล์ไม่ได้ซ่อนโค้ด แต่การคำนวณ hash หลักย้ายไปทำใน Python แล้ว
- MD5 และ SHA-1 แสดงเพื่อเปรียบเทียบทางการศึกษา ไม่ควรใช้เก็บรหัสผ่านจริง
- อัตรา GPU ในหน้าประมาณการเป็นตัวเลขประกอบการสอน ส่วนผล brute-force ขนาดเล็กคำนวณจริงด้วย Python บนเครื่องที่รัน server
- Flask development server นี้มีไว้สำหรับ localhost และการสาธิต ไม่ใช่การ deploy production
