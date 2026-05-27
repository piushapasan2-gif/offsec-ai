# Deploy OffSec AI 2025 to Render

```
╔══════════════════════════════════════════════════════════╗
║  Hybrid Production Stack                                 ║
║    Frontend + Backend  →  Render (Free tier)             ║
║    Database + Auth     →  Supabase                       ║
║    Vault (secrets)     →  Stays LOCAL on disk            ║
╚══════════════════════════════════════════════════════════╝
```

## ✅ Step 1 — Set up Supabase

1. Open https://supabase.com/dashboard → your project
2. Click **SQL Editor** → **New query**
3. Open `backend/db/schema.sql` from this repo, copy everything, paste into the editor
4. Click **RUN** — creates 6 tables with RLS policies
5. Click **Authentication** → **Providers** → enable **Email**
6. Optional: configure email templates (Auth → Email Templates)

You should now see these tables in **Database → Tables**:
`chat_sessions`, `chat_messages`, `audit_log`, `findings`, `engagements`, `assets`

## ✅ Step 2 — Push to GitHub

```bash
cd offsec-ai/
git init
git add .
git commit -m "Initial OffSec AI 2025 commit"
git branch -M main
# create new private repo at github.com/new
git remote add origin git@github.com:YOUR_USER/offsec-ai.git
git push -u origin main
```

⚠ **Verify `.env` is gitignored.** It already is — but double-check `git status` shows no `.env`.

## ✅ Step 3 — Deploy to Render

### Option A: One-click Blueprint (easiest)

1. Open https://dashboard.render.com/
2. Click **New +** → **Blueprint**
3. Connect your GitHub repo
4. Render reads `render.yaml` automatically and creates the web service
5. After "Build complete", go to your new service → **Environment** tab
6. Fill in all the `sync: false` env vars (your API keys and Supabase keys)

### Option B: Manual web service

1. Click **New +** → **Web Service**
2. Connect repo
3. Settings:
   - Build command: `pip install --upgrade pip && pip install -r requirements.txt`
   - Start command: `gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT --timeout 120 wsgi:app`
   - Health check path: `/health`
   - Plan: Free
4. Add environment variables (copy from your local `.env`, plus set `PROD=1` and `STORAGE_BACKEND=supabase`)
5. Click **Create Web Service**

Render builds (3-5 min on first deploy). You'll get a URL like `https://offsec-ai-xxxx.onrender.com`.

## ✅ Step 4 — Allow Render's URL in Supabase Auth

Supabase blocks login redirects from unknown URLs by default.

1. Supabase Dashboard → **Authentication** → **URL Configuration**
2. Add to **Redirect URLs**:
   - `https://your-render-app.onrender.com/`
   - `https://your-render-app.onrender.com/login`
3. Set **Site URL** to your Render URL

## ✅ Step 5 — Test it

1. Open `https://your-render-app.onrender.com/login`
2. Click **Sign up**, enter email/password
3. Check inbox → click verification link
4. Log in
5. You should land on the dashboard, see your LLM/intel providers loaded
6. Try a chat: "What's the latest critical CVE?"

## 🥶 About Render Free Tier Cold Starts

Free instances **spin down after 15 minutes of inactivity**. First request after that takes ~30 seconds.

Mitigation:
- Set up free **UptimeRobot** monitor pinging `/health` every 5 minutes
- Or upgrade to `Starter` ($7/mo) — always-on

```
UptimeRobot setup:
  https://uptimerobot.com/dashboard → Add new monitor
  Type: HTTP(s)
  URL: https://your-app.onrender.com/health
  Interval: 5 minutes
```

## 🔒 Security Hardening (do this!)

1. **Rotate the service_role key** (you pasted it in chat earlier):
   Supabase → Settings → API → "Reset service_role key"
2. **Lock RLS policies** — already done in schema.sql ✔
3. **Enable Supabase email confirmation** — Authentication → Settings → "Enable email confirmations"
4. **Rate limit logins** — Authentication → Rate Limiting (already on by default)
5. **HTTPS only** — Render gives you HTTPS by default ✔

## 🛠 Troubleshooting

| Symptom | Fix |
|---------|-----|
| Build fails on Render | Check `requirements.txt` — try `pip install -r requirements.txt` locally first |
| 401 on every request | Check `SUPABASE_URL` and `SUPABASE_ANON_KEY` env vars match exactly |
| Login button does nothing | Open browser dev console; check `/api/auth/config` returns your URL |
| "missing token" error | Clear localStorage, log in again |
| Slow first request | Cold start (free tier). See UptimeRobot section above. |
| Socket.IO won't connect | Render's free tier supports WebSockets ✔. Check browser console for errors. |

## 🔁 Local Dev Still Works

Your local `run.bat` keeps working. To switch local dev between cloud and SQLite:

```bash
# Use cloud (default since you set STORAGE_BACKEND=supabase)
STORAGE_BACKEND=supabase python run.py

# Use local SQLite (no Supabase needed)
STORAGE_BACKEND=sqlite python run.py
```

## 📈 Next Steps

- Add custom domain: Render → Settings → Custom Domain
- Connect Discord notifications: set `DISCORD_WEBHOOK_URL` (already in your .env)
- Scheduled CVE alerts: see `intelligence/cve_monitor.py` `critical_recent()`
- Multi-user collaboration: turn on Supabase Realtime
