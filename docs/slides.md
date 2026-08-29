---
title: "SFTP-Lite"
subtitle: "Project 1 — Socket Programming, CS351"
author: "Chissanupun Athiwarikanon"
---

## The problem

- ส่งไฟล์ให้ตัวเองผ่าน LINE/Messenger → **โดนบีบอัดคุณภาพ** (รูป/วิดีโอ) อัตโนมัติ
- ต้องพึ่งอินเทอร์เน็ต แม้ทั้งสองเครื่องอยู่ห้องเดียวกัน
- **SFTP-Lite**: ส่งไฟล์ raw bytes ตรงระหว่างเครื่องในวง LAN/WiFi เดียวกัน — ไม่บีบอัด ไม่ต้องเน็ต

## What it does

- **ระบบหลัก — File Transfer**: `STORE` / `GET` / `LIST` / `DELETE`
- **ระบบรอง — Discovery Beacon**: client หา server เจอเองในวง LAN โดยไม่ต้องรู้ IP ล่วงหน้า
- CLI จริง: `sftplite store/get/list/delete/discover`

## Transport — main system (File Transfer)

| มิติ | ความต้องการ | บังคับ? |
|---|---|---|
| **Data integrity** | ไฟล์ต้องไม่หาย/ไม่เพี้ยน | **บังคับ → TCP** |
| Timing | ไม่ time-sensitive | ไม่บังคับ |
| Throughput | Elastic | ไม่บังคับ |
| Security | ไม่มี (ตัดสินใจไว้ตั้งใจ) | ไม่บังคับ |

**มีแค่ integrity บังคับ → TCP**

## Transport — secondary system (Discovery)

| มิติ | ความต้องการ | บังคับ? |
|---|---|---|
| Data integrity | ทนการสูญหายได้ (ส่งซ้ำทุก 2s) | ไม่บังคับ |
| **โครงสร้างการสื่อสาร** | ต้อง broadcast แบบ one-to-many | **บังคับ → UDP** (TCP เป็น point-to-point ทำไม่ได้) |

**สองระบบ สองเหตุผล ไม่ใช่การเลือกไม่ถูก**

## Protocol session (mirrors SMTP: handshake → transfer → closure)

```
S: 220 SFTP-Lite ready

C: STORE <filename> <size>
S: 100 Continue | 400 Bad Request
C: <raw bytes>
S: 201 Stored | 500 Server Error

C: GET <filename>       → S: 200 OK <size> + bytes | 404 Not Found
C: LIST                 → S: 200 OK <count> + names
C: DELETE <filename>    → S: 200 OK Deleted | 404 Not Found
C: QUIT                 → S: 221 Closing
```

## Why `100 Continue`

- Naive design: client sends header, immediately streams file bytes
- If server rejects (`400`) **after** bytes are already sent → those bytes sit in the TCP stream, get misread as the next command → **session desync**
- Fix: client waits for `100 Continue` before sending any payload
- Protocol-level fix, not a patch

## Demo plan

1. Happy path: store → list → get → delete
2. `404` — get a missing file
3. `400` — driven by hand over raw TCP (`nc`), proves the protocol is genuinely line-based text
4. Partial-transfer discard — interrupt a large STORE, show no corrupt file left behind
5. Discovery beacon
