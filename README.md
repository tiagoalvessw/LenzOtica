# LenzOtica — Atendente Virtual via WhatsApp com IA

Projeto de estudo: chatbot para agendamento de consultas de uma otica via WhatsApp, com resposta automatizada por Inteligencia Artificial.

---

## Sumario

1. [Visao Geral do Projeto](#visao-geral-do-projeto)
2. [Por que cada ferramenta foi escolhida](#por-que-cada-ferramenta-foi-escolhida)
3. [Arquitetura do Sistema](#arquitetura-do-sistema)
4. [Passo a Passo: Como o Projeto Foi Construido](#passo-a-passo-como-o-projeto-foi-construido)
5. [Estrutura de Arquivos](#estrutura-de-arquivos)
6. [Como Executar Localmente](#como-executar-localmente)
7. [Desafios e Solucoes](#desafios-e-solucoes)
8. [Bugs Corrigidos e Melhorias](#bugs-corrigidos-e-melhorias)
9. [Proximos Passos](#proximos-passos)

---

## Visao Geral do Projeto

A **LenzOtica** e uma atendente virtual que responde mensagens no WhatsApp de forma automatica e humanizada. Quando um cliente envia uma mensagem para o numero da otica, a IA assume o atendimento, coleta os dados necessarios (nome, data e horario) e agenda a consulta.

**Objetivo educacional:** aprender na pratica como integrar:
- Servicos em containers Docker
- APIs externas (WhatsApp, IA)
- Servidores web em Python
- Comunicacao via webhooks

**Custo:** zero. Todo o stack utiliza planos gratuitos.

---

## Por que cada ferramenta foi escolhida

### WhatsApp como canal de atendimento
O WhatsApp e o aplicativo de mensagens mais usado no Brasil. Para uma otica atender clientes de forma automatica, faz sentido estar onde os clientes ja estao, sem precisar instalar nenhum app novo.

### Evolution API — Gateway do WhatsApp
**O que e:** um servidor open-source que simula o WhatsApp Web, permitindo enviar e receber mensagens via API REST.

**Por que usar:**
- Gratuito e self-hosted (roda na sua propria maquina)
- Alternativa acessivel a API oficial do WhatsApp Business (que exige aprovacao da Meta e tem custos)
- Ideal para projetos de estudo e prototipagem

**Desvantagem:** nao e a API oficial do Meta, portanto nao e indicada para uso em producao em larga escala.

### Docker — Conteinerizacao
**O que e:** uma plataforma que empacota aplicacoes em "containers" — ambientes isolados com tudo que o software precisa para rodar.

**Por que usar:**
- A Evolution API requer Node.js, PostgreSQL e diversas dependencias. Instalar tudo manualmente seria complexo e propenso a erros.
- Com Docker, um unico arquivo (`docker-compose.yml`) sobe toda a infraestrutura com um comando.
- Garante que o ambiente e identico em qualquer maquina.

### PostgreSQL — Banco de Dados
**O que e:** banco de dados relacional open-source, um dos mais usados no mundo.

**Por que usar:**
- A Evolution API v2 exige um banco de dados para armazenar sessoes, mensagens e configuracoes.
- PostgreSQL e robusto, gratuito e tem excelente suporte na comunidade.

### Python + FastAPI — Servidor Web
**O que e:** Python e uma linguagem de programacao de alto nivel; FastAPI e um framework moderno para criar APIs web em Python.

**Por que usar Python:**
- Sintaxe simples e legivel, ideal para quem esta aprendendo
- Enorme ecossistema de bibliotecas (IA, APIs, automacao)
- Muito usado em projetos de IA e machine learning

**Por que FastAPI:**
- Cria endpoints HTTP de forma rapida e com pouco codigo
- Suporta programacao assincrona (async/await), ideal para receber webhooks
- Gera documentacao automatica em `/docs`

### Groq API — Inteligencia Artificial
**O que e:** plataforma de IA que oferece acesso a modelos de linguagem (LLMs) como o LLaMA da Meta, com hardware especializado (LPU) que gera respostas extremamente rapidas.

**Por que usar:**
- Plano gratuito generoso: 14.400 requisicoes por dia
- Muito mais rapido que alternativas (respostas em menos de 1 segundo)
- Nao requer cartao de credito para comecar

**Modelo escolhido:** `llama-3.3-70b-versatile` — modelo grande, com excelente compreensao de portugues e raciocinio para conduzir conversas de agendamento.

**Modelo de fallback:** `llama-3.1-8b-instant` — acionado automaticamente quando o modelo principal atinge o limite de tokens por dia (TPD). Tem quota diaria propria de 500.000 tokens e janela de contexto de 128k, suficiente para o prompt do sistema.

**Alternativa testada e descartada:** Google Gemini — o plano gratuito da conta do usuario estava com `limit: 0`, impossibilitando o uso.

### Ollama — LLM Local para Testes
**O que e:** ferramenta open-source que baixa e executa modelos de linguagem diretamente no computador, sem internet e sem custo.

**Por que usar:**
- O plano gratuito da Groq tem limite de 100.000 tokens por dia. Para desenvolver e testar o comportamento da Liza sem consumir essa quota, o Ollama roda o mesmo modelo localmente.
- Testes ilimitados sem risco de esgotar a API de producao.
- Funciona completamente offline.

**Desvantagem:** respostas mais lentas em CPU (~5–15 segundos por mensagem). Adequado para desenvolvimento, nao para producao.

**Como alternar:** variavel `USE_LOCAL_LLM` no `server/.env`.

### ngrok — Tunel para Desenvolvimento Local
**O que e:** ferramenta que cria uma URL publica acessivel pela internet, redirecionando o trafego para sua maquina local.

**Por que usar:**
- A Evolution API precisa enviar os eventos (mensagens recebidas) para uma URL acessivel publicamente — o que sua maquina local nao e por padrao.
- Com ngrok, o servidor Python rodando em `localhost:8000` fica disponivel em uma URL como `https://abc123.ngrok-free.app`.
- Ideal para desenvolvimento: nao precisa fazer deploy em um servidor real para testar.

### python-dotenv — Gerenciamento de Segredos
**O que e:** biblioteca Python que le variaveis de ambiente de um arquivo `.env`.


**Por que usar:**
- Chaves de API (senhas) nunca devem ficar escritas diretamente no codigo — se o codigo for para o GitHub, qualquer pessoa veria a chave.
- O arquivo `.env` fica local e e adicionado ao `.gitignore`, permanecendo privado.

---

## Arquitetura do Sistema

```
Cliente (WhatsApp)
       |
       | envia mensagem
       v
Evolution API (Docker, porta 8080)
       |
       | dispara evento via HTTP POST (webhook)
       v
ngrok (ponte localhost <-> internet)
       |
       v
FastAPI Server (Python, porta 8000)
       |
       |-- extrai texto da mensagem
       |-- chama get_response(sender, texto)
       |
       v
Groq API (LLaMA 3.3 70B)
       |
       | retorna resposta da IA
       v
FastAPI Server
       |
       | chama Evolution API para enviar resposta
       v
Evolution API
       |
       v
Cliente (recebe resposta no WhatsApp)
```

**Fluxo resumido:** mensagem do cliente → Evolution API captura → dispara webhook → Python processa → IA gera resposta → Evolution API envia de volta ao cliente.

---

## Passo a Passo: Como o Projeto Foi Construido

### Etapa 1 — Planejamento e escolha do stack

Antes de escrever qualquer codigo, foi necessario responder:
- Como conectar ao WhatsApp? → Evolution API (gratuita, open-source)
- Em qual linguagem programar o servidor? → Python (mais simples para iniciantes)
- Qual IA usar? → Groq (gratuita, rapida)
- Como expor o servidor local para a internet? → ngrok

### Etapa 2 — Instalacao do ambiente

**Ferramentas instaladas:**
1. **Python 3.x** — baixado em [python.org](https://python.org) com a opcao "Add Python to PATH" marcada
2. **Docker Desktop** — para rodar a Evolution API em container
3. **WSL (Windows Subsystem for Linux)** — exigido pelo Docker no Windows; atualizado via `wsl --update`
4. **ngrok** — instalado e configurado com conta gratuita
5. **VS Code** — editor de codigo escolhido para escrever os arquivos

**Bibliotecas Python instaladas:**
```bash
pip install fastapi uvicorn python-dotenv requests groq
```

### Etapa 3 — Configuracao da Evolution API com Docker

Foi criado o arquivo `docker-compose.yml` para orquestrar dois servicos:
- **postgres**: banco de dados exigido pela Evolution API v2
- **evolution-api**: o gateway do WhatsApp

Para subir os containers:
```bash
docker compose up -d
```

A Evolution API ficou disponivel em `http://localhost:8080`.

### Etapa 4 — Criacao da instancia e conexao do WhatsApp

Pela interface da Evolution API (`http://localhost:8080`), foi criada uma instancia chamada `lenz-otica`. Ao acessar o QR code da instancia, o WhatsApp foi conectado escaneando com o celular (assim como no WhatsApp Web).

### Etapa 5 — Configuracao do servidor Python

**Estrutura do servidor:**

O arquivo `ai.py` gerencia a comunicacao com a IA:
- Mantem o historico de conversa por usuario (sessoes em dicionario Python)
- Envia o historico completo a cada chamada para que a IA "lembre" o contexto

O arquivo `main.py` e o servidor FastAPI:
- Recebe os eventos da Evolution API no endpoint `/webhook`
- Filtra apenas mensagens de texto recebidas (ignora mensagens enviadas pelo bot, midias, etc.)
- Resolve identificadores especiais de usuarios (`@lid` → numero de telefone real)
- Chama a IA e devolve a resposta via Evolution API

### Etapa 6 — Configuracao do ngrok

O ngrok cria um tunel entre a internet e o servidor local:
```bash
ngrok http 8000
```

A URL gerada (ex: `https://abc123.ngrok-free.app`) foi configurada como webhook na Evolution API para o evento `messages.upsert`.

### Etapa 7 — Integracao com IA (Groq)

Inicialmente o projeto usava o Google Gemini. Apos enfrentar limitacoes de quota no plano gratuito (`limit: 0` em todos os modelos), a IA foi migrada para a **Groq API**, que oferece plano gratuito funcional com 14.400 requisicoes por dia.

A migracao envolveu:
1. Criar conta em [console.groq.com](https://console.groq.com)
2. Gerar uma API key
3. Instalar a biblioteca: `pip install groq`
4. Reescrever o `ai.py` para usar o SDK da Groq

### Etapa 8 — Testes

**Teste do webhook** (sem WhatsApp real):
```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"event": "messages.upsert", "data": {"key": {"fromMe": false, "remoteJid": "5511999999999"}, "message": {"conversation": "Ola, quero agendar uma consulta"}}}'
```

**Resultado esperado:** a IA responde com uma mensagem de boas-vindas pedindo o nome do cliente.

---

## Estrutura de Arquivos

```
lenz-otica/
├── docker-compose.yml      # Orquestra Evolution API + PostgreSQL
├── patch-os.js             # Correcao de compatibilidade para a Evolution API no Windows
├── README.md               # Esta documentacao
├── imagens/
│   └── logo lenzótica.PNG  # Logo da empresa (exibida no painel administrativo)
└── server/
    ├── .env                # Chaves de API (NUNCA subir ao GitHub)
    ├── main.py             # Servidor FastAPI (recebe webhooks, envia respostas, scheduler)
    ├── ai.py               # Modulo de IA (Groq API, sessoes persistentes)
    ├── appointments.py     # Gerenciamento de agendamentos (CRUD + logica de lembrete)
    ├── panel.py            # Modulo do painel administrativo (HTML/CSS/JS isolado)
    ├── pending.py          # Modulo de pendencias para o operador (CRUD em pending.json)
    ├── appointments.json   # Banco de dados local de agendamentos (gerado automaticamente)
    ├── sessions.json       # Historico de conversas persistido (gerado automaticamente)
    ├── pending.json        # Pendencias registradas pela IA para o operador (gerado automaticamente)
    ├── calendar_service.py # Integracao com Google Calendar API
    ├── credentials.json    # Credenciais OAuth do Google Cloud (NUNCA subir ao GitHub)
    ├── token.json          # Token de acesso gerado apos login (NUNCA subir ao GitHub)
    └── qrcode.html         # QR code gerado automaticamente pela Evolution API
```

### `.gitignore` recomendado

```
server/.env
server/__pycache__/
server/qrcode.html
*.pyc
```

---

## Como Executar Localmente

### Pre-requisitos

- Python 3.10+
- Docker Desktop instalado e em execucao
- Conta no [Groq](https://console.groq.com) com API key
- Conta no [ngrok](https://ngrok.com) com authtoken configurado

### 1. Clonar o repositorio

```bash
git clone https://github.com/seu-usuario/lenz-otica.git
cd lenz-otica
```

### 2. Configurar variaveis de ambiente

Criar o arquivo `server/.env`:
```
GROQ_API_KEY=gsk_sua_chave_aqui
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=lenz-otica-key-2024
EVOLUTION_INSTANCE=lenz-otica
ADMIN_TOKEN=uma-senha-forte-para-o-painel
CALENDAR_EMBED_URL=https://calendar.google.com/calendar/embed?src=SEU_EMAIL&ctz=America%2FSao_Paulo
USE_LOCAL_LLM=false
```

> `ADMIN_TOKEN` e obrigatorio. O servidor nao inicia sem ele. Todos os endpoints `/admin/*` exigem esse token no header `X-Admin-Token`. O painel envia o token automaticamente via JavaScript — nao e necessario inserir manualmente.

> `CALENDAR_EMBED_URL` e opcional. Obtenha a URL em: Google Calendar → Configuracoes → [nome do calendario] → Integrar agenda → URL publica. O calendario deve estar definido como publico para exibir os eventos.

> `USE_LOCAL_LLM` e opcional (padrao: `false`). Defina como `true` para usar o Ollama local em vez da Groq — util para testes sem consumir tokens. Requer Ollama instalado e o modelo `llama3.1:8b` baixado.

### 3. Subir a infraestrutura Docker

```bash
docker compose up -d
```

### 4. Instalar dependencias Python

```bash
pip install fastapi uvicorn python-dotenv requests groq
```

### 5. Iniciar o servidor

```bash
cd server
uvicorn main:app --reload
```

### 6. Criar tunel ngrok

Em outro terminal:
```bash
ngrok http 8000
```

### 7. Configurar webhook na Evolution API

Acessar `http://localhost:8080`, selecionar a instancia `lenz-otica` e configurar o webhook com a URL do ngrok + `/webhook`.

### 8. Conectar o WhatsApp

Na interface da Evolution API, acessar o QR code da instancia e escanear com o celular.

---

## Desafios e Solucoes

| Problema | Causa | Solucao |
|---|---|---|
| Docker nao iniciava | WSL desatualizado no Windows | `wsl --update` no PowerShell como Admin |
| Evolution API: "Database provider invalid" | Versao v2 exige banco de dados | Adicionar PostgreSQL ao docker-compose.yml |
| Python nao encontrado no PATH | Instalacao via Microsoft Store sem PATH | Reinstalar pelo python.org com "Add to PATH" |
| IndentationError no Python | Notepad adicionava espacos extras ao colar codigo | Migrar para VS Code |
| Gemini API: `limit: 0` | Quota zerada no plano gratuito | Migrar para Groq API |
| Mensagens chegando com ID `@lid` | Evolution API v2 anonimiza o JID do remetente; endpoints da API nao retornam o numero real | Mapeamento manual via `.env`: `TEST_LID=<lid>` e `TEST_PHONE=<numero>` para numeros conhecidos. Limitacao documentada abaixo. |
| IA responde mas nao envia para LIDs desconhecidos | `sendText` valida o numero antes de enviar e rejeita JIDs `@lid` | Limitacao tecnica da Evolution API v2 — ver secao abaixo |

---

## Limitacao Tecnica: Identificadores @lid

O WhatsApp versao 6+ adotou um sistema de privacidade que substitui o numero de telefone por um identificador anonimo chamado **LID** (ex: `222711351644201@lid`). A Evolution API v2 recebe esses LIDs mas nao consegue converte-los de volta para numeros reais.

**O que foi investigado e testado:**

| Tentativa | Resultado |
|---|---|
| Endpoint `/chat/findChats` | Retorna o LID, mas sem campo de numero de telefone |
| Endpoint `/contact/fetchContacts` | Retorna erro 404 (nao existe nessa versao) |
| Endpoint `/docs` (Swagger) | Retorna erro 404 (desabilitado) |
| Envio direto para `@lid` via `sendText` | Erro 400: `exists: false` — validacao rejeita LIDs |
| Quoted reply com ID da mensagem original | Erro 400: validacao ocorre antes de verificar o contexto |
| Campo `remoteJidAlt` no objeto `key` do webhook | Campo nao existe na v2.2.3 — sugestao encontrada em comunidades nao se aplica a esta versao |
| Endpoint `GET /contact/profile/{lid}` | Erro 404 — endpoint nao existe na v2.2.3 |
| Variavel de ambiente `WPP_LID_MODE=false` no Docker | Variavel nao reconhecida — mensagens continuam chegando como `@lid` |
| Banco de dados PostgreSQL da Evolution API | Tabelas `Contact` e `Chat` armazenam apenas o LID, sem numero real |

**Conclusao v2.2.3:** Nenhum dos mecanismos acima funcionou nessa versao.

**Solucao encontrada:** Atualizar para a **Evolution API v2.3.7** compilada a partir do codigo-fonte do GitHub. O PR #2544 corrigiu o problema estendendo o bypass de validacao (que ja existia para `@broadcast`) para incluir JIDs `@lid`. A partir da v2.3.7, todas as mensagens chegam no formato `@s.whatsapp.net` com o numero real — o problema de LID foi eliminado completamente.

**Como aplicar a correcao:**
```bash
git clone https://github.com/EvolutionAPI/evolution-api.git
cd evolution-api
docker build -t evolution-api:local .
```
No `docker-compose.yml`, trocar `atendai/evolution-api:latest` por `evolution-api:local`.

---

## Bugs Corrigidos e Melhorias

### Bug 1 — Agendamentos nunca eram salvos

**Problema:** o `main.py` esperava que a IA gerasse um marcador `[AGENDAR:Nome|AAAA-MM-DD|HH:MM]` na resposta para extrair os dados e salvar o agendamento. Porem o `SYSTEM_PROMPT` em `ai.py` nunca instrui a IA a gerar esse marcador — ele so pedia um texto de confirmacao formatado. Resultado: nenhum agendamento era persistido no `appointments.json` e o lembrete automatico nunca disparava.

**Solucao:** adicionado ao `SYSTEM_PROMPT` a instrucao explicita para incluir o marcador ao final de cada confirmacao, com exemplo de formato. Testado e validado.

---

### Bug 2 — Sessoes perdidas ao reiniciar o servidor

**Problema:** o historico de conversas de todos os usuarios ficava em um dicionario Python em memoria (`sessions = {}`). Ao reiniciar o servidor, todas as sessoes eram apagadas — usuarios no meio de um agendamento recebiam a mensagem de boas-vindas novamente como se fossem novos contatos.

**Solucao:** sessoes agora sao persistidas automaticamente em `sessions.json`. O arquivo e carregado na inicializacao e atualizado a cada mensagem enviada ou recebida. Reiniciar o servidor nao interrompe mais conversas em andamento.

---

### Bug 3 — Qualquer resposta ao lembrete era tratada como confirmacao

**Problema:** ao receber o lembrete de 1 hora antes da consulta, o cliente via a opcao de responder `SIM` ou `NAO`. Porem qualquer mensagem — inclusive "Nao posso ir" ou "Preciso reagendar" — era marcada como `response_received`, impedindo o cancelamento automatico mas sem processar a intencao do cliente.

**Solucao:** implementada classificacao de intenção da resposta:
- Palavras positivas (`sim`, `ok`, `confirmo`, `pode`, `presente`, etc.) → status `confirmed`, mensagem de confirmacao enviada
- Palavras negativas (`nao`, `cancelar`, `reagendar`, etc.) → agendamento cancelado, mensagem de cancelamento enviada
- Resposta ambigua → `mark_response_received` (impede cancelamento automatico) e a IA assume o atendimento normalmente

Funcoes adicionadas em `appointments.py`: `has_pending_reminder`, `confirm_appointment`, `cancel_pending_reminders`.

---

### Bug 4 — Endereco com erros tipograficos na mensagem de confirmacao

**Problema:** a mensagem de confirmacao hardcoded em `main.py` tinha o endereco sem acentos e em minusculas: `"forquilhinhas, sao jose - SC (Ao lado do cartorio)"`.

**Solucao:** corrigido para `"Forquilhinhas, Sao Jose - SC (ao lado do cartorio)"`, consistente com o endereco no `SYSTEM_PROMPT`.

---

### Melhoria — Fluxo de lembretes automaticos duplos (scheduler)

O servidor roda um loop em segundo plano (`scheduler_loop`) a cada 60 segundos com tres verificacoes:

1. **Lembrete 1 dia antes** — busca agendamentos entre 23h55 e 24h05 no futuro → envia aviso informativo pelo WhatsApp → status `day_reminder_sent`
2. **Lembrete 1h antes** — busca agendamentos entre 55 e 65 minutos no futuro → envia pedido de confirmacao de presenca → status `reminder_sent`
3. **Auto-cancelamento** — busca agendamentos com horario passado sem confirmacao → cancela e notifica o cliente

**Fluxo completo de status:**
```
scheduled
   ↓ (24h antes) → mensagem: "Amanha voce tem consulta as Xh!"
day_reminder_sent
   ↓ (1h antes)  → mensagem: "Confirma presenca? SIM / NAO"
reminder_sent
   ↓
confirmed (cliente respondeu SIM) / cancelled (cliente respondeu NAO ou nao respondeu)
```

**Todos os cenarios testados e validados (9/9):**
- Agendamento criado → status `scheduled` ✓
- Lembrete 1 dia detectado (24h no futuro) ✓
- Apos lembrete 1 dia → status `day_reminder_sent` ✓
- Nao aparece no lembrete 1h enquanto falta 24h ✓
- Lembrete 1h detectado (60min no futuro) ✓
- Apos lembrete 1h → status `reminder_sent` ✓
- Resposta SIM → status `confirmed` ✓
- Resposta NAO → status `cancelled` ✓
- Sem resposta + horario passou → auto-cancelar ✓

---

### Melhoria — Painel administrativo

Acessivel em `http://localhost:8000/painel`. O HTML do painel foi isolado em `server/panel.py`, mantendo o `main.py` limpo — o endpoint se resume a tres linhas.

**Endpoints do painel:**

| Metodo | Rota | Funcao |
|---|---|---|
| `GET` | `/painel` | Pagina principal do painel |
| `GET` | `/painel/logo` | Serve a logo da empresa (sem biblioteca extra) |
| `POST` | `/admin/cancel` | Cancela agendamento + remove evento do Google Calendar |
| `POST` | `/admin/remind` | Dispara lembrete de confirmacao via WhatsApp manualmente |
| `POST` | `/admin/appointments` | Cria agendamento manual + evento no Google Calendar |
| `POST` | `/admin/edit` | Edita dados do agendamento + recria evento no Google Calendar |
| `POST` | `/admin/recover` | Recupera agendamento cancelado + recria evento no Google Calendar |
| `POST` | `/admin/attended` | Marca comparecimento do cliente |
| `POST` | `/admin/completed` | Conclui atendimento (requer comparecimento marcado) |
| `POST` | `/admin/reschedule` | Reabre agendamento com status no_show para reagendamento |
| `POST` | `/admin/close_protocol` | Encerra protocolo: arquiva o registro + remove evento do Google Calendar |
| `POST` | `/admin/reset_session` | Apaga o historico de conversa da IA para um numero especifico |
| `POST` | `/admin/pending/dismiss` | Remove uma pendencia da aba Pendente |
| `POST` | `/admin/completed_by_phone` | Marca o agendamento ativo de um telefone como concluido (sem exigir status `attended`) |

**Design e layout:**
- Fonte Inter (Google Fonts) para visual moderno e legivel
- Header fixo com gradiente azul e logo da empresa
- Layout em duas colunas: tabela de agendamentos + Google Calendar incorporado
- **Painel do calendario redimensionavel:** uma alca arrastavel (drag handle) entre a tabela e o calendario permite ajustar a largura do calendario livremente; largura preferida salva no `localStorage` e restaurada ao recarregar; limites: minimo 260px, maximo 900px
- Totalmente responsivo — em telas menores (< 1250px) a alca some e o calendario ocupa 100% da largura abaixo da tabela
- Modo claro e escuro com botao de alternancia no header; preferencia salva no `localStorage`

**Tab nav — 6 abas no topo (substituem os antigos cards de resumo):**

Cada aba exibe a contagem do filtro e serve simultaneamente como indicador e como filtro da tabela. Clicar na aba aplica o filtro imediatamente.

| Aba | Cor | O que exibe |
|---|---|---|
| Atendimento do Dia | Azul | Agendamentos de hoje com status ativo (exceto cancelled, no_show, completed) |
| Confirmado | Verde | Status `confirmed` ou `attended` — qualquer data |
| Cancelado | Vermelho | Status `cancelled` ou `no_show` — qualquer data |
| Concluido | Ciano | Status `completed` — qualquer data |
| Geral | Cinza | Todos os agendamentos visiveis |
| Pendente | Amarelo | Itens registrados pela IA para revisao do operador |

Apos cada acao do operador (cancelar, concluir, marcar comparecimento, etc.) a funcao `applyFilter()` e chamada automaticamente — a linha migra para a aba correta sem recarregar a pagina.

**Tabela de agendamentos:**
- Colunas: Cliente, Telefone, Data, Hora, Faltam, Status, Acoes
- Nome do cliente em negrito; telefone em fonte monoespaco
- Hora exibida em chip visual com borda
- Coluna **Faltam**: calcula e exibe o tempo restante ate a consulta em tempo real
  - Verde — mais de 2 horas
  - Laranja em negrito — menos de 2 horas
  - Cinza — consulta ja passou
  - Traco — agendamento cancelado ou concluido
- Linhas do dia atual destacadas com fundo azul claro e badge **HOJE** na data

**Acoes por linha (icone + texto):**
- Botao **Lembrete** — visivel para `scheduled` e `day_reminder_sent`; envia confirmacao via WhatsApp e atualiza o status sem recarregar
- Botao **Editar** — abre modal arrastavel preenchido com os dados atuais; salva nome, telefone, data e hora; recria o evento no Google Calendar
- Botao **Cancelar** — exibe modal de confirmacao antes de agir; cancela o evento no Calendar e atualiza a linha
- Botao **Recuperar** — aparece em linhas canceladas; restaura o agendamento para `scheduled` e recria o evento no Calendar
- Botao **Compareceu** — visivel para `confirmed`; registra que o cliente chegou (status `attended`)
- Botao **Concluir** — visivel para `attended`; abre modal para registrar observacoes e finaliza o atendimento (status `completed`)
- Botao **Remarcar** — visivel para `no_show`; reabre o agendamento para novo contato (status `scheduled`)
- Botao **Encerrar Protocolo** — visivel para `completed`, `cancelled` e `no_show`; exibe modal de confirmacao, arquiva o registro (status `archived`), remove o evento do Google Calendar e retira a linha do painel imediatamente. Os dados permanecem salvos no `appointments.json` para historico.
- Botao **Resetar IA** — visivel em todas as linhas; exibe modal de confirmacao nativo do browser; ao confirmar, apaga o historico de conversa da IA para aquele numero (`sessions.json`). A proxima mensagem do cliente sera tratada como primeiro contato. Util quando o cliente esta travado em uma conversa sem saida ou quando um numero muda de titular.
- **Toast de feedback** com icone de check ou X confirma sucesso ou erro em cada acao

**Aba Pendente:**
- A IA pode gerar o marcador `[PENDENTE:observacao]` na resposta para sinalizar situacoes que precisam de atencao humana (ex: cliente indica um contato para ser abordado, situacao ambigua que a IA nao soube resolver).
- O `main.py` detecta o marcador, registra o item em `pending.json` via `pending.py` e remove o marcador do texto antes de enviar ao cliente.
- A aba Pendente exibe telefone, observacao e data/hora de cada item.
- Acoes disponiveis: **Resetar IA** (reinicia conversa do numero) e **Concluir** (remove o item da lista — contador decrementado imediatamente, sem modal).

**Agendamento manual:**
- Botao **+ Novo agendamento** no cabecalho da tabela
- Modal flutuante e arrastavel; auto-refresh pausado enquanto o modal esta aberto
- Campos: Nome, Telefone, Data e Hora
- Ao confirmar: cria o agendamento no `appointments.json` e o evento no Google Calendar

**Busca em tempo real:**
- Barra de busca com icone integrado; filtra por nome ou telefone dentro da aba ativa
- O filtro de texto e combinado com o filtro de aba — ambos funcionam simultaneamente

**Auto-refresh:**
- Pagina recarrega automaticamente a cada 30 segundos quando o operador esta ocioso
- **Pausa por interacao:** se o operador mover o mouse, apertar uma tecla ou rolar a pagina, o contador e reiniciado para 30s e o cabecalho exibe "Pausado". O contador so conta regressivamente apos 15 segundos sem interacao (`IDLE_MS = 15000`)
- **Pausa por modal:** qualquer modal aberto (editar, concluir, cancelar, novo agendamento, encerrar protocolo) pausa o auto-refresh; ao fechar o modal o contador retoma do zero
- Timestamp "Atualizado HH:MM" exibido no header

**Google Calendar incorporado:**
- Google Calendar da otica exibido na coluna direita do painel
- Configurado via variavel de ambiente `CALENDAR_EMBED_URL` no `server/.env`
- Quando nao configurado, exibe instrucoes de como obter a URL
- O calendario precisa estar definido como publico no Google Calendar para exibir os eventos

**Tabela de status:**

| Status | Cor | Significado |
|---|---|---|
| Aguardando | Amarelo | Agendado, sem lembrete enviado ainda |
| Lembrete 1 dia | Azul | Aviso de amanha enviado |
| Lembrete 1h | Indigo | Pedido de confirmacao enviado |
| Respondeu | Roxo | Cliente respondeu algo apos o lembrete |
| Confirmado | Verde | Cliente confirmou presenca |
| Compareceu | Verde-agua | Cliente chegou fisicamente; aguardando conclusao |
| Concluido | Azul-ciano | Atendimento finalizado pelo operador |
| Nao veio | Laranja | Horario passou sem registro de comparecimento (scheduler automatico) |
| Cancelado | Vermelho | Cancelado pelo cliente ou automaticamente |
| Arquivado | — | Protocolo encerrado pelo operador; nao aparece no painel |

**Fluxo completo de status:**
```
scheduled
   ↓ (24h antes) scheduler
day_reminder_sent
   ↓ (1h antes) scheduler
reminder_sent
   ↓ cliente responde SIM          ↓ cliente responde NAO / nao responde + horario passa
confirmed                          cancelled
   ↓ horario passa sem attended    ↓ operador "Recuperar"
no_show                            scheduled (reaberto)
   ↓ operador "Compareceu"         ↓ operador "Encerrar Protocolo"
attended                           archived
   ↓ operador "Concluir"
completed
   ↓ operador "Encerrar Protocolo"
archived
```

---

### Melhoria — Integracao com Google Calendar

Quando um cliente confirma um agendamento via WhatsApp, um evento e criado automaticamente no Google Calendar da otica. Quando o cliente cancela, o evento e removido.

**Arquivo criado:** `server/calendar_service.py`

**Funcoes:**
- `create_event(name, date, time, phone)` — cria evento no Calendar com nome, data, hora, endereco e telefone do cliente na descricao
- `cancel_event(event_id)` — remove o evento do Calendar

**Formato do evento no Calendar:**
```
Titulo:    Consulta — Nome do Cliente
Local:     Rua Vereador Arthur Manoel Mariano, 362, Forquilhinhas, Sao Jose - SC
Descricao: Agendado via WhatsApp
           Telefone: 5511999999999
Duracao:   1 hora
```

**Configuracao necessaria (feita uma unica vez):**
1. Criar projeto no Google Cloud Console
2. Ativar Google Calendar API
3. Criar credenciais OAuth (tipo "App para computador") e salvar como `server/credentials.json`
4. Adicionar o e-mail como usuario de teste na tela de consentimento OAuth
5. Rodar `python -c "from calendar_service import _get_service; _get_service()"` — abre o navegador para login, gera `server/token.json`

Apos o login inicial, o `token.json` e renovado automaticamente — nao e necessario autenticar novamente.

**Bibliotecas instaladas:**
```bash
pip install google-api-python-client google-auth-oauthlib
```

**Arquivos gerados (nao subir ao GitHub):**
- `server/credentials.json` — chave OAuth do Google Cloud
- `server/token.json` — token de acesso gerado apos o login

---

### Melhoria — Tratamento de midias

Anteriormente, mensagens sem texto (audios, fotos, videos, documentos, figurinhas) eram silenciosamente ignoradas — o cliente nao recebia nenhuma resposta.

Agora a Liza responde educadamente para cada tipo de midia:

| Midia recebida | Resposta enviada |
|---|---|
| Audio | "Nao consigo ouvir audios, mas fico feliz em te ajudar por texto! Como posso te atender?" |
| Imagem | "Nao consigo visualizar imagens, mas pode me descrever o que precisa! Como posso te ajudar?" |
| Video | "Nao consigo assistir videos, mas pode me escrever o que precisa! Como posso te ajudar?" |
| Documento | "Nao consigo abrir documentos, mas pode me descrever o que precisa! Como posso te ajudar?" |
| Figurinha | "Que simpatico! Posso te ajudar com alguma coisa?" |

A resposta e injetada no historico de conversa da sessao, mantendo o contexto para a proxima mensagem do cliente.

---

### Bugs de IA corrigidos no SYSTEM_PROMPT

**Datas erradas nas opcoes de agendamento:** a IA ancoravam em datas fixas do exemplo no prompt (`26/05`, `28/05`, `30/05`) em vez de calcular a partir da data atual. Corrigido substituindo por placeholders `[DD/MM]` com instrucao explicita de calculo.

**Data errada no marcador [AGENDAR:]:** a IA escrevia a data correta no texto de confirmacao mas gerava a data com +1 dia no marcador. Corrigido adicionando instrucao explicita: "use a MESMA data que aparece na confirmacao, convertida para AAAA-MM-DD".

---

### Melhoria — Referencia de localizacao para clientes que nao conhecem a regiao

Quando o cliente diz que nao conhece o endereco ou a regiao de Forquilhinhas, a Liza fornece uma referencia de como chegar:

> "E bem facinho, saindo da BR no trevo da Forquilhinhas, descendo a rua voce ja vai ver um predio comercial grande marrom a sua direita. Mas e so colocar no gps que da bem certinho."

---

### Melhoria — Validacao de data e hora no marcador de agendamento

**Problema:** a regex que detecta o marcador `[AGENDAR:Nome|AAAA-MM-DD|HH:MM]` validava apenas o formato (digitos no lugar certo), mas nao os valores — datas como `2026-13-01` (mes 13) ou horarios como `25:00` passavam silenciosamente e causariam erro ao salvar ou criar evento no Calendar.

**Solucao:** adicionada validacao com `datetime.fromisoformat` + `replace(hour, minute)` antes de qualquer persistencia. Se a data ou hora for invalida:
1. O erro e registrado no console com `[VALIDACAO]`
2. A mensagem de confirmacao e enviada ao cliente sem o marcador tecnico
3. O agendamento **nao e salvo** — evitando dados corrompidos no `appointments.json` e erros no Google Calendar

Localizacao: `main.py`, bloco `if match:` do endpoint `/webhook`.

---

### Melhoria — Treinamento da IA com situacoes reais de atendimento

O `SYSTEM_PROMPT` foi atualizado com tres situacoes reais de atendimento usadas como exemplos (few-shot) para a IA aprender o fluxo, o tom e as respostas esperadas em cada cenario.

**Situacao 1 — Agendamento direto:**
Cliente pergunta como agendar → Liza coleta o nome → informa a campanha → pergunta preferencia de dia → apresenta horarios do dia escolhido → confirma.

**Situacao 2 — Cliente com duvidas sobre obrigacao de compra e precos:**
- Se o cliente perguntar se e obrigado a comprar oculos para fazer o exame gratuito, a Liza explica que nao ha vinculo entre o exame e a compra, mas pede a oportunidade de atender.
- Se o cliente perguntar sobre precos ou prazo de confeccao, a Liza informa: armacoes a partir de R$149,90 e lentes a partir de R$99,90, com opcoes premium disponiveis.
- Se a conversa esfriar apos as duvidas, a Liza retoma pelo nome do cliente com proposta direta de agendamento.

**Situacao 3 — Cliente com receita pedindo orcamento:**
Cliente informa que tem receita e quer orcamento → Liza coleta o nome → pede para enviar a foto da receita → informa que um consultor ira atende-lo em breve.

**Novo fluxo de agendamento (duas etapas):**
Antes: a Liza apresentava 3 opcoes de data+hora diretamente.
Agora: primeiro pergunta a preferencia de dia ("Tenho horarios na quarta e sexta, gostaria de aproveitar?"), depois apresenta os horarios disponiveis para o dia escolhido ("Na sexta tenho: 13:30 | 14:30 | 16:00 — qual fica melhor?"). Fluxo mais natural e alinhado com o atendimento real.

---

### Melhoria — Ciclo de vida completo do atendimento no painel

Implementado o fluxo completo de encerramento de atendimentos no painel administrativo.

**Problema anterior:** agendamentos concluidos, cancelados e nao comparecidos ficavam visiveis no painel indefinidamente, sem forma de o operador remove-los. Alem disso, os eventos correspondentes permaneciam no Google Calendar mesmo apos o atendimento ser finalizado.

**Solucao — Botao "Encerrar Protocolo":**

Adicionado o botao **Encerrar Protocolo** (icone de arquivo, cor cinza) nas linhas com status:
- `completed` (Concluido)
- `cancelled` (Cancelado)
- `no_show` (Nao veio)

Ao clicar, um modal de confirmacao pergunta se o operador deseja encerrar. Ao confirmar:
1. O endpoint `POST /admin/close_protocol` e chamado com `phone`, `date` e `time`
2. O evento correspondente e removido do Google Calendar via `cancel_event`
3. O status do registro muda para `archived` no `appointments.json` (dados preservados para historico)
4. A linha e removida do painel imediatamente sem recarregar a pagina
5. O painel filtra registros `archived` no carregamento — eles nunca reaparecem

**Funcoes adicionadas em `appointments.py`:**
- `archive_appointment(phone, date, time)` — muda status para `archived` e registra `archived_at`; aceita `completed`, `cancelled` e `no_show`

---

### Bug corrigido — Eventos orphaos no Google Calendar apos marcar como "Nao veio"

**Problema:** quando o scheduler automaticamente marcava um agendamento como `no_show` (confirmado cujo horario passou ha 30+ minutos sem comparecimento registrado), o evento continuava existindo no Google Calendar. Se o operador depois clicasse em "Remarcar", um novo evento era criado sem remover o antigo, gerando duplicatas visiveis no calendario.

**Solucao:** adicionada chamada a `cancel_event` na funcao `check_no_shows()` de `main.py`, imediatamente antes de `mark_no_show()`. A partir de agora, ao detectar um no-show, o evento e automaticamente removido do Calendar.

**Limpeza retroativa executada:** 9 eventos orfaos identificados no Google Calendar (7 de registros `archived` + 2 de registros `no_show` criados antes da correcao). Todos foram removidos via script de limpeza; `event_id` zerado no `appointments.json` para os registros afetados.

---

### Melhoria — Painel do Google Calendar redimensionavel

**Problema anterior:** a largura do painel do Google Calendar era fixa em 400px, sem possibilidade de ajuste pelo operador.

**Solucao:** substituido o layout de grid fixo por um layout flex com uma **alca de redimensionamento arrastavel** entre a tabela de agendamentos e o calendario.

**Como usar:** passar o mouse sobre a linha divisoria entre os dois paineis — ela fica destacada em azul. Arrastar para a esquerda amplia o calendario; para a direita encolhe.

**Detalhes tecnicos:**
- Layout: `display: flex` com `layout-left { flex: 1 }` e `layout-right { width: 400px }`
- Alca (`.resize-handle`): elemento de 10px de largura com cursor `col-resize` e indicador visual (barra azul ao hover/drag)
- Limites: minimo 260px, maximo 900px para o calendario
- Preferencia de largura salva em `localStorage` com chave `cal-panel-width` e restaurada automaticamente ao carregar o painel
- Responsivo: em telas menores que 1250px a alca e ocultada e o calendario ocupa 100% da largura abaixo da tabela (`width: 100% !important`)

---

### Melhoria — Fluxo de oftalmologista no prompt da Liza

O `SYSTEM_PROMPT` foi atualizado para que a Liza diferencie os dois profissionais presentes no predio.

**Regra:** a LenzOtica agenda apenas consultas com o optometrista (triagem gratuita). Casos que exijam oftalmologista sao redirecionados para o Doutor Popular (48 3375-2050), que fica no mesmo predio.

**Fluxo:**
1. Cliente pergunta se e atendimento com oftalmologista → Liza explica a diferenca entre os dois e pergunta se o cliente ja faz algum tratamento.
2. Se o cliente so precisa renovar oculos → Liza prossegue com o agendamento normalmente.
3. Se o cliente faz tratamento ou prefere oftalmologista → Liza redireciona para o Doutor Popular e encerra o fluxo de agendamento pela LenzOtica.

---

### Melhoria — Deteccao de horario vencido e reagendamento no mesmo dia

**Problema anterior:** se o horario da consulta ja havia passado (ex: consulta marcada para 9h e o cliente abre o WhatsApp as 11h), a Liza nao reconhecia a situacao e seguia o atendimento normalmente.

**Solucao:** o `main.py` injeta dinamicamente no contexto da IA a lista de horarios ja ocupados para o dia atual. Quando a Liza percebe que o horario agendado passou, oferece um encaixe no mesmo dia com os slots livres restantes.

**Como funciona:**
- A cada mensagem recebida, `ai.py` recebe como contexto adicional: `"Horarios ocupados hoje (YYYY-MM-DD): HH:MM, HH:MM..."` com base nos agendamentos ativos do dia em `appointments.json`.
- O prompt instrui a Liza a cruzar essa lista com a grade de funcionamento e a hora atual para oferecer somente slots realmente disponiveis.

---

### Melhoria — Slots de 30 minutos e 6 opcoes de horario

**Duracao da consulta:** cada atendimento ocupa 30 minutos. Os slots seguem a grade: 9:00, 9:30, 10:00, 10:30...

**Quantidade de opcoes:** ao apresentar horarios disponiveis, a Liza oferece 6 opcoes para o dia escolhido (antes eram 3-4). Se o dia tiver menos de 6 slots livres, todos os disponiveis sao listados com aviso.

---

### Melhoria — Marcadores especiais no prompt da Liza

O sistema usa dois marcadores ocultos na resposta da IA para acionar acoes no servidor sem expor codigo tecnico ao cliente.

| Marcador | Formato | O que faz |
|---|---|---|
| `[AGENDAR:]` | `[AGENDAR:Nome\|AAAA-MM-DD\|HH:MM]` | Salva o agendamento em `appointments.json` e cria evento no Google Calendar |
| `[PENDENTE:]` | `[PENDENTE:descricao da situacao]` | Registra um item na aba Pendente do painel para revisao do operador |
| `[BREAK]` | `[BREAK]` | Divide a resposta em duas mensagens WhatsApp separadas (util para nao misturar campanha com pergunta de horario) |

Todos os marcadores sao removidos do texto antes de enviar a mensagem ao cliente.

---

### Bug corrigido — JavaScript do painel quebrado apos adicao do botao Resetar IA

**Problema:** apos adicionar o botao "Resetar IA" ao painel, dois erros foram introduzidos no `panel.py` que quebravam silenciosamente todo o bloco `<script>` — o browser abandonava o parse do JavaScript sem exibir erro visivel. Como resultado, nenhuma funcao JS era registrada: o botao de dark mode parava de funcionar, o auto-refresh nao pausava, e nenhum botao de acao respondia.

**Causa 1 — Bloco de codigo orfao:**
Ao refatorar a funcao `resetSession`, o corpo antigo da funcao ficou solto fora de qualquer funcao no nivel superior do script. Em JavaScript, instrucoes como `return`, `await` e declaracoes `const` fora de funcoes causam erro de parse imediato.

**Causa 2 — `\n` literal em f-string Python:**
O HTML do painel e gerado como um f-string Python gigante. Dentro desse f-string, `\n` e interpretado pelo Python como uma quebra de linha real — que e inserida literalmente no HTML. Strings JavaScript nao aceitam quebras de linha literais (apenas template literals com crase aceitam). Os `confirm()` do botao Resetar IA continham `\n\n` que geravam duas quebras de linha dentro das aspas, invalidando o parse.

**Correcao:**
1. O bloco orfao foi removido integralmente do `panel.py`.
2. Os `\n\n` nos `confirm()` foram substituidos por `\\n\\n` — com a barra dupla, o Python gera a sequencia de escape `\n` no HTML, que o JavaScript interpreta corretamente como nova linha no dialogo.

**Licao aprendida:** em f-strings Python que geram JavaScript, nunca usar `\n` diretamente dentro de strings JS — sempre usar `\\n`. Qualquer `\n` sem barra dupla vira newline real no HTML e quebra o parse JS.

---

### Melhoria — Controle de consumo de tokens no Groq

**Problema:** o bot excedia o limite de tokens por minuto (TPM) da Groq em tres frentes distintas:

1. **Modelo `gemma2-9b-it` com janela de 8.192 tokens:** o segundo modelo da lista de fallback tinha uma janela de contexto muito pequena. O system prompt sozinho ultrapassava 4.000 tokens, tornando o modelo inutil e causando erros de contexto excedido.

2. **Historico ilimitado por contagem de mensagens:** o limite `MAX_HISTORY = 8` cortava o historico pelo numero de mensagens, sem considerar o tamanho real de cada uma. Uma conversa com respostas longas podia acumular 3.000+ tokens de historico e exceder o TPM disponivel.

3. **System prompt com 4.161 tokens:** o prompt original consumia 83% do orcamento de tokens por requisicao antes mesmo de incluir o historico ou a mensagem do usuario.

**Solucoes aplicadas:**

**1 — Remocao do `gemma2-9b-it` da lista de fallback (`ai.py`):**

```python
# Antes
MODELS = [
    "llama-3.3-70b-versatile",
    "gemma2-9b-it",          # janela de 8k — insuficiente para o prompt
    "llama-3.1-8b-instant",
]

# Depois
MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",  # 128k de contexto — seguro
]
```

**2 — Trim de historico baseado em tokens (`ai.py`):**

Substituido o corte fixo por uma funcao que estima os tokens de cada mensagem (tamanho do texto / 4) e remove pares de mensagens (user + assistant) do inicio do historico ate caber no orcamento disponivel:

```python
def _count_tokens(text: str) -> int:
    return max(1, len(text) // 4)

def _trim_history(history, system_tokens, max_total=5000):
    budget = max_total - system_tokens
    total = sum(_count_tokens(m["content"]) for m in history)
    while total > budget and len(history) > 2:
        removed = history.pop(0)
        total -= _count_tokens(removed["content"])
        if history and history[0]["role"] == "assistant":
            removed = history.pop(0)
            total -= _count_tokens(removed["content"])
    return history
```

Conversas com mensagens longas truncam mais cedo; conversas com mensagens curtas mantem mais contexto. O historico nunca ultrapassa o orcamento calculado dinamicamente.

**3 — Enxugamento do SYSTEM_PROMPT (reducao de 49%):**

Removidos os elementos redundantes sem alterar nenhum comportamento:
- Tres conversas de exemplo completas (Situacoes 1, 2, 3) que repetiam regras ja descritas
- Dois exemplos inline do formato `[BREAK]` (redundantes com o template obrigatorio)
- Aviso de nomes ficticios e separador `--- FIM DOS EXEMPLOS ---`
- Regras duplicadas e conectivos verbosos

| Metrica | Antes | Depois |
|---|---|---|
| Caracteres do system prompt | 16.647 | 8.475 |
| Tokens estimados | 4.161 | 2.118 |
| Budget para historico | 839 tokens | 2.882 tokens |
| Reducao total | — | **-49%** |

O custo por requisicao caiu de ~5.000 para ~2.500 tokens, dobrando a capacidade de historico e reduzindo a pressao sobre o limite de TPM do plano gratuito do Groq.

---

### Melhoria — Modo de teste local com Ollama (sem consumo de tokens)

**Problema:** o plano gratuito da Groq tem limite de 100.000 tokens por dia. Em dias de desenvolvimento intenso, o limite e atingido rapidamente — cada requisicao custa ~2.500 tokens so de overhead do system prompt, independentemente do conteudo da conversa.

**Solucao:** suporte a dois modos de operacao controlados pela variavel `USE_LOCAL_LLM` no `.env`:

- `USE_LOCAL_LLM=false` (padrao) — usa a Groq API normalmente com fallback para `llama-3.1-8b-instant`
- `USE_LOCAL_LLM=true` — usa o Ollama rodando localmente com o modelo `llama3.1:8b`, sem internet e sem custo

**Como funciona no `ai.py`:**
```python
USE_LOCAL = os.getenv("USE_LOCAL_LLM", "false").lower() == "true"

if USE_LOCAL:
    from openai import OpenAI as _LocalClient
    client = _LocalClient(base_url="http://localhost:11434/v1", api_key="ollama")
else:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
```

A API do Ollama e compativel com o padrao OpenAI — o restante do codigo nao muda.

**Como configurar o Ollama:**
```bash
# 1. Instalar em ollama.com
# 2. Baixar o modelo
ollama pull llama3.1:8b
# 3. Instalar a lib Python
pip install openai
# 4. Setar no .env
USE_LOCAL_LLM=true
```

| | Groq (producao) | Ollama (testes) |
|---|---|---|
| Custo | Consome TPD (100k/dia) | Zero |
| Velocidade | < 1 segundo | 5–15 seg (CPU) |
| Qualidade | Alta (70b) | Boa (8b) |
| Internet | Necessaria | Nao precisa |

**Modelo de fallback adicionado:** `llama-3.1-8b-instant` reinserido na lista de fallback do modo Groq. Quando o `llama-3.3-70b-versatile` esgota o TPD diario, o servidor cai automaticamente para o modelo menor (500.000 tokens/dia de quota propria) sem interromper o atendimento.

---

### Melhoria — Aba Pendente: botao Concluir simplificado

**Problema anterior:** a aba Pendente tinha dois botoes por item — **Finalizar** (arquivava o agendamento associado via `close_by_phone` + descartava a notificacao) e **Descartar** (abria modal de confirmacao e so removia a notificacao). O fluxo era confuso e o operador precisava de dois passos para uma acao simples.

**Solucao:** os dois botoes foram substituidos por um unico botao verde **Concluir** que remove o item da tela imediatamente — sem modal, sem confirmacao, sem tocar no agendamento.

**Como funciona:**
- Clicar em **Concluir** chama `POST /admin/pending/dismiss` com o `id` do item.
- O item e removido do array `PENDING_ITEMS` em memoria e a tabela e re-renderizada em JS (sem recarregar a pagina).
- O contador da aba Pendente decrementado em tempo real: 24 → 23 → 22...

**Detalhe tecnico:** o botao passa apenas `this` no `onclick` (sem argumentos de string), e a funcao JS `concludePending(btn)` localiza o item pelo indice da linha no DOM — evitando o bug classico de aspas duplas dentro de atributos HTML onclick ao usar `JSON.stringify`.

Tambem foi adicionado o endpoint `POST /admin/completed_by_phone` ao `main.py` (marca o agendamento ativo de um telefone como `completed` sem exigir status `attended`). Nao e usado pelo painel atualmente, mas esta disponivel para uso futuro.

---

## Proximos Passos

### Acesso externo ao painel (custo zero)

**Objetivo:** expor o painel administrativo `http://localhost:8000/painel` para acesso fora da rede local sem custo.

**Contexto:** o ngrok gratuito ja e usado para o webhook do WhatsApp. O plano gratuito do ngrok permite apenas **1 tunnel ativo** simultaneamente — nao da para manter webhook + painel ao mesmo tempo sem pagar.

---

#### Fase 1 — Auditoria (antes de qualquer exposicao)

- [ ] Confirmar se todos os endpoints `/admin/*` exigem autenticacao (header `X-Admin-Token`)
- [ ] Confirmar se o painel HTML faz todas as chamadas com esse header
- [ ] Verificar se o ngrok atual ja expoe o painel (a URL aponta para a porta 8000 inteira)
- [ ] Identificar dados sensiveis visiveis no painel (telefones, nomes, etc.)

---

#### Fase 2 — Escolha da solucao gratuita

| Opcao | URL estavel | Abre porta no roteador | Para quem |
|---|---|---|---|
| **Tailscale** | IP privado fixo | Nao | So voce (1-2 dispositivos) |
| **Cloudflare Tunnel** | Sim (HTTPS) | Nao | Compartilhar com a otica |
| **LocalTunnel** | Parcial | Nao | Testes rapidos |
| **Port forward + DuckDNS** | Sim (dinamico) | **Sim** (risco maior) | Evitar |

- [ ] Decidir entre Tailscale (privado) ou Cloudflare Tunnel (publico com URL estavel)

---

#### Fase 3 — Hardening de seguranca (obrigatorio antes de expor)

- [ ] **Autenticacao no painel HTML:** verificar que o JavaScript do painel envia `X-Admin-Token` em todas as chamadas `fetch` para `/admin/*`
- [ ] **Autenticacao na rota GET `/painel`:** o endpoint que serve o HTML tambem deve exigir o token (ou HTTP Basic Auth) — sem isso, qualquer pessoa com a URL ve o painel
- [ ] **HTTPS:** garantido automaticamente pelo Tailscale ou Cloudflare Tunnel
- [ ] **Rate limiting nos POSTs:** evitar que alguem com a URL cancele agendamentos em massa (biblioteca `slowapi` ou contador simples em memoria)
- [ ] **Mascarar telefones no HTML** se forem exibidos completos (ex: `+55 48 9****-1234`)

> Nivel de risco sem autenticacao + URL publica: **critico**. Nunca expor sem a Fase 3 concluida.

---

#### Fase 4 — Implementacao

**Rota A — Tailscale (acesso privado, sem URL publica):**
1. Instalar Tailscale no Windows (app gratuito em tailscale.com)
2. Instalar no celular ou outro dispositivo que precisar de acesso
3. Login com conta Google — a rede privada e criada automaticamente
4. Painel disponivel via `http://100.x.x.x:8000/painel` (IP Tailscale)
5. Ninguem fora da sua rede Tailscale acessa

**Rota B — Cloudflare Tunnel (URL publica e estavel, HTTPS automatico):**
1. Criar conta gratuita em cloudflare.com
2. Instalar `cloudflared` no Windows
3. Autenticar: `cloudflared tunnel login`
4. Criar tunnel: `cloudflared tunnel create lenzotica`
5. Configurar para apontar para `localhost:8000`
6. Iniciar: `cloudflared tunnel run lenzotica`
7. URL gerada: `https://lenzotica.cfargotunnel.com` (ou dominio proprio)

> Com Cloudflare Tunnel, o webhook do WhatsApp pode continuar usando o ngrok **ou** ser migrado para o mesmo tunnel (rota `/webhook` no mesmo dominio).

---

#### Fase 5 — Testes e validacao

- [ ] Acessar o painel de um dispositivo externo (celular em 4G, fora do Wi-Fi local)
- [ ] Tentar acessar `GET /painel` sem autenticacao — deve retornar 401 ou redirecionar para login
- [ ] Tentar `POST /admin/cancel` sem o token — deve retornar 401
- [ ] Confirmar que o webhook do WhatsApp continua recebendo mensagens normalmente
- [ ] Monitorar o console do servidor por alguns dias para checar acessos suspeitos

---

- [ ] Deploy em servidor real (ex: Railway, Render) para remover a dependencia do ngrok completamente

---

## Licenca

Projeto de uso educacional. Livre para estudo e adaptacao.
