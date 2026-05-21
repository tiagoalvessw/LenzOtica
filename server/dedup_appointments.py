"""Remove agendamentos duplicados: mantém o mais recente por phone+date+time e cancela os eventos extra no Google Calendar."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from appointments import load, save
from calendar_service import cancel_event

def dedup():
    data = load()
    seen = {}
    to_cancel = []

    for apt in sorted(data, key=lambda a: a.get("created_at", "")):
        key = (apt["phone"], apt["date"], apt["time"])
        if key in seen:
            to_cancel.append(apt)
        else:
            seen[key] = apt

    if not to_cancel:
        print("Nenhum duplicado encontrado.")
        return

    for apt in to_cancel:
        eid = apt.get("event_id", "")
        if eid:
            try:
                cancel_event(eid)
                print(f"Evento Google Calendar removido: {eid}")
            except Exception as e:
                print(f"Erro ao remover evento {eid}: {e}")
        apt["status"] = "cancelled"

    save(data)
    print(f"\n{len(to_cancel)} duplicado(s) cancelado(s) e removido(s) do calendário.")

if __name__ == "__main__":
    dedup()
