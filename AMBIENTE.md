# Documentação de Ambiente — LenzOtica

## 1. Histórico de Alterações

### 1.1 Correção de BOM no `.env`
**Arquivo:** `server/.env`  
**Problema:** BOM UTF-8 (`\xef\xbb\xbf`) fazia o `python-dotenv` ler as chaves com caractere invisível extra.  
**Correção:** Arquivo reescrito sem BOM com `encoding='utf-8'` explícito.

```python
with open('server/.env', 'rb') as f:
    raw = f.read()
print('BOM presente!' if raw.startswith(b'\xef\xbb\xbf') else 'OK — sem BOM')
```

### 1.2 `load_dotenv` com `override=True`
**Arquivo:** `server/ai.py`  
**Motivo:** Garante que variáveis do `.env` sobrescrevem o ambiente do sistema operacional.

### 1.3 Diagnóstico: `localhost` vs `127.0.0.1` no Windows
No Windows, `localhost` pode resolver para `::1` (IPv6) enquanto o uvicorn escuta em `127.0.0.1` (IPv4). Usar sempre `--host 0.0.0.0` ou acessar via `127.0.0.1`.

### 1.4 Migração para PostgreSQL + pgvector
Os três arquivos JSON foram substituídos por tabelas no banco:

| Antes | Depois |
|---|---|
| `server/appointments.json` | tabela `appointments` |
| `server/sessions.json` | tabela `conversation_history` |
| `server/pending.json` | tabela `pending_items` |

Arquivos adicionados:
- `db/init.sql` — schema completo (executado automaticamente pelo Docker)
- `server/db.py` — pool de conexões (`psycopg_pool`, min=1 max=5)
- `server/migrate.py` — migração única dos JSONs para o banco (já executada)

Arquivos atualizados: `appointments.py`, `ai.py`, `pending.py`, `docker-compose.yml`

Dependências adicionadas: `psycopg[binary]`, `psycopg-pool`

---

## 2. Divisão dos Ambientes

| Aspecto | Desenvolvimento (Local) | Produção |
|---|---|---|
| `USE_LOCAL_LLM` | `true` | `false` |
| Motor de IA | Ollama (`qwen2.5:7b`) | Groq API (`llama-3.3-70b-versatile`) |
| `GROQ_API_KEY` | Não necessário | Obrigatório |
| Evolution API | Opcional | Obrigatório |
| PostgreSQL | `lenz-postgres` (Docker, porta 5433) | Igual |
| WhatsApp real | Não conectado | Conectado |

---

## 3. Estado atual do `server/.env`

```env
GROQ_API_KEY=...
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=lenz-otica-key-2024
EVOLUTION_INSTANCE=lenz-otica
CALENDAR_EMBED_URL=https://calendar.google.com/calendar/embed?src=...
ADMIN_TOKEN=lenzotica-admin-2024
USE_LOCAL_LLM=false
DATABASE_URL=postgresql://lenz:lenz-pg-2024@localhost:5433/lenzdb
```

> Em desenvolvimento, troque `USE_LOCAL_LLM` para `true` e certifique-se de que o Ollama está rodando.

---

## 4. Como Iniciar Cada Ambiente

### 4.1 Desenvolvimento (Local com Ollama)

```powershell
# 1. Subir o banco (obrigatório em ambos os ambientes)
cd "C:\Users\PC-Tiago\Documents\First Project\lenz-otica"
docker compose up -d postgres-lenz

# 2. Baixar o modelo Ollama (só na primeira vez)
ollama pull qwen2.5:7b

# 3. Confirmar que o Ollama está rodando
ollama list

# 4. Definir USE_LOCAL_LLM=true no .env

# 5. Subir o servidor
cd server
python -m uvicorn main:app --reload --host 0.0.0.0
```

**Acessos:**
- Painel administrativo: `http://127.0.0.1:8000/painel`
- Documentação da API: `http://127.0.0.1:8000/docs`

**O que funciona sem Evolution API:**
- Painel (visualizar, criar, editar, cancelar agendamentos)
- Google Calendar (se `credentials.json` e `token.json` estiverem válidos)
- Lógica de IA (testável via `/docs`)

**O que NÃO funciona sem Evolution API:**
- Receber/enviar mensagens WhatsApp reais
- Lembretes automáticos (scheduler roda, mas as requisições falham silenciosamente)

---

### 4.2 Produção (Groq + Evolution API + WhatsApp)

```powershell
# 1. Subir todos os containers
cd "C:\Users\PC-Tiago\Documents\First Project\lenz-otica"
docker compose up -d

# 2. Verificar containers rodando
docker ps
# Esperado: lenz-postgres, evolution-postgres, evolution-api

# 3. Garantir USE_LOCAL_LLM=false no .env

# 4. Subir o servidor Python
cd server
python -m uvicorn main:app --reload --host 0.0.0.0

# 5. Abrir túnel ngrok (em outro terminal)
ngrok http 8000

# 6. Configurar webhook na Evolution API
# http://localhost:8080 → Instância → Settings → Webhook
# URL: https://xxxx.ngrok-free.app/webhook

# 7. Conectar WhatsApp via QR Code
```

**Acessos:**
- Evolution API: `http://localhost:8080`
- Painel administrativo: `http://127.0.0.1:8000/painel`
- Webhook: `https://xxxx.ngrok-free.app/webhook`

---

## 5. Banco de Dados

### Containers PostgreSQL

| Container | Porta | Banco | Uso |
|---|---|---|---|
| `lenz-postgres` | 5433 | `lenzdb` | Painel, IA, RAG, histórico |
| `evolution-postgres` | interna | `evolution` | Evolution API (WhatsApp) |

### Verificações rápidas do banco

```powershell
# Listar tabelas
docker exec -it lenz-postgres psql -U lenz -d lenzdb -c "\dt"

# Contar agendamentos
docker exec -it lenz-postgres psql -U lenz -d lenzdb -c "SELECT count(*) FROM appointments;"

# Contar histórico de conversas
docker exec -it lenz-postgres psql -U lenz -d lenzdb -c "SELECT count(*) FROM conversation_history;"

# Verificar pgvector
docker exec -it lenz-postgres psql -U lenz -d lenzdb -c "SELECT extname, extversion FROM pg_extension WHERE extname='vector';"

# Testar conexão Python
cd "C:\Users\PC-Tiago\Documents\First Project\lenz-otica\server"
python -c "import db; print('OK:', db.fetchval('SELECT count(*) FROM appointments'), 'agendamentos')"
```

### Recriar o banco do zero

Se precisar recriar o banco (perde todos os dados):

```powershell
docker compose down -v          # apaga volumes
docker compose up -d postgres-lenz
# O init.sql é executado automaticamente na primeira subida
```

---

## 6. Verificações Rápidas

### Checar se o .env está sendo lido corretamente

```powershell
cd "C:\Users\PC-Tiago\Documents\First Project\lenz-otica\server"
python -c "from dotenv import load_dotenv; import os; load_dotenv('.env', override=True); print(os.getenv('DATABASE_URL'))"
```

### Testar se o painel responde

```powershell
python -c "import urllib.request; r = urllib.request.urlopen('http://127.0.0.1:8000/painel', timeout=5); print('Painel OK:', r.status)"
```

### Rodar validação completa do sistema

```powershell
cd "C:\Users\PC-Tiago\Documents\First Project\lenz-otica\server"
python -c "
import db, appointments, pending, ai
print('DB OK:', db.fetchval('SELECT count(*) FROM appointments'), 'agendamentos')
print('Sessions:', len(ai.sessions), 'telefones carregados')
print('Pending:', len(pending.load()), 'pendencias')
"
```

---

## 7. Arquivos Sensíveis (nunca versionar)

| Arquivo | Conteúdo |
|---|---|
| `server/.env` | Chaves de API, tokens e `DATABASE_URL` |
| `server/credentials.json` | OAuth Google Cloud |
| `server/token.json` | Token de acesso Google Calendar |

> Os arquivos `appointments.json`, `sessions.json` e `pending.json` foram removidos — os dados estão no banco PostgreSQL.

Todos os arquivos sensíveis já estão no `.gitignore`. **Nunca remover essas entradas.**

---

## 8. Estrutura de Arquivos Relevantes

```
lenz-otica/
├── docker-compose.yml       # dois postgres: lenz-postgres (5433) + evolution-postgres
├── db/
│   └── init.sql             # schema completo — executado automaticamente pelo Docker
├── DATABASE.md              # documentação do banco, fluxo de dados e RAG
├── AMBIENTE.md              # este arquivo
└── server/
    ├── .env                 # variáveis de ambiente (nunca versionar)
    ├── db.py                # pool de conexões psycopg
    ├── main.py              # FastAPI + scheduler
    ├── ai.py                # agente IA (Groq / Ollama) + histórico no banco
    ├── appointments.py      # CRUD de agendamentos → PostgreSQL
    ├── pending.py           # CRUD de pendências → PostgreSQL
    ├── panel.py             # renderização do painel HTML
    ├── calendar_service.py  # integração Google Calendar
    ├── migrate.py           # migração única JSON → banco (já executada)
    ├── credentials.json     # OAuth Google (nunca versionar)
    └── token.json           # token Google Calendar (nunca versionar)
```

---

## 9. Ordem de Inicialização Resumida

```
Desenvolvimento:
  1. docker compose up -d postgres-lenz
  2. ollama serve  (se não estiver rodando como serviço)
  3. cd server && uvicorn main:app --reload --host 0.0.0.0
  4. Abrir http://127.0.0.1:8000/painel

Produção:
  1. docker compose up -d
  2. cd server && uvicorn main:app --reload --host 0.0.0.0
  3. ngrok http 8000
  4. Configurar webhook URL na Evolution API
  5. Escanear QR code
  6. Abrir http://127.0.0.1:8000/painel
```
