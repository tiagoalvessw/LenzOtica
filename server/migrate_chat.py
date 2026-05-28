"""
Migracao chat: adiciona suporte ao Chat Cliente no painel.
Execute uma vez: python migrate_chat.py
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)
import psycopg

DATABASE_URL = os.getenv("DATABASE_URL")

SQL_STEPS = [
    # 1. Coluna para identificar mensagens enviadas pelo operador manualmente
    ("sent_by_operator column",
     """
     ALTER TABLE conversation_history
     ADD COLUMN IF NOT EXISTS sent_by_operator BOOLEAN DEFAULT FALSE;
     """),

    # 2. Tabela para controle de leitura por contato
    ("chat_read_status table",
     """
     CREATE TABLE IF NOT EXISTS chat_read_status (
         phone TEXT PRIMARY KEY,
         last_read_at TIMESTAMPTZ DEFAULT NOW()
     );
     """),

    # 3. Tabela para controle de modo IA por contato
    ("chat_ia_mode table",
     """
     CREATE TABLE IF NOT EXISTS chat_ia_mode (
         phone TEXT PRIMARY KEY,
         ia_enabled BOOLEAN DEFAULT TRUE,
         updated_at TIMESTAMPTZ DEFAULT NOW()
     );
     """),
]

if __name__ == "__main__":
    print(f"Conectando em: {DATABASE_URL}\n")
    with psycopg.connect(DATABASE_URL) as conn:
        for name, sql in SQL_STEPS:
            try:
                conn.execute(sql)
                conn.commit()
                print(f"  OK: {name}")
            except Exception as e:
                print(f"  ERRO: {name}: {e}")
    print("\nMigracao de chat concluida.")
