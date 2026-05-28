import sys
sys.stdout.reconfigure(encoding="utf-8")
import db

row = db.fetchone("SELECT store_name, store_address, store_phone FROM bot_config LIMIT 1")
if row:
    print("Nome da loja :", row["store_name"])
    print("Endereco     :", row["store_address"])
    print("Telefone     :", row["store_phone"])
else:
    print("Nenhuma configuracao encontrada.")
