"""Base agent class — all agents inherit from this."""
from __future__ import annotations
from backend.core import router
from backend.utils.logger import get_logger

log = get_logger("agents")


class BaseAgent:
    name: str = "base"
    description: str = ""
    system_prompt: str = ""
    task_type: str = "security_research"

    def can_handle(self, task: str) -> bool:
        return False

    def run(self, task: str, context: dict = None) -> dict:
        """Run agent. Returns {"agent", "result", "steps", "ok"}."""
        ctx = context or {}
        steps = []
        try:
            # Let subclasses enrich context with pre-LLM steps
            enriched_ctx, pre_steps = self.prepare(task, ctx)
            steps.extend(pre_steps)

            messages = self._build_messages(task, enriched_ctx)
            result = router.chat(messages, task_type=self.task_type)
            steps.append({"step": "llm_response", "provider": result["provider"],
                          "model": result["model"], "elapsed_ms": result["elapsed_ms"]})
            return {"ok": True, "agent": self.name, "result": result["content"], "steps": steps}
        except Exception as e:
            log.error(f"[{self.name}] {e}")
            return {"ok": False, "agent": self.name, "error": str(e), "steps": steps}

    def prepare(self, task: str, context: dict) -> tuple:
        """Override to fetch data before calling LLM. Return (enriched_ctx, steps)."""
        return context, []

    def _build_messages(self, task: str, context: dict) -> list:
        system = self.system_prompt
        # Inject context into system prompt if provided
        if context:
            context_text = "\n\n".join(
                f"=== {k.upper()} ===\n{v}" for k, v in context.items() if v
            )
            if context_text:
                system += f"\n\n--- CONTEXT ---\n{context_text}"
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": task},
        ]
