import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
import db


def run():
    print("[MIGRATE BOT] Iniciando...")

    # 1. Tabela bot_config (1 linha única)
    db.execute("""
        CREATE TABLE IF NOT EXISTS bot_config (
            id               SERIAL      PRIMARY KEY,
            store_name       TEXT        NOT NULL DEFAULT '',
            store_address    TEXT        NOT NULL DEFAULT '',
            store_phone      TEXT        NOT NULL DEFAULT '',
            store_services   TEXT        NOT NULL DEFAULT '',
            store_notes      TEXT        NOT NULL DEFAULT '',
            bot_name         TEXT        NOT NULL DEFAULT '',
            bot_tone         TEXT        NOT NULL DEFAULT 'informal',
            bot_personality  TEXT        NOT NULL DEFAULT '',
            bot_greeting     TEXT        NOT NULL DEFAULT '',
            bot_extra_rules  TEXT        NOT NULL DEFAULT '',
            updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    exists = db.fetchval("SELECT COUNT(*) FROM bot_config")
    if not exists:
        db.execute("""
            INSERT INTO bot_config
                (store_name, store_address, store_phone, store_services, store_notes,
                 bot_name, bot_tone, bot_personality, bot_greeting, bot_extra_rules)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            "LenzÓtica",
            "Rua Vereador Arthur Manoel Mariano, 362, Forquilhinhas, São José - SC (ao lado do cartório)",
            "(48) 3375-2050",
            "Exame de vista gratuito, venda de óculos, lentes de contato e armações",
            "Estamos ao lado do cartório, em frente ao prédio comercial marrom",
            "Liza",
            "informal",
            "Simpática e acolhedora. Usa o nome do cliente quando sabe. Mensagens curtas e objetivas.",
            "Me chamo Liza, como posso ajudá-lo?",
            "Nunca use emojis\nNunca se identifique como robô ou IA",
        ))
        print("[MIGRATE BOT] bot_config criada com valores padrão LenzÓtica")
    else:
        print("[MIGRATE BOT] bot_config já existe, pulando")

    # 2. Tabela faq_items
    db.execute("""
        CREATE TABLE IF NOT EXISTS faq_items (
            id         SERIAL      PRIMARY KEY,
            question   TEXT        NOT NULL,
            answer     TEXT        NOT NULL,
            is_active  BOOLEAN     NOT NULL DEFAULT true,
            sort_order INT         NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    faq_count = db.fetchval("SELECT COUNT(*) FROM faq_items")
    if not faq_count:
        examples = [
            ("Vocês aceitam convênio?",
             "Atendemos particulares, mas o exame de vista é totalmente gratuito! Não precisa de convênio.",
             0),
            ("Quanto tempo demora para ficar pronto os óculos?",
             "Em média 5 a 7 dias úteis após a aprovação do pedido. Avisamos assim que estiver pronto!",
             1),
            ("Posso levar a receita sem fazer o exame aqui?",
             "Sim, claro! Se você já tem receita, pode trazer e a gente faz o orçamento das lentes e armações.",
             2),
        ]
        for q, a, order in examples:
            db.execute(
                "INSERT INTO faq_items (question, answer, sort_order) VALUES (%s,%s,%s)",
                (q, a, order),
            )
        print("[MIGRATE BOT] 3 FAQs de exemplo inseridos")
    else:
        print("[MIGRATE BOT] faq_items já existe, pulando")

    # 3. Monta e salva o prompt a partir da nova estrutura
    import prompt_builder
    prompt_builder.build_and_save_prompt()
    print("[MIGRATE BOT] Prompt montado e salvo em rag_config.system_prompt")

    print("[MIGRATE BOT] Concluído!")


if __name__ == "__main__":
    run()
