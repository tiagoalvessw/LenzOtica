"""
Migração v2: adiciona coluna birth_date à tabela clients.
Execute uma vez: python migrate_clients_v2.py
"""
import os
from dotenv import load_dotenv
import psycopg

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)
DATABASE_URL = os.getenv("DATABASE_URL")

DDL = """
ALTER TABLE clients ADD COLUMN IF NOT EXISTS birth_date DATE;
"""

if __name__ == "__main__":
    print(f"Conectando em: {DATABASE_URL}\n")
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(DDL)
        conn.commit()
    print("Coluna 'birth_date' adicionada (ou já existia). Migração concluída.")
