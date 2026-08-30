# SFTP-Lite

LAN file-transfer tool (STORE/GET/LIST/DELETE over TCP + UDP discovery beacon).
Project 1, CS351 Computer Communications.

- [Design doc (PDF)](docs/design.pdf)
- [Slides](docs/slides.pptx)
- [Video demo (Canva)](https://canva.link/gq620m4se5ox1t9)

## Run

```bash
python3 src/server.py
python3 src/client.py store <file>
python3 src/client.py get <file> --out <dest>
python3 src/client.py list
python3 src/client.py delete <file>
python3 src/client.py discover
```
