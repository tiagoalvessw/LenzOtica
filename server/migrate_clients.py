"""
Migração: Cria a tabela clients para o módulo de cadastro de clientes.
Execute uma vez: python migrate_clients.py
"""
import os
from dotenv import load_dotenv
import psycopg

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)
DATABASE_URL = os.getenv("DATABASE_URL")

DDL = """
CREATE TABLE IF NOT EXISTS clients (
    id                    SERIAL       PRIMARY KEY,
    first_name            VARCHAR(100) NOT NULL,
    last_name             VARCHAR(100) NOT NULL DEFAULT '',
    phone                 VARCHAR(50)  NOT NULL DEFAULT '',
    last_appointment_date DATE,
    notes                 TEXT         NOT NULL DEFAULT '',
    return_date           DATE,
    return_period_months  INT,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clients_phone       ON clients(phone);
CREATE INDEX IF NOT EXISTS idx_clients_return_date ON clients(return_date);
CREATE INDEX IF NOT EXISTS idx_clients_created_at  ON clients(created_at);
"""

if __name__ == "__main__":
    print(f"Conectando em: {DATABASE_URL}\n")
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(DDL)
        conn.commit()
    print("Tabela 'clients' criada (ou já existia). Migração concluída.")
