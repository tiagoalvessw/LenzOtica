import sys
sys.stdout.reconfigure(encoding="utf-8")
import db

tables = db.fetchall(
    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
)
print("Tabelas no banco:")
for t in tables:
    print(" -", t["table_name"])
