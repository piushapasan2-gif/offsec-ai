# Render Environment Variables — Paste These In

## 📋 Step-by-Step

1. Open https://dashboard.render.com/web/srv-d8bd1d6l51nc739jpjv0
2. Left sidebar → **Environment**
3. For each variable below, click **Add Environment Variable**, paste the **Key** and **Value**
4. Click **Save Changes** at the bottom
5. Render will auto-redeploy

---

## 🔑 REQUIRED — Without these the app won't boot

| Key | Value |
|-----|-------|
| `PROD` | `1` |
| `STORAGE_BACKEND` | `supabase` |
| `PYTHON_VERSION` | `3.11.9` |
| `LOG_LEVEL` | `INFO` |
| `FLASK_SECRET_KEY` | *(click "Generate Value" button)* |
| `VAULT_MASTER_KEY` | *(click "Generate Value" button)* |
| `SUPABASE_URL` | `https://blshugycaplworieocru.supabase.co` |
| `SUPABASE_ANON_KEY` | *(your anon key — see your `.env` file)* |
| `SUPABASE_SERVICE_KEY` | *(your service_role key — see your `.env` file)* |

---

## 🧠 LLM PROVIDERS — Add what you have

| Key | Value source |
|-----|--------------|
| `OPENAI_API_KEY` | from `.env` |
| `GOOGLE_API_KEY` | from `.env` |
| `GROQ_API_KEY` | from `.env` |
| `DEEPSEEK_API_KEY` | from `.env` |
| `MISTRAL_API_KEY` | from `.env` |
| `OPENROUTER_API_KEY` | from `.env` |
| `HUGGINGFACE_API_KEY` | from `.env` |
| `TOGETHER_API_KEY` | from `.env` |
| `COHERE_API_KEY` | from `.env` |
| `XAI_API_KEY` | from `.env` |
| `ANTHROPIC_API_KEY` | *(skip if empty)* |
| `PERPLEXITY_API_KEY` | *(skip if empty)* |

---

## 🛰 INTEL APIs — Add what you have

| Key | Value source |
|-----|--------------|
| `SHODAN_API_KEY` | from `.env` |
| `OTX_API_KEY` | from `.env` |
| `ABUSEIPDB_API_KEY` | from `.env` |
| `URLSCAN_API_KEY` | from `.env` |
| `IPINFO_API_KEY` | from `.env` |
| `NVD_API_KEY` | from `.env` |
| `FULLHUNT_API_KEY` | from `.env` |
| `ZOOMEYE_API_KEY` | from `.env` |
| `LEAKIX_API_KEY` | from `.env` |
| `GITHUB_TOKEN` | from `.env` |
| `DISCORD_WEBHOOK_URL` | from `.env` |

---

## 💡 Faster way — Bulk import

Render's Environment tab has a **"Add from .env"** option:

1. Open your local `.env` file in Notepad
2. Select all (Ctrl+A), copy
3. Render Environment tab → click the dropdown next to "Add Environment Variable" → **Add from .env**
4. Paste, click **Add Variables**

⚠ **Important:** Before pasting, manually edit out these lines (they shouldn't go to Render):
- `APP_HOST=127.0.0.1` (Render auto-sets host)
- `APP_PORT=7777` (Render uses $PORT)
- Make sure `PROD=1` and `STORAGE_BACKEND=supabase` are set (not `PROD=0`)

---

## ✅ After Saving Env Vars

1. Render shows "Deploying..." automatically
2. Wait ~2-3 minutes (build is now FAST since we removed heavy SDKs)
3. When status = **Live**, click the URL at the top of the dashboard
4. You'll get the login screen

## 🚨 If still failing

Open Render dashboard → **Logs** tab → copy the **last 30 lines** that contain "Error" or "Traceback" → paste them back to me.
