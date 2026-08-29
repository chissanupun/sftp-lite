# SFTP-Lite — Full Narration Script (per slide)

ใช้คู่กับ `slides.html` และ `presentation-run-order.md`. สคริปต์นี้คือคำพูดแบบเต็ม พูดตามได้เลย ไม่ต้องด้นสด — ปรับสำนวนให้เป็นธรรมชาติของตัวเองได้ตอนซ้อม

---

## Intro (ก่อนเปิดสไลด์, กล้องหน้าตัวเอง)

สวัสดีครับ ผมชิษณุพันธ์ วันนี้จะมาพรีเซนต์โปรเจกต์ Project 1 Socket Programming ชื่อว่า **SFTP-Lite** เป็น LAN file-transfer tool ที่ผมเขียนขึ้นเพื่อแก้ปัญหาจริงที่เจอเอง — ไม่ใช่แค่ทำตามโจทย์เฉยๆ

---

## Sheet 01/07 — Problem

ไอเดียนี้เริ่มจากเห็นเพื่อนใช้ Mac แล้วมี AirDrop กับ shared clipboard ที่ส่งไฟล์หรือ copy-paste ข้ามเครื่องได้ทันทีในวง WiFi เดียวกัน ผมใช้ Linux ไม่มีอะไรแบบนั้นให้ใช้เลย เวลาจะย้ายไฟล์รูปหรือวิดีโอจากมือถือไปโน้ตบุ๊ก ต้องพึ่งส่งผ่าน LINE หรือ Messenger ให้ตัวเอง ซึ่งแอปพวกนี้จะบีบอัดคุณภาพไฟล์ให้อัตโนมัติ ทั้งที่จริงๆ สองเครื่องอยู่ห้องเดียวกัน ต่อ WiFi วงเดียวกัน ไม่ควรต้องพึ่งอินเทอร์เน็ตหรือโดนบีบอัดอะไรเลย

**SFTP-Lite** คือคำตอบ — ส่งไฟล์แบบ raw bytes ตรงระหว่างเครื่องในวง LAN เดียวกัน ไม่บีบอัด ไม่ต้องเน็ต ไม่ต้องเสียบสาย แค่อยู่เน็ตเวิร์กเดียวกันก็พอ — เอาฟีลของ AirDrop มาทำเองบน Linux

---

## Sheet 02/07 — Scope

โปรแกรมนี้แบ่งเป็นสองระบบที่ทำงานร่วมกัน

ระบบหลักคือ **File Transfer** มีสี่คำสั่ง: `STORE` เก็บไฟล์ขึ้น server, `GET` ดึงไฟล์ลงมา, `LIST` ดูรายชื่อไฟล์ทั้งหมด, `DELETE` ลบไฟล์

ระบบรองคือ **Discovery Beacon** — ให้ client หา server เจอเองในวง LAN โดยไม่ต้องรู้ IP ล่วงหน้า คล้าย AirDrop

ทั้งหมดนี้ควบคุมผ่าน CLI จริง ไม่ใช่แค่สคริปต์ demo — พิมพ์ `sftplite store`, `sftplite get`, `sftplite list`, `sftplite delete`, `sftplite discover` ได้เลย

---

## Sheet 03/07 — Transport: Main system

ทีนี้มาดูว่าทำไมผมเลือก transport แต่ละแบบ ผมวิเคราะห์ตาม 4 มิติที่เรียนในวิชานี้: data integrity, timing, throughput, security

สำหรับ**การโอนไฟล์** — มิติที่บังคับทิศทางจริงๆ มีแค่ **data integrity** ไฟล์ต้องไม่หาย ไม่เพี้ยนแม้แต่ byte เดียว เพราะถ้า byte ผิดจุดเดียว ไฟล์อาจเปิดไม่ได้เลย ส่วน timing ไม่ time-sensitive เหมือนวิดีโอคอล, throughput เป็นแบบ elastic ทำงานได้ทั้งเน็ตช้าเร็ว, security ผมตัดสินใจไว้ตั้งใจว่าไม่ทำ encryption ระดับ protocol — เหมือน HTTP ธรรมดาที่ไม่มี TLS ไม่ใช่ลืมทำ

เพราะฉะนั้น มีแค่ integrity มิติเดียวที่บังคับ และมันบังคับไปทาง **TCP** เพราะ TCP รับประกัน reliable, in-order delivery

---

## Sheet 04/07 — Transport: Secondary system

ส่วน **discovery beacon** วิเคราะห์แยกกันเลย เพราะลักษณะงานต่างกันโดยสิ้นเชิง

data integrity ของ beacon ไม่บังคับ เพราะถ้า beacon ครั้งหนึ่งหายไป ไม่เป็นไร server จะส่งซ้ำทุก 2 วินาทีอยู่แล้ว client แค่รอรอบถัดไป

แต่มิติที่บังคับคือ**โครงสร้างการสื่อสาร** — server ต้องประกาศตัวไปยังทุกเครื่องในวง LAN พร้อมกัน โดยไม่รู้ล่วงหน้าว่ามี client กี่เครื่องอยู่ที่ไหน นี่คือ one-to-many broadcast ซึ่ง**TCP ทำไม่ได้โดยธรรมชาติของ protocol เอง** เพราะ TCP เป็น point-to-point ต้อง connect ไปยังปลายทางที่รู้ IP ล่วงหน้าเท่านั้น

เพราะฉะนั้นงานนี้บังคับไปทาง **UDP**

สรุปคือ SFTP-Lite ไม่ได้เลือกไม่ถูกระหว่าง TCP กับ UDP แต่มีสองงานย่อยที่มีลักษณะต่างกันจริง แต่ละงานเลือก transport ที่เหมาะกับตัวเองแยกกัน

---

## Sheet 05/07 — Protocol session

นี่คือหน้าตา session ทั้งหมดของ SFTP-Lite ออกแบบให้มีโครงสร้างแบบเดียวกับ SMTP ที่เรียนในคลาส คือ handshake ก่อน แล้วค่อย transfer แล้วจบด้วย closure

พอ client เชื่อมต่อ TCP มา server จะตอบ `220 SFTP-Lite ready` ทันที

ถ้า client ส่ง `STORE` พร้อมชื่อไฟล์กับขนาดไฟล์ server จะตอบ `100 Continue` ถ้า header ถูกต้อง หรือ `400 Bad Request` ถ้าผิด แล้ว client ค่อยส่ง raw bytes ตามมา จบด้วย `201 Stored` หรือถ้าเขียนไฟล์ไม่สำเร็จก็ `500 Server Error`

`GET` กับ `DELETE` ก็มี logic คล้ายกัน ตอบ `200 OK` พร้อมข้อมูล หรือ `404 Not Found` ถ้าไม่มีไฟล์

จบ session ด้วย `QUIT` แล้ว server ตอบ `221 Closing` ก่อนปิด connection

---

## Sheet 06/07 — Why 100 Continue

ตรงนี้คือจุดที่ผมคิดว่าน่าสนใจที่สุดของ protocol design — ทำไมต้องมี `100 Continue`

ถ้าออกแบบแบบไร้เดียงสา คือ client ส่ง header แล้วยิง payload ตามทันทีโดยไม่รอคำตอบ ปัญหาคือ ถ้า server เจอว่า header ผิด เช่นชื่อไฟล์มี `../` แล้วตอบ `400` ทันที แต่ client ส่ง payload ไปแล้วก่อนได้รับคำตอบ — bytes พวกนั้นจะยังค้างอยู่ใน TCP stream และถูกตีความผิดเป็นคำสั่งถัดไป ทำให้ session พังทั้งหมด เรียกว่า session desync

วิธีแก้คือบังคับให้ client รอ `100 Continue` จาก server ก่อนเสมอ ถึงจะส่ง payload ได้ นี่คือ protocol-level fix ที่แก้ปัญหาตั้งแต่ระดับการออกแบบ ไม่ต้องมาแก้ implementation ทีหลัง

---

## Sheet 07/07 — Demo plan

ต่อไปจะโชว์ demo สดห้าอย่าง

หนึ่ง happy path เต็มรูปแบบ — store, list, get, delete

สอง โชว์ `404` ตอน get ไฟล์ที่ไม่มีอยู่จริง

สาม โชว์ `400` โดยพิมพ์เองผ่าน raw TCP ด้วย `nc` ไม่ผ่าน client โปรแกรม — เพื่อพิสูจน์ว่า protocol นี้เป็น line-based text จริงๆ ไม่ใช่แค่ client ตัวเองที่คุยได้

สี่ โชว์ partial-transfer discard — ผมจะ interrupt การ STORE ไฟล์ใหญ่กลางทาง แล้วโชว์ว่าไม่มีไฟล์เสียค้างอยู่บน server

ห้า โชว์ discovery beacon ทำงานจริงในวง LAN

---

## Wrap (ปิดท้าย, กล้องหน้าตัวเอง)

สรุปคือ SFTP-Lite ใช้สอง transport สำหรับสองงานที่มีเหตุผลรองรับแยกกันชัดเจน และ protocol design ทั้งหมดพิสูจน์ได้จริง ทั้งผ่าน client ที่เขียนเอง และมือเปล่าผ่าน raw TCP ขอบคุณครับ
