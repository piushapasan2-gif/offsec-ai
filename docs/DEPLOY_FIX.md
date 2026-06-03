# Deploy Fix — Status 1 Crash

## ❌ What broke
Your deploy at `srv-d8bd1d6l51nc739jpjv0` exited with status 1. Root cause:

**Eventlet was being monkey-patched twice** — once in `wsgi.py` and again by gunicorn's `--worker-class eventlet`. The second patch fails because the runtime is already patched, killing the worker.

## ✅ What I fixed
- `wsgi.py` — removed the manual `eventlet.monkey_patch()` (gunicorn handles it)
- `Procfile` — added `--log-level info` so future errors show up in Render logs

## 🚀 Push and redeploy

```bash
cd "C:\Users\PIUSH\OneDrive\Desktop\2025 offsec tool\Offsec AI Tool 2025\offsec-ai"
git add wsgi.py Procfile requirements.txt
git commit -m "fix: remove double eventlet monkey-patch (Render crash)"
git push
```

Render will auto-redeploy (~2 min). Then **add env vars** (next section).

## 🔑 You MUST add env vars in Render (deploy will still fail without them)

Render Dashboard → your service → **Environment** tab → add these:

### Critical (without these the app crashes immediately)

| Key | Value |
|-----|-------|
| `PROD` | `1` |
| `STORAGE_BACKEND` | `supabase` |
| `PYTHON_VERSION` | `3.11.9` |
| `SUPABASE_URL` | `https://blshugycaplworieocru.supabase.co` |
| `SUPABASE_ANON_KEY` | *(from your local `.env`)* |
| `SUPABASE_SERVICE_KEY` | *(from your local `.env`)* |
| `FLASK_SECRET_KEY` | *(click "Generate Value")* |
| `VAULT_MASTER_KEY` | *(click "Generate Value")* |

### LLM keys (skip empties)

| Key | Source |
|-----|--------|
| `OPENAI_API_KEY`, `GROQ_API_KEY`, `GOOGLE_API_KEY`, `DEEPSEEK_API_KEY` | from `.env` |
| `MISTRAL_API_KEY`, `OPENROUTER_API_KEY`, `HUGGINGFACE_API_KEY` | from `.env` |
| `TOGETHER_API_KEY`, `COHERE_API_KEY`, `XAI_API_KEY` | from `.env` |

### Intel keys
| Key | Source |
|-----|--------|
| `SHODAN_API_KEY`, `OTX_API_KEY`, `ABUSEIPDB_API_KEY` | from `.env` |
| `URLSCAN_API_KEY`, `IPINFO_API_KEY`, `NVD_API_KEY` | from `.env` |
| `FULLHUNT_API_KEY`, `ZOOMEYE_API_KEY`, `LEAKIX_API_KEY` | from `.env` |
| `GITHUB_TOKEN`, `DISCORD_WEBHOOK_URL` | from `.env` |

### 💡 Bulk import trick

Render → Environment → click the **`...`** menu next to "Add Environment Variable" → **Add from .env**.
Open your local `.env` in Notepad, copy ALL contents, paste into Render.

⚠ Before clicking Add: remove `APP_HOST`, `APP_PORT`, and change `PROD=0` → `PROD=1`.

## 🩺 If it STILL fails after fix + env vars

1. Render dashboard → **Logs** tab
2. Copy the last 30 lines (look for "Traceback", "ImportError", "ModuleNotFoundError", "Error:")
3. Paste them back to me

The most common remaining causes (in order of likelihood):

| Symptom in logs | Fix |
|----------------|-----|
| `ModuleNotFoundError: No module named 'backend'` | Your repo has files inside `offsec-ai/` subfolder. Either move them to repo root, or in Render Settings → "Root Directory" set to `offsec-ai` |
| `ImportError: No module named 'eventlet'` | requirements.txt wasn't picked up — push the slim requirements.txt |
| `Worker failed to boot` followed by long Python traceback | Read the traceback line above — usually missing env var |
| `Address already in use` | Use `--bind 0.0.0.0:$PORT` not a fixed port (already fixed in Procfile) |
| Process exits silently (no traceback) | Eventlet monkey-patch issue — confirmed fixed in this update |

## 🧪 Smoke test locally before pushing

```bash
cd offsec-ai
.venv\Scripts\activate   # or source .venv/bin/activate on linux
pip install -r requirements.txt
gunicorn --worker-class eventlet -w 1 --bind 127.0.0.1:8000 wsgi:app
```

Visit http://127.0.0.1:8000/health — should return `{"ok": true, ...}`.
If that works locally, Render should work too.
