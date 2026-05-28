"""
Módulo de CRUD para a tabela clients.
"""
from datetime import date as _date
import db


def _row(row: dict) -> dict:
    if row is None:
        return None
    r = dict(row)
    for f in ("last_appointment_date", "return_date", "birth_date"):
        if r.get(f) is not None:
            r[f] = str(r[f])
    for f in ("created_at", "updated_at"):
        if r.get(f) is not None:
            r[f] = r[f].isoformat()
    return r


def load() -> list[dict]:
    return [_row(r) for r in db.fetchall(
        """
        SELECT c.*,
               COUNT(a.id) FILTER (WHERE a.status IN ('attended','completed')) AS visit_count
        FROM clients c
        LEFT JOIN appointments a ON a.phone = c.phone
        GROUP BY c.id
        ORDER BY c.created_at DESC
        """
    )]


def get_by_id(client_id: int) -> dict | None:
    row = db.fetchone("SELECT * FROM clients WHERE id = %s", (client_id,))
    return _row(row) if row else None


def add_client(
    first_name: str,
    last_name: str,
    phone: str = "",
    last_appointment_date: str | None = None,
    notes: str = "",
    return_date: str | None = None,
    return_period_months: int | None = None,
    birth_date: str | None = None,
) -> int:
    return db.fetchval(
        """
        INSERT INTO clients
            (first_name, last_name, phone, last_appointment_date,
             notes, return_date, return_period_months, birth_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            first_name,
            last_name,
            phone,
            last_appointment_date or None,
            notes,
            return_date or None,
            return_period_months,
            birth_date or None,
        ),
    )


def update_client(
    client_id: int,
    first_name: str,
    last_name: str,
    phone: str = "",
    last_appointment_date: str | None = None,
    notes: str = "",
    return_date: str | None = None,
    return_period_months: int | None = None,
    birth_date: str | None = None,
) -> None:
    db.execute(
        """
        UPDATE clients SET
            first_name            = %s,
            last_name             = %s,
            phone                 = %s,
            last_appointment_date = %s,
            notes                 = %s,
            return_date           = %s,
            return_period_months  = %s,
            birth_date            = %s,
            updated_at            = NOW()
        WHERE id = %s
        """,
        (
            first_name,
            last_name,
            phone,
            last_appointment_date or None,
            notes,
            return_date or None,
            return_period_months,
            birth_date or None,
            client_id,
        ),
    )


def delete_client(client_id: int) -> None:
    db.execute("DELETE FROM clients WHERE id = %s", (client_id,))


def upsert_from_appointment(phone: str, name: str, appointment_date: str) -> None:
    """Registra o cliente ao agendar ou atualiza last_appointment_date se já existe.

    - Se `phone` estiver vazio, ignora (não há como identificar o cliente).
    - Divide `name` em first_name / last_name pelo primeiro espaço.
    - Se já existir um registro com o mesmo phone, apenas atualiza a data da última consulta.
    """
    if not phone:
        return

    parts = name.strip().split(" ", 1)
    first_name = parts[0]
    last_name  = parts[1] if len(parts) > 1 else ""

    existing = db.fetchone(
        "SELECT id FROM clients WHERE phone = %s LIMIT 1", (phone,)
    )
    if existing:
        db.execute(
            "UPDATE clients SET last_appointment_date = %s, updated_at = NOW() WHERE id = %s",
            (appointment_date, existing["id"]),
        )
    else:
        db.execute(
            """
            INSERT INTO clients (first_name, last_name, phone, last_appointment_date)
            VALUES (%s, %s, %s, %s)
            """,
            (first_name, last_name, phone, appointment_date),
        )


def get_return_stats() -> dict:
    """Retorna métricas de retorno para o painel."""
    row = db.fetchone(
        """
        SELECT
            COUNT(*)                                                                   AS total,
            COUNT(*) FILTER (WHERE created_at >= date_trunc('month', CURRENT_DATE))   AS new_this_month,
            COUNT(*) FILTER (WHERE return_date IS NOT NULL
                               AND return_date < CURRENT_DATE)                         AS overdue,
            COUNT(*) FILTER (WHERE return_date >= CURRENT_DATE
                               AND return_date <= CURRENT_DATE + INTERVAL '30 days')   AS upcoming
        FROM clients
        """
    )
    return dict(row) if row else {"total": 0, "new_this_month": 0, "overdue": 0, "upcoming": 0}
