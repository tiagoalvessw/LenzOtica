"""
Backfill: importa clientes existentes da tabela appointments para clients.

Regras:
  - Agrupa por phone — um cliente = um phone.
  - Ignora agendamentos sem phone.
  - Usa a data do agendamento mais recente como last_appointment_date.
  - Se o phone já existir em clients, apenas atualiza last_appointment_date.
  - Se não existir, cria o registro com first_name / last_name extraídos do nome.

Execute uma única vez:
    python backfill_clients.py
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import db
import clients as clients_mod


def run():
    # Busca o agendamento mais recente por phone (qualquer status)
    rows = db.fetchall(
        """
        SELECT DISTINCT ON (phone)
            phone,
            name,
            date
        FROM appointments
        WHERE phone IS NOT NULL AND phone <> ''
        ORDER BY phone, date DESC
        """
    )

    if not rows:
        print("Nenhum agendamento encontrado na tabela appointments.")
        return

    inserted = 0
    updated  = 0

    for row in rows:
        phone = str(row["phone"]).strip()
        name  = str(row["name"]).strip()
        date  = str(row["date"])[:10]   # garante "YYYY-MM-DD"

        if not phone:
            continue

        existing = db.fetchone(
            "SELECT id FROM clients WHERE phone = %s LIMIT 1", (phone,)
        )

        if existing:
            db.execute(
                "UPDATE clients SET last_appointment_date = %s, updated_at = NOW() WHERE id = %s",
                (date, existing["id"]),
            )
            print(f"  [ATUALIZADO] {phone} → {name} ({date})")
            updated += 1
        else:
            parts      = name.split(" ", 1)
            first_name = parts[0]
            last_name  = parts[1] if len(parts) > 1 else ""
            db.execute(
                """
                INSERT INTO clients (first_name, last_name, phone, last_appointment_date)
                VALUES (%s, %s, %s, %s)
                """,
                (first_name, last_name, phone, date),
            )
            print(f"  [INSERIDO]   {phone} → {name} ({date})")
            inserted += 1

    print(f"\nBackfill concluído: {inserted} inseridos, {updated} atualizados.")


if __name__ == "__main__":
    run()
