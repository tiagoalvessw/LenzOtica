"""
Adiciona coluna reminder_sent_at à tabela appointments.
Execute uma vez: python migrate_reminder_timeout.py
"""
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

import psycopg

DATABASE_URL = os.getenv("DATABASE_URL")

if __name__ == "__main__":
    print(f"Conectando em: {DATABASE_URL}\n")
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute("""
            ALTER TABLE appointments
            ADD COLUMN IF NOT EXISTS reminder_sent_at TIMESTAMPTZ;
        """)
        conn.commit()
        print("Coluna reminder_sent_at adicionada (ou já existia).")
    print("Migração concluída.")
