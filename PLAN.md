# OffSec AI 2025 — Master Build Plan

```
╔══════════════════════════════════════════════════════════════════╗
║   10 MVP Sections · Each Shippable · Kali-Ready · GitHub-Hosted  ║
╚══════════════════════════════════════════════════════════════════╝
```

Each section below is a **self-contained MVP** — finish it, commit it, test it,
then move to the next. Never start a new section with broken code from the previous one.

---

## ✅ CURRENT STATE (Already Built)

Before the plan starts, here is what exists and works:

| Component | Status |
|-----------|--------|
| Flask app + Socket.IO | ✅ Working |
| Supabase auth (JWT middleware) | ✅ Working |
| Multi-LLM engine (12 providers) | ✅ Working |
| Smart task router | ✅ Working |
| Intel APIs (10 providers) | ✅ Working |
| Scope guard (strict/permissive/lab) | ✅ Working |
| Vault (encrypted creds) | ✅ Working |
| Audit log + Quota manager | ✅ Working |
| Basic chat UI | ✅ Working |
| Findings DB (severity/cvss/mitre) | ✅ Working |
| Docker + render.yaml | ✅ Working |
| `backend/agents/` folder | ⚠️ Empty stub |
| `backend/modules/` folder | ⚠️ Empty stub |
| Streaming responses | ❌ Not built |
| Kali tool execution | ❌ Not built |
| PDF reporting | ❌ Not built |
| GitHub Actions CI/CD | ❌ Not built |
| Kali install script | ❌ Not built |

---

## MVP 1 — GitHub Setup + Kali Install

**Goal:** Anyone can `git clone` and be running in under 5 minutes on Kali Linux.

### Tasks

**1.1 — Clean the repo for public GitHub**
- Audit `.gitignore` — confirm `.env`, `*.db`, `logs/`, `__pycache__/`, `.venv/` are all excluded
- Remove any hardcoded secrets from code
- Add `.env.example` with placeholder values for all keys (already exists — review and update)
- Delete `__pycache__/` from git history if committed by accident

**1.2 — Write `install.sh` (Kali one-liner installer)**
```bash
#!/bin/bash
# install.sh — OffSec AI 2025 Kali installer
set -e
echo "[*] Installing OffSec AI 2025..."
sudo apt-get update -qq
sudo apt-get install -y python3 python3-pip python3-venv git curl

git clone https://github.com/YOUR_USERNAME/offsec-ai.git /opt/offsec-ai
cd /opt/offsec-ai

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
echo "[*] Edit /opt/offsec-ai/.env with your API keys, then run:"
echo "    cd /opt/offsec-ai && ./run.sh"
```

**1.3 — Write `uninstall.sh`**
- Removes `/opt/offsec-ai`, service if registered

**1.4 — Systemd service file (`offsec-ai.service`)**
- So the tool auto-starts on Kali boot (optional, for dedicated machines)
```ini
[Unit]
Description=OffSec AI 2025
After=network.target

[Service]
WorkingDirectory=/opt/offsec-ai
ExecStart=/opt/offsec-ai/.venv/bin/gunicorn wsgi:application -w 2 -b 0.0.0.0:7777
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

**1.5 — GitHub Actions CI (`/.github/workflows/ci.yml`)**
```yaml
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - run: python -m pytest tests/ -v
```

**1.6 — Update README.md**
- Add "Install on Kali" section with one-liner
- Add badges (Python version, license, CI status)
- Add screenshot placeholder

**Deliverable:** `git push` → GitHub repo is clean, CI passes, `install.sh` works on fresh Kali.

---

## MVP 2 — Streaming Responses + UI Polish

**Goal:** Responses stream token-by-token instead of waiting for the full reply.
The UI feels fast and professional.

### Why this matters first
The current chat sends one big HTTP response. For slow LLMs on long pentest tasks, users
see nothing for 30+ seconds. Streaming fixes this and makes the tool feel alive.

### Tasks

**2.1 — Add SSE streaming endpoint**
- Add `POST /api/chat/stream` that returns `text/event-stream`
- Each provider's `chat()` needs a `stream=True` variant returning a generator
- Start with Anthropic and OpenAI (both support streaming natively), fall back to
  non-streaming for others

**2.2 — Update `ai_engine.py` — add `stream()` method to each provider**
```python
def stream(self, messages, model=None, temperature=0.7, max_tokens=2048):
    # yields str chunks
    raise NotImplementedError
```
Implement for: `AnthropicProvider`, `OpenAICompatProvider` (covers OpenAI, Groq, DeepSeek, etc.), `GoogleProvider`

**2.3 — Update `orchestrator.py` — add `handle_stream()` function**
- Same logic as `handle()` but calls `router.stream()` and yields chunks
- Saves the full assembled response to DB at end

**2.4 — Update frontend `app.js`**
- Switch chat form to use `fetch()` with `ReadableStream` on `/api/chat/stream`
- Render chunks as they arrive (append to the active message bubble)
- Show provider name + model in message footer once complete
- Keep spinner until first chunk arrives

**2.5 — UI: Session list in sidebar**
- Currently "SESSIONS" is missing from the sidebar
- Add a collapsible session list — click to load a past conversation
- Add "New Chat" button that clears and starts fresh

**2.6 — UI: Copy button on every message**
- Each AI message gets a `[copy]` button
- Code blocks get syntax highlighting (use highlight.js from CDN)

**2.7 — UI: Model selector improvement**
- The `<select id="prefer">` already exists but only shows "auto"
- Populate it from `/api/llm/status` on load so users see real provider names

**Deliverable:** Chat streams. Sessions work. Code in responses is highlighted.

---

## MVP 3 — Intel Dashboard (Full Working)

**Goal:** Every intel API is reachable from the UI with real results displayed cleanly.

### Current gaps
The Intel tab exists but it's basic — one input, raw JSON output. It needs:
- Proper per-provider forms (Shodan needs `host`, URLScan needs a URL, CVE needs a CVE ID)
- Formatted output, not raw JSON
- Quick-lookup buttons that auto-run common queries
- Intel results that can be fed directly into the chat ("Analyze this Shodan result")

### Tasks

**3.1 — Fix/verify all 10 intel modules work end-to-end**
Go through each module and test with real API keys:
- `shodan_intel.py` — host_info, search
- `virustotal.py` — ip_info, domain_info, file_hash_info
- `otx.py` — ip_indicators, domain_indicators
- `abuseipdb.py` — check_ip
- `urlscan.py` — submit, result, search
- `ipinfo.py` — lookup
- `cve_monitor.py` — cve_lookup, search, critical_recent
- `github_intel.py` — code_search, org_recon
- `fullhunt.py` — domain_details, subdomains
- `leakix.py` — host_lookup, search

**3.2 — Add `/api/intel/bulk` endpoint**
- Accept a target (IP/domain/hash) and run all applicable modules against it
- Return aggregated JSON: `{ shodan: {...}, virustotal: {...}, abuseipdb: {...}, ... }`
- Run modules concurrently with `ThreadPoolExecutor`

**3.3 — Frontend: Intel Dashboard tab redesign**
Replace the current raw input/output with:
- Target input at top (IP, domain, or hash)
- "Quick Scan" button → hits `/api/intel/bulk`
- Results shown per-provider in collapsible cards, not raw JSON
- Each card has: provider name, key fields (risk score, country, tags), expand for full data
- "Send to AI" button on each card — injects the result into the chat prompt

**3.4 — Add `GET /api/intel/history`**
- Return last 50 intel lookups from audit log
- Show in a new "Intel History" sub-tab

**Deliverable:** Type an IP/domain → one click → all 10 intel APIs run in parallel → formatted results appear → send to AI for analysis.

---

## MVP 4 — Multi-Agent System

**Goal:** Build the `backend/agents/` system so the tool can autonomously chain
multiple tasks — recon → exploit path → report.

### Architecture
```
Coordinator Agent
├── Recon Agent       (subdomain enum, port scan analysis, OSINT)
├── Exploit Agent     (CVE mapping, PoC search, payload generation)
├── CTF Agent         (category detection, step-by-step solve)
└── Report Agent      (formats findings into structured output)
```

### Tasks

**4.1 — Base agent class (`backend/agents/base.py`)**
```python
class BaseAgent:
    name: str
    description: str
    
    def run(self, task: str, context: dict) -> dict:
        # calls orchestrator.handle() with specialized system prompt
        raise NotImplementedError
    
    def can_handle(self, task: str) -> bool:
        raise NotImplementedError
```

**4.2 — Recon Agent (`backend/agents/recon.py`)**
- System prompt: expert OSINT/recon specialist
- Integrates intel APIs automatically — detects if task mentions an IP/domain,
  runs bulk intel, appends results to context before calling LLM
- Tools: subdomain enumeration (via LLM + FullHunt), port scan interpretation,
  Shodan banner analysis

**4.3 — Exploit Agent (`backend/agents/exploit.py`)**
- System prompt: exploit dev + vuln research expert
- On CVE mention → auto-run `cve_monitor.cve_lookup()` and inject details
- Generates working PoC code, not pseudocode
- References ExploitDB, Metasploit modules by name

**4.4 — CTF Agent (`backend/agents/ctf.py`)**
- System prompt: CTF specialist (pwn, web, crypto, forensics, rev)
- Detects challenge category from description
- Provides tool commands + Python solver scripts
- Outputs: category, difficulty estimate, approach, solution steps, flag pattern

**4.5 — Report Agent (`backend/agents/report.py`)**
- Takes a list of findings from DB
- Structures them into: Executive Summary, Methodology, Findings (by severity),
  Remediation Recommendations
- Outputs markdown (for preview) and raw data (for PDF in MVP 6)

**4.6 — Coordinator (`backend/agents/coordinator.py`)**
- Decides which agent(s) to invoke based on the user's message
- Can chain agents: "Run a full recon on target.com" →
  Recon Agent → results fed to Exploit Agent → findings saved
- Exposes a single `run(task, context)` interface

**4.7 — New API endpoint: `POST /api/agents/run`**
```json
{ "task": "Full recon on target.com", "mode": "auto" }
```
Returns: `{ "agent": "coordinator", "steps": [...], "result": "..." }`

**4.8 — Frontend: Agents tab**
- New tab in right pane: "AGENTS"
- Dropdown: Auto / Recon / Exploit / CTF / Report
- Task input + "RUN AGENT" button
- Shows each agent step as it executes (via Socket.IO events)
- Results appear in chat pane

**Deliverable:** User types "Full recon on 10.10.10.5", coordinator picks recon agent,
intel APIs run automatically, LLM synthesizes findings, results shown step-by-step.

---

## MVP 5 — Kali Tool Execution Engine

**Goal:** The tool can run actual Kali Linux tools, parse their output, and feed
results to the AI for analysis. This is the "Kali integration" core feature.

### Tools to integrate (in priority order)
1. **nmap** — port scanning, service detection, OS detection
2. **gobuster / ffuf** — directory and subdomain fuzzing
3. **sqlmap** — SQL injection detection
4. **nikto** — web server scanner
5. **hydra** — brute force (lab mode only)
6. **whatweb** — web tech fingerprinting
7. **theHarvester** — OSINT email/domain harvesting

### Tasks

**5.1 — Tool executor (`backend/modules/tool_executor.py`)**
```python
import subprocess, shlex, threading

class ToolExecutor:
    ALLOWED_TOOLS = ["nmap", "gobuster", "ffuf", "sqlmap", "nikto", 
                     "whatweb", "theharvester"]
    
    def run(self, tool: str, args: str, timeout: int = 300) -> dict:
        # Validates tool is in ALLOWED_TOOLS
        # Validates target is in scope via scope_guard
        # Runs subprocess with timeout
        # Returns { stdout, stderr, returncode, elapsed_ms }
    
    def stream(self, tool: str, args: str):
        # Generator: yields lines as they come from subprocess
```

**5.2 — Nmap module (`backend/modules/nmap_module.py`)**
- Preset scan profiles: Quick (`-T4 -F`), Full (`-T4 -p-`), Version (`-sV -sC`), Stealth (`-sS`)
- XML output parser → structured dict (hosts, ports, services, OS)
- AI summary: feed parsed results to LLM for "what's interesting here?"

**5.3 — Gobuster/FFUF module (`backend/modules/fuzz_module.py`)**
- Common wordlist paths for Kali: `/usr/share/wordlists/dirbuster/`, `/usr/share/seclists/`
- Parses output → list of found paths with status codes
- Auto-feeds to LLM: "Which of these paths look interesting?"

**5.4 — SQLmap module (`backend/modules/sqlmap_module.py`)**
- Preset options: detection only vs. extraction
- Scope guard enforces target is in-scope before running
- Parses vulnerability findings

**5.5 — Scope guard integration**
- Every tool execution MUST pass scope check first
- If scope mode is `strict` and target not in `in_scope` list → reject
- All executions logged to audit trail with full command

**5.6 — New API endpoints**
- `GET /api/tools/available` — list tools installed on the system (checks `which` for each)
- `POST /api/tools/run` — run a tool: `{ tool, args, target }`
- `GET /api/tools/run/<job_id>` — get job status/output
- Socket.IO: emit `tool_output` events line-by-line during execution

**5.7 — Frontend: Tools tab**
- New tab: "TOOLS"
- Dropdown of available tools (those installed on the system)
- Scan profile presets for nmap
- Target input (pre-filled from scope)
- Live output terminal (lines stream in via Socket.IO)
- "Analyze with AI" button at end of scan

**Deliverable:** Click nmap quick scan on a target → output streams live in UI →
"Analyze" sends results to AI → AI identifies interesting ports and suggests next steps.

---

## MVP 6 — Findings Manager + PDF Reports

**Goal:** All discovered vulnerabilities are tracked in a proper findings database
and can be exported as a professional pentest report PDF.

### Current state
`findings_repo` exists in the DB with: title, severity, description, evidence,
engagement, cvss, cve_ids, mitre. The API endpoints exist. The UI has **nothing** for it yet.

### Tasks

**6.1 — Findings UI tab**
Add a "FINDINGS" tab to the right pane:
- Table view: severity badge (Critical/High/Medium/Low/Info), title, engagement, date
- Click a finding → expand to full detail view
- "Add Finding" form (manual entry)
- "Auto-extract" button — scans the current chat session and asks AI to identify
  and extract any vulnerabilities mentioned

**6.2 — AI auto-extraction from chat**
New endpoint `POST /api/findings/extract`:
- Takes a `session_id`
- Sends the full session history to the LLM with prompt:
  "Extract all security vulnerabilities mentioned. Return JSON array with:
   title, severity (critical/high/medium/low/info), description, evidence,
   cvss_score, cve_ids, mitre_technique"
- Auto-creates findings in DB from the AI response

**6.3 — Findings severity statistics endpoint**
`GET /api/findings/stats` → `{ critical: 2, high: 5, medium: 8, low: 3, info: 1 }`

**6.4 — Markdown report generator (`backend/agents/report.py` — from MVP 4)**
Input: list of findings from DB for a given engagement
Output: full markdown report with sections:
```markdown
# Penetration Test Report
## Executive Summary
## Scope & Methodology  
## Findings
### [CRITICAL] SQL Injection in /api/login
**CVSS:** 9.8 | **CVE:** CVE-2024-XXXX | **MITRE:** T1190
**Description:** ...
**Evidence:** ...
**Remediation:** ...
## Appendix
```

**6.5 — PDF export (`backend/modules/report_pdf.py`)**
- Use `reportlab` or `weasyprint` to convert the markdown report to PDF
- Include: cover page (engagement name, date, assessor), TOC, findings sorted by severity,
  severity distribution chart
- Add `reportlab` or `weasyprint` to `requirements.txt`
- New endpoint: `GET /api/findings/report/pdf?engagement=...` → returns PDF download

**6.6 — Frontend: Report generation button**
In the Findings tab:
- "Generate Report" → asks for engagement name → calls report endpoint
- Shows markdown preview inline
- "Download PDF" button

**Deliverable:** After a pentest session, click "Generate Report" →
all findings auto-formatted → download professional PDF.

---

## MVP 7 — Dashboard + Engagement Manager

**Goal:** A proper home dashboard giving a full picture of current engagements,
findings summary, LLM usage stats, and recent activity.

### Tasks

**7.1 — Dashboard route (`/dashboard`)**
- New page served at `/dashboard`
- Auto-redirect there after login (currently goes straight to chat)

**7.2 — Dashboard widgets**
- **Engagement selector** — create/switch engagements (currently scope only supports one)
- **Findings summary** — donut chart of severity distribution (use Chart.js from CDN)
- **Recent activity** — last 10 audit events
- **LLM usage** — bar chart of calls per provider this week (from audit log)
- **Intel lookups** — count per provider
- **Active sessions** — list of recent chat sessions with message count

**7.3 — Multi-engagement support**
Current scope_guard only holds one engagement at a time.
Add `engagement_id` as a column on: sessions, findings, audit_log.
`GET /api/engagements` — list all engagements
`POST /api/engagements` — create new
`PUT /api/engagements/:id` — update scope/targets

**7.4 — Settings page (`/settings`)**
- LLM provider health check (button that pings all providers)
- Intel API status (green/red dots)
- Scope mode selector (permissive / strict / lab)
- Vault: add/view/delete stored credentials (encrypted, never shown in plaintext)

**7.5 — Mobile-responsive layout**
- The current 3-pane layout breaks on mobile
- Add a hamburger menu + collapsible sidebar for screens < 768px

**Deliverable:** Login → Dashboard shows engagement overview → navigate to Chat,
Findings, or Settings from the sidebar.

---

## MVP 8 — Payload & Wordlist Generator

**Goal:** The AI generates custom payloads, wordlists, and attack scripts
tailored to the specific target context.

### Tasks

**8.1 — Payload generator module (`backend/modules/payload_gen.py`)**
Categories:
- **Web** — XSS payloads (DOM, reflected, stored), SQLi payloads, SSTI, SSRF, XXE, path traversal
- **Network** — Reverse shell one-liners (bash, python, powershell, php, ruby, nc)
- **Phishing** — Email templates, pretexts (never for actual phishing — lab/awareness only)
- **Custom** — AI-generated based on target tech stack

**8.2 — Wordlist generator (`backend/modules/wordlist_gen.py`)**
- Target-aware wordlists: given a company name + industry, generate likely:
  - Usernames (firstname.lastname, first initial + last name, etc.)
  - Passwords (company name + year, common patterns)
  - Subdomain names (dev., staging., vpn., mail., etc.)
  - Directory names based on detected tech stack

**8.3 — New API endpoint: `POST /api/generate/payload`**
```json
{
  "type": "reverse_shell",
  "options": { "ip": "10.10.14.1", "port": 4444, "shell": "bash" }
}
```

**8.4 — New API endpoint: `POST /api/generate/wordlist`**
```json
{
  "type": "subdomain",
  "context": { "company": "acme", "industry": "finance" }
}
```

**8.5 — Frontend: Generator tab**
- "GENERATE" tab in right pane
- Type selector (payload type or wordlist type)
- Context inputs (vary by type)
- Generated output in a copy-able text box
- Download as `.txt` button

**Deliverable:** Select "Reverse Shell" → enter LHOST/LPORT → get 10 variants
(bash, python, powershell, etc.) ready to copy-paste.

---

## MVP 9 — Dark Web & Leak Monitoring

**Goal:** Monitor paste sites and breach databases for mentions of target assets.

### Tasks

**9.1 — LeakIX integration (already in intel module — wire up properly)**
- `leakix.py` exists, ensure search by domain returns structured leak events
- Add to bulk intel scan from MVP 3

**9.2 — HaveIBeenPwned module (`backend/intelligence/hibp.py`)**
- Check email addresses against HIBP breach database
- Endpoint: `POST /api/intel/hibp` with `{ "email": "..." }`

**9.3 — DeHashed module (`backend/intelligence/dehashed.py`)**
- Search for credentials by domain, email, username, IP
- Requires DeHashed API key (paid service — document this)

**9.4 — Paste monitor (`backend/intelligence/paste_monitor.py`)**
- Search Pastebin, GitHub Gist, and similar for target domain/IP mentions
- Via Google dorks (using Perplexity/web-grounded LLM) and direct paste APIs

**9.5 — Scheduled monitoring**
- New endpoint: `POST /api/monitor/target` — register a target for periodic checks
- Background thread checks every N hours, saves findings, Discord notification on hit
- `GET /api/monitor/alerts` — list triggered alerts

**9.6 — Discord notification (enhance existing `backend/notifications/discord.py`)**
- Current discord.py exists — ensure it sends rich embeds (not plain text)
- Embed format: target, finding type, severity, source, timestamp

**Deliverable:** Add a domain to monitoring → get Discord alert when it appears in a leak or paste site.

---

## MVP 10 — Production Hardening + GitHub Release

**Goal:** The tool is battle-hardened, documented, and released on GitHub with a
proper version tag and all features working end-to-end.

### Tasks

**10.1 — End-to-end test suite (`tests/`)**
Write pytest tests for every API endpoint:
- `test_chat.py` — mock LLM, test orchestrator pipeline
- `test_intel.py` — mock intel APIs, test each module
- `test_scope.py` — test all three scope modes
- `test_agents.py` — test coordinator routing
- `test_tools.py` — test tool executor with mock subprocess

**10.2 — Rate limiting**
Add `flask-limiter` to protect `/api/chat`:
```python
from flask_limiter import Limiter
limiter = Limiter(app, key_func=current_user_id, default_limits=["60/minute"])
```

**10.3 — Docker Compose (`docker-compose.yml`)**
```yaml
services:
  offsec-ai:
    build: .
    ports: ["7777:7777"]
    env_file: .env
    volumes:
      - ./database:/app/database
      - ./logs:/app/logs
```
One command: `docker-compose up -d`

**10.4 — GitHub Releases workflow**
`.github/workflows/release.yml` — on push to `v*` tag:
- Run tests
- Build Docker image
- Push to GitHub Container Registry (`ghcr.io`)
- Create GitHub Release with changelog

**10.5 — Security audit**
- Ensure no API keys ever appear in responses or logs
- SQL injection protection in all DB queries (already using parameterized — verify)
- CORS locked down in production mode
- Secrets never logged even at DEBUG level
- `.env` verified in `.gitignore` (double-check)

**10.6 — Full documentation**
- `docs/INSTALL.md` — full install guide (Kali, Docker, bare metal)
- `docs/API.md` — all endpoints documented with curl examples
- `docs/AGENTS.md` — how the multi-agent system works
- `docs/TOOLS.md` — which Kali tools are integrated and how

**10.7 — GitHub repo polish**
- `README.md` with screenshot GIF
- Topics/tags: `pentesting`, `osint`, `llm`, `kali-linux`, `security`
- License file (`MIT` recommended for open source, or private)
- `CONTRIBUTING.md` if open-sourcing

**Deliverable:** `git tag v1.0.0 && git push --tags` → CI runs → Docker image published →
GitHub Release created → tool is publicly deployable with one command.

---

## Build Order Summary

```
MVP 1  → GitHub + Kali install (2-3 days)
MVP 2  → Streaming + UI polish (2-3 days)
MVP 3  → Intel dashboard (2 days)
MVP 4  → Multi-agent system (4-5 days)
MVP 5  → Kali tool execution (3-4 days)  ← BIG VALUE
MVP 6  → Findings + PDF reports (2-3 days)
MVP 7  → Dashboard + engagements (3 days)
MVP 8  → Payload generator (2 days)
MVP 9  → Dark web monitoring (2-3 days)
MVP 10 → Production hardening (2-3 days)
────────────────────────────────────────
Total estimate: ~25-30 development days
```

## Priority if time-constrained

If you only have time for half the plan, do **MVP 1, 2, 3, 4, 5** in order.
Those five give you: clean GitHub install → streaming chat → full intel → agents → tool execution.
That is the core product. Everything else (PDF, dashboard, dark web) is enhancement.

---

## File Creation Checklist

Track every new file this plan requires:

### MVP 1
- [ ] `install.sh`
- [ ] `uninstall.sh`
- [ ] `offsec-ai.service`
- [ ] `.github/workflows/ci.yml`

### MVP 2
- [ ] `backend/core/streaming.py` (SSE helpers)
- [ ] Updated `backend/core/ai_engine.py` (stream methods)
- [ ] Updated `backend/core/orchestrator.py` (handle_stream)
- [ ] Updated `frontend/js/app.js` (streaming fetch)

### MVP 3
- [ ] Updated `frontend/index.html` (intel dashboard redesign)
- [ ] `GET /api/intel/bulk` in `backend/app.py`
- [ ] `GET /api/intel/history` in `backend/app.py`

### MVP 4
- [ ] `backend/agents/__init__.py`
- [ ] `backend/agents/base.py`
- [ ] `backend/agents/recon.py`
- [ ] `backend/agents/exploit.py`
- [ ] `backend/agents/ctf.py`
- [ ] `backend/agents/report.py`
- [ ] `backend/agents/coordinator.py`

### MVP 5
- [ ] `backend/modules/__init__.py`
- [ ] `backend/modules/tool_executor.py`
- [ ] `backend/modules/nmap_module.py`
- [ ] `backend/modules/fuzz_module.py`
- [ ] `backend/modules/sqlmap_module.py`

### MVP 6
- [ ] `backend/modules/report_pdf.py`
- [ ] `reportlab` added to `requirements.txt`

### MVP 7
- [ ] `frontend/dashboard.html`
- [ ] `frontend/settings.html`
- [ ] `backend/db/engagements_repo.py`

### MVP 8
- [ ] `backend/modules/payload_gen.py`
- [ ] `backend/modules/wordlist_gen.py`

### MVP 9
- [ ] `backend/intelligence/hibp.py`
- [ ] `backend/intelligence/dehashed.py`
- [ ] `backend/intelligence/paste_monitor.py`

### MVP 10
- [ ] `tests/test_chat.py`
- [ ] `tests/test_intel.py`
- [ ] `tests/test_scope.py`
- [ ] `tests/test_agents.py`
- [ ] `tests/test_tools.py`
- [ ] `docker-compose.yml`
- [ ] `.github/workflows/release.yml`
- [ ] `docs/INSTALL.md`
- [ ] `docs/API.md`
- [ ] `docs/AGENTS.md`
- [ ] `docs/TOOLS.md`
