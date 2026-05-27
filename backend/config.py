"""Central config - loads .env."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _e(k, d=None):
    v = os.getenv(k, d)
    return v if v and v.strip() else None


class Config:
    BASE_DIR = BASE_DIR
    LOG_DIR = BASE_DIR / "logs"
    DB_DIR = BASE_DIR / "database"
    OUTPUT_DIR = BASE_DIR / "output"
    VAULT_DIR = BASE_DIR / "backend" / "vault"

    HOST = _e("APP_HOST", "127.0.0.1")
    PORT = int(_e("APP_PORT", "7777"))
    SECRET_KEY = _e("FLASK_SECRET_KEY") or os.urandom(32).hex()
    LOG_LEVEL = _e("LOG_LEVEL", "INFO")
    PROD = (_e("PROD") or "0") == "1"

    LLM_KEYS = {
        "openai":      _e("OPENAI_API_KEY"),
        "anthropic":   _e("ANTHROPIC_API_KEY"),
        "google":      _e("GOOGLE_API_KEY"),
        "groq":        _e("GROQ_API_KEY"),
        "deepseek":    _e("DEEPSEEK_API_KEY"),
        "mistral":     _e("MISTRAL_API_KEY"),
        "openrouter":  _e("OPENROUTER_API_KEY"),
        "huggingface": _e("HUGGINGFACE_API_KEY"),
        "together":    _e("TOGETHER_API_KEY"),
        "cohere":      _e("COHERE_API_KEY"),
        "perplexity":  _e("PERPLEXITY_API_KEY"),
        "xai":         _e("XAI_API_KEY"),
    }

    INTEL_KEYS = {
        "shodan":         _e("SHODAN_API_KEY"),
        "censys_id":      _e("CENSYS_API_ID"),
        "censys_secret":  _e("CENSYS_API_SECRET"),
        "virustotal":     _e("VIRUSTOTAL_API_KEY"),
        "otx":            _e("OTX_API_KEY"),
        "abuseipdb":      _e("ABUSEIPDB_API_KEY"),
        "securitytrails": _e("SECURITYTRAILS_API_KEY"),
        "urlscan":        _e("URLSCAN_API_KEY"),
        "greynoise":      _e("GREYNOISE_API_KEY"),
        "ipinfo":         _e("IPINFO_API_KEY"),
        "hibp":           _e("HIBP_API_KEY"),
        "hunter":         _e("HUNTER_API_KEY"),
        "nvd":            _e("NVD_API_KEY"),
        "binaryedge":     _e("BINARYEDGE_API_KEY"),
        "fullhunt":       _e("FULLHUNT_API_KEY"),
        "zoomeye":        _e("ZOOMEYE_API_KEY"),
        "leakix":         _e("LEAKIX_API_KEY"),
    }

    GITHUB_TOKEN     = _e("GITHUB_TOKEN")
    DISCORD_WEBHOOK  = _e("DISCORD_WEBHOOK_URL")
    SLACK_WEBHOOK    = _e("SLACK_WEBHOOK_URL")
    TELEGRAM_TOKEN   = _e("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT    = _e("TELEGRAM_CHAT_ID")

    VAULT_MASTER_KEY = _e("VAULT_MASTER_KEY")

    SUPABASE_URL         = _e("SUPABASE_URL")
    SUPABASE_ANON_KEY    = _e("SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_KEY = _e("SUPABASE_SERVICE_KEY")
    STORAGE_BACKEND      = (_e("STORAGE_BACKEND") or "sqlite").lower()

    @classmethod
    def available_llms(cls):
        return [k for k, v in cls.LLM_KEYS.items() if v]

    @classmethod
    def available_intel(cls):
        return [k for k, v in cls.INTEL_KEYS.items() if v]

    @classmethod
    def ensure_dirs(cls):
        for d in (cls.LOG_DIR, cls.DB_DIR, cls.OUTPUT_DIR, cls.VAULT_DIR):
            d.mkdir(parents=True, exist_ok=True)


Config.ensure_dirs()
