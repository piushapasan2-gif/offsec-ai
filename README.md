# OffSec AI 2025 — Multi-LLM Pentesting Assistant

```
╔══════════════════════════════════════════════════════════╗
║         Elite Offensive Security Suite  v2025.2          ║
║         Multi-LLM · Multi-Agent · Authorized Use         ║
╚══════════════════════════════════════════════════════════╝
```

## ⚡ Quick Start

```bash
# Windows
run.bat

# Linux/macOS
chmod +x run.sh && ./run.sh
```

Opens at **http://127.0.0.1:7777**.

## 🧠 What's Inside

### Multi-LLM Brain
10+ LLM providers with automatic task-aware routing + fallback:
- **Anthropic Claude** · **OpenAI** · **Google Gemini** · **Groq** · **DeepSeek**
- **Mistral** · **OpenRouter** · **HuggingFace** · **Together** · **Cohere**
- **Perplexity** · **xAI Grok**

Router picks the best model for the task:
| Task | Preferred providers |
|------|---------------------|
| Code/exploit dev | Claude → DeepSeek → OpenAI → Groq |
| CTF solve | Claude → DeepSeek → OpenAI → Groq |
| Fast/cheap | Groq → DeepSeek → Gemini |
| Web-grounded | Perplexity → OpenRouter |
| Long context | Gemini (2M) → Claude |

### Intelligence APIs
- **Shodan** · **VirusTotal** · **AlienVault OTX** · **AbuseIPDB**
- **URLScan** · **IPInfo** · **NVD CVE** · **GitHub** · **FullHunt** · **LeakIX**

All wrapped with: caching, quota tracking, audit logging.

### Safety / Reliability Layers
- **`core/scope_guard.py`** — enforces in-scope-only targeting (strict / permissive / lab modes)
- **`vault/credentials.py`** — encrypted (Fernet) credential vault for engagement creds
- **`utils/audit_log.py`** — immutable SQLite audit trail
- **`core/cache.py`** — SHA-keyed response cache (saves $$$ on LLM + intel calls)
- **`utils/quota_manager.py`** — per-provider quota tracking
- **`utils/retry.py`** — exponential-backoff retry decorator

## 🛠 Configure

API keys live in `.env`. Empty values are skipped automatically (router and intel routes detect missing keys).

```bash
cp .env.example .env
# edit .env, paste keys for providers you have
```

## 📁 Layout

```
offsec-ai/
├── backend/
│   ├── core/
│   │   ├── ai_engine.py       # 10+ LLM adapters
│   │   ├── router.py          # Smart task→provider routing
│   │   ├── orchestrator.py    # Top-level handler
│   │   ├── memory.py          # SQLite chat history
│   │   ├── scope_guard.py     # Authorization enforcement
│   │   └── cache.py           # Response cache
│   ├── intelligence/          # Shodan, VT, OTX, URLScan, etc.
│   ├── vault/                 # Encrypted credential storage
│   ├── utils/                 # Logger, audit, quotas, retry
│   ├── notifications/         # Discord, Slack
│   ├── modules/               # Attack modules (Phase 4+)
│   ├── agents/                # Multi-agent system (Phase 3)
│   ├── app.py                 # Flask app
│   └── config.py
├── frontend/                  # Vanilla HTML/CSS/JS chat UI
├── database/                  # SQLite: chat, audit, cache, quotas, scope
├── logs/                      # Rotating logs (5MB × 5)
├── tests/
├── docs/
├── .env / .env.example
├── requirements.txt
├── run.py / run.bat / run.sh
└── README.md
```

## 🎯 API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/chat` | Send prompt to AI router |
| `GET`  | `/api/sessions` | List chat sessions |
| `GET`  | `/api/llm/status` | Configured LLM providers |
| `POST` | `/api/llm/healthcheck` | Ping each LLM |
| `GET`  | `/api/intel/status` | Configured intel APIs |
| `POST` | `/api/intel/<provider>` | Call intel API |
| `GET`/`POST` | `/api/scope` | Read/update engagement scope |
| `GET`  | `/api/audit` | Recent audit events |
| `GET`  | `/api/quotas` | Quota usage |

## 🔒 Scope Modes

- **permissive** (default) — no scope enforcement (use for lab/dev)
- **strict** — only targets in current engagement allowed
- **lab** — only private IPs + `.local`/`.lab`/`.test`/`.htb`/`.thm` TLDs allowed

Set via `POST /api/scope`:
```json
{
  "mode": "strict",
  "engagement": "client-acme",
  "in_scope": ["*.acme.com", "10.0.0.0/24"],
  "blocklist": ["prod.acme.com"]
}
```

## 🗺 Build Phases

- ✅ **Phase 1** — Foundation
- ✅ **Phase 2** — AI Engine + Router
- ⏳ **Phase 3** — Agents (recon, exploit, ctf, report, coordinator)
- ⏳ **Phase 4** — Attack modules
- ⏳ **Phase 5** — More intel + dark-web monitoring
- ⏳ **Phase 6** — Reporting + PDF
- ⏳ **Phase 7** — Frontend polish + dashboard

## ⚠ Legal

Authorized testing only. Stay in scope. Document everything.
