# SFTP-Lite — Video Run Order (08-29 recording)

**Target: ≤15 min.** ก่อนกดอัด: server รันอยู่แล้ว, terminal 2 บาน (server log + client) วางเรียงให้เห็นทั้งคู่บนจอเดียว, ไฟล์ใหญ่ (50–100MB) staged ไว้ในโฟลเดอร์ demo แล้ว.

## 1. เปิดกล้อง หน้าตัวเอง — พูดก่อนเปิดอะไรเลย (0:00–0:30)
ชื่อ → "SFTP-Lite" → หนึ่งประโยค: LAN file-transfer tool แก้ปัญหา LINE/Messenger บีบอัดไฟล์ตอนส่งให้ตัวเอง

## 2. เปิด `docs/slides.html` (fullscreen browser) (0:30–3:30)
เดินตาม 7 สไลด์ตามลำดับ:
1. ปัญหา
2. ทำอะไร (STORE/GET/LIST/DELETE + discovery)
3. ตาราง TCP (main system) → เน้น: "มีแค่ integrity บังคับ → TCP"
4. ตาราง UDP (discovery) → เน้น: "โครงสร้างการสื่อสาร บังคับ → UDP"
5. protocol session diagram (S:/C: transcript)
6. ทำไมต้อง `100 Continue`
7. demo plan

พูดชัดตรงสไลด์ 3–4: สองระบบ สองเหตุผลแยกกัน ไม่ใช่เลือกไม่ถูกระหว่าง TCP/UDP

## 3. สลับไปโค้ด — editor/terminal (3:30–8:30)
- `protocol.py` — ชี้ `ConnBuffer`, พูดประโยคนี้ตรงๆ: *"TCP has no message boundaries, so this loops until size_bytes."*
- `server.py` — ชี้ `100 Continue` handshake ใน `handle_store`, อธิบาย bug ที่ป้องกัน (session desync)
- ชี้ partial-transfer discard code
- ชี้ path traversal guard (`safe_filename` — reject `/`, `..`, `\x00`)

## 4. Live demo — terminal, server + client คนละหน้าต่าง (8:30–13:30)
1. Happy path: `store` → `list` → `get` → `delete`, narrate `>>`/`<<` protocol lines ที่ scroll
2. `get missing.txt` → 404
3. เปิด `nc 127.0.0.1 5050` พิมพ์เอง → โชว์ `400` (verified: `STORE ../etc/passwd 10` + `FOO bar` + `QUIT` → `400`×2 + `221`)
4. STORE ไฟล์ใหญ่ → Ctrl+C ฝั่ง **client** กลางทาง → `list` โชว์ไม่มี `.partial` ค้าง (อย่า kill server ฝั่งเดียว — cleanup code รันแค่ตอน client disconnect)
5. `sftplite discover` — ถ้าหาเครื่องที่สองไม่เจอ พูดสาเหตุที่เป็นไปได้ (AP/client isolation) ไว้เผื่อ

## 5. ปิดท้าย (13:30–14:30)
สรุปประโยคเดียว: สองทรานสปอร์ต สองเหตุผลที่มีหลักฐานรองรับ, protocol พิสูจน์ผ่านทั้ง CLI และมือเปล่าผ่าน raw TCP

---
Source: video script เต็มอยู่ใน [[Project1-Socket-Programming]] (vault) — ไฟล์นี้คือ run order แบบสั้น ใช้เช็คระหว่างอัดจริง
