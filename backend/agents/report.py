"""Report Agent — structures findings into a pentest report."""
from backend.agents.base import BaseAgent
from backend.db.repo import findings_repo


class ReportAgent(BaseAgent):
    name = "report"
    description = "Generates structured pentest reports from findings"
    task_type = "reasoning"
    system_prompt = """You are a senior penetration testing report writer.

Given a list of security findings, generate a professional pentest report with:

## EXECUTIVE SUMMARY
Non-technical overview of risk posture (2-3 paragraphs).

## FINDINGS SUMMARY TABLE
| # | Title | Severity | CVSS | Status |

## DETAILED FINDINGS
For each finding:
### [SEVERITY] Finding Title
- **CVSS:** score | **CVE:** id | **MITRE:** technique
- **Description:** technical detail
- **Evidence:** reproduction steps
- **Impact:** business risk
- **Remediation:** specific fix with timeline

## REMEDIATION ROADMAP
Prioritized action plan by severity.

Use professional language. Be specific and technical for the findings section."""

    def can_handle(self, task: str) -> bool:
        keywords = ["report", "findings", "summarize vulnerabilities", "write report"]
        return any(w in task.lower() for w in keywords)

    def prepare(self, task: str, context: dict):
        steps = []
        # Try to load findings from DB
        try:
            user_id = context.get("user_id")
            engagement = context.get("engagement")
            if user_id:
                raw = findings_repo.list(user_id, limit=50)
                if raw:
                    import json
                    context["findings"] = json.dumps(raw, indent=2, default=str)[:8000]
                    steps.append({"step": "findings_loaded", "count": len(raw)})
        except Exception as e:
            steps.append({"step": "findings_load_failed", "error": str(e)})
        return context, steps
