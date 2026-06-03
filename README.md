# OffSec AI 2025 — Multi-LLM Pentesting Assistant

```
╔══════════════════════════════════════════════════════════╗
║         Elite Offensive Security Suite  v2025.2          ║
║         Multi-LLM · Multi-Agent · Authorized Use         ║
╚══════════════════════════════════════════════════════════╝
```

![CI](https://github.com/YOUR_USERNAME/offsec-ai/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ⚡ Install on Kali Linux (one command)

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/offsec-ai/main/install.sh | sudo bash
```

Then edit your keys and run:

```bash
nano /opt/offsec-ai/.env
cd /opt/offsec-ai && ./run.sh
```

Opens at **http://127.0.0.1:7777**

---

## 🖥️ Quick Start (manual)

```bash
git clone https://github.com/YOUR_USERNAME/offsec-ai.git
cd offsec-ai
cp .env.example .env      # paste your API keys
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

Windows:
```cmd
run.bat
```

---

## 🧠 What's Inside

### Multi-LLM Brain (10+ providers, auto-routing)

| Task | Preferred providers |
|------|---------------------|
| Code / exploit dev | Claude → DeepSeek → OpenAI → Groq |
| CTF solve | Claude → DeepSeek → OpenAI → Groq |
| Fast / cheap | Groq → DeepSeek → Gemini |
| Web-grounded | Perplexity → OpenRouter |
| Long context | Gemini (2M) → Claude |

Providers: **Anthropic · OpenAI · Google Gemini · Groq · DeepSeek · Mistral · OpenRouter · HuggingFace · Together · Cohere · Perplexity · xAI Grok**

### Security Intelligence APIs

| Provider | Capabilities |
|----------|-------------|
| Shodan | Host info, banner search |
| VirusTotal | IP/domain/hash/URL analysis |
| AlienVault OTX | Threat indicators, pulses |
| AbuseIPDB | IP reputation check |
| URLScan | URL scanning and analysis |
| IPInfo | IP geolocation and ASN |
| NVD CVE | CVE lookup and search |
| GitHub | Code search, org recon |
| FullHunt | Domain and subdomain enum |
| LeakIX | Host and service leaks |

### Safety Layers

- **Scope Guard** — strict / permissive / lab modes
- **Encrypted Vault** — Fernet-encrypted credential storage
- **Audit Log** — immutable SQLite audit trail
- **Response Cache** — SHA-keyed, saves API costs
- **Quota Manager** — per-provider rate tracking
- **Retry Logic** — exponential backoff on failures

---

## 🔒 Scope Modes

```bash
# Lab mode — only private IPs + .htb/.thm/.local
POST /api/scope  { "mode": "lab" }

# Strict — only your defined targets
POST /api/scope  { "mode": "strict", "in_scope": ["10.0.0.0/24", "*.acme.com"] }

# Permissive — no restrictions (dev/research)
POST /api/scope  { "mode": "permissive" }
```

---

## 📁 Structure

```
offsec-ai/
├── backend/
│   ├── core/          # AI engine, router, orchestrator, scope guard, cache
│   ├── intelligence/  # Shodan, VT, OTX, URLScan, CVE, GitHub, etc.
│   ├── agents/        # Multi-agent system (Phase 3)
│   ├── modules/       # Attack modules & tool execution (Phase 4+)
│   ├── vault/         # Encrypted credential storage
│   ├── utils/         # Logger, audit, quotas, retry
│   ├── notifications/ # Discord, Slack
│   └── app.py         # Flask + Socket.IO
├── frontend/          # Vanilla HTML/CSS/JS terminal UI
├── database/          # SQLite: chat, audit, findings
├── scripts/           # Systemd service file
├── tests/
├── install.sh         # Kali one-liner installer
├── uninstall.sh
├── run.sh / run.bat / run.py
├── requirements.txt
├── render.yaml        # One-click Render deploy
└── Dockerfile
```

---

## 🎯 API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/chat` | Send prompt, get AI response |
| `GET` | `/api/sessions` | List chat sessions |
| `GET` | `/api/llm/status` | LLM provider health |
| `POST` | `/api/llm/healthcheck` | Ping all LLMs |
| `GET` | `/api/intel/status` | Intel API status |
| `POST` | `/api/intel/<provider>` | Run intel query |
| `GET/POST` | `/api/scope` | Read / update scope |
| `GET` | `/api/audit` | Recent audit events |
| `GET/POST` | `/api/findings` | Findings manager |

---

## 🗺 Roadmap

- ✅ Phase 1 — Foundation (Flask, auth, DB, logging)
- ✅ Phase 2 — AI Engine (12 LLMs, smart router)
- ⏳ Phase 3 — Agents (recon, exploit, CTF, report)
- ⏳ Phase 4 — Kali tool execution (nmap, gobuster, sqlmap)
- ⏳ Phase 5 — Findings + PDF reports
- ⏳ Phase 6 — Dashboard + engagements
- ⏳ Phase 7 — Payload generator + dark web monitoring

---

## 🚀 Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

Or manually:
1. Fork this repo
2. Go to [render.com](https://render.com) → New Web Service → connect repo
3. Render detects `render.yaml` automatically
4. Add your API keys in the Environment tab
5. Deploy

---

## ⚠️ Legal

Authorized testing only. Stay in scope. Document everything.
This tool is for professional penetration testers, CTF players, and security researchers.
