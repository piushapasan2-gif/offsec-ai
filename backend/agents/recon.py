"""Recon Agent — OSINT + target intelligence specialist."""
import re, importlib, ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed
from backend.agents.base import BaseAgent
from backend.config import Config


class ReconAgent(BaseAgent):
    name = "recon"
    description = "OSINT and target reconnaissance specialist"
    task_type = "security_research"
    system_prompt = """You are an elite OSINT and reconnaissance specialist.

Given a target and intelligence data, provide:
1. ATTACK SURFACE SUMMARY — key exposed services, ports, technologies
2. HIGH-VALUE TARGETS — most interesting findings (open ports, admin panels, leaks)
3. RISK ASSESSMENT — what's exploitable and why
4. RECOMMENDED NEXT STEPS — specific tools and techniques to go deeper
5. MITRE ATT&CK TECHNIQUES — relevant initial access / discovery techniques

Be specific. Use the provided intel data. No vague advice — give exact commands."""

    def can_handle(self, task: str) -> bool:
        keywords = ["recon", "scan", "enumerate", "osint", "footprint",
                    "subdomain", "discover", "map", "fingerprint"]
        return any(w in task.lower() for w in keywords)

    def prepare(self, task: str, context: dict):
        steps = []
        target = self._extract_target(task) or context.get("target")
        if not target:
            return context, steps

        steps.append({"step": "target_detected", "target": target})
        intel = self._bulk_intel(target)
        steps.append({"step": "intel_scan", "providers_ran": list(intel.keys()),
                      "target": target})

        # Build context from intel
        intel_summary = {}
        for provider, result in intel.items():
            if result.get("ok"):
                intel_summary[provider] = str(result["data"])[:2000]
            else:
                intel_summary[provider] = f"Error: {result.get('error', 'failed')}"

        context["target"] = target
        context["intel"] = "\n".join(
            f"[{p.upper()}] {v}" for p, v in intel_summary.items()
        )
        return context, steps

    def _extract_target(self, task: str) -> str | None:
        # IPv4
        m = re.search(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b", task)
        if m:
            return m.group(1)
        # Domain
        m = re.search(r"\b([a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9]\.[a-zA-Z]{2,})\b", task)
        if m:
            return m.group(1)
        return None

    def _bulk_intel(self, target: str) -> dict:
        def is_ip(t):
            try: ipaddress.ip_address(t); return True
            except: return False

        key = lambda k: bool(Config.INTEL_KEYS.get(k))

        if is_ip(target):
            tasks = {}
            if key("shodan"):    tasks["shodan"]     = ("shodan_intel", "host_info",       {"ip": target})
            if key("abuseipdb"): tasks["abuseipdb"]  = ("abuseipdb",    "check_ip",        {"ip": target})
            if key("ipinfo"):    tasks["ipinfo"]      = ("ipinfo",       "lookup",          {"ip": target})
            if key("otx"):       tasks["otx"]         = ("otx",          "ip_indicators",   {"ip": target})
        else:
            tasks = {}
            if key("fullhunt"):  tasks["fullhunt"]    = ("fullhunt",     "domain_details",  {"domain": target})
            if key("urlscan"):   tasks["urlscan"]     = ("urlscan",      "search",          {"query": target})
            if key("otx"):       tasks["otx"]         = ("otx",          "domain_indicators",{"domain": target})

        results = {}
        def run_one(name, mod, fn, args):
            try:
                m = importlib.import_module(f"backend.intelligence.{mod}")
                return name, {"ok": True, "data": getattr(m, fn)(**args)}
            except Exception as e:
                return name, {"ok": False, "error": str(e)}

        with ThreadPoolExecutor(max_workers=5) as ex:
            futs = {ex.submit(run_one, n, mod, fn, args): n
                    for n, (mod, fn, args) in tasks.items()}
            for f in as_completed(futs, timeout=25):
                name, res = f.result()
                results[name] = res
        return results
