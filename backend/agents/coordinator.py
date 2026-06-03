"""Coordinator — routes tasks to the right agent(s), chains when needed."""
import re
from backend.agents.base import BaseAgent
from backend.agents.recon import ReconAgent
from backend.agents.exploit import ExploitAgent
from backend.agents.ctf import CTFAgent
from backend.agents.report import ReportAgent
from backend.utils.logger import get_logger

log = get_logger("coordinator")

AGENTS = [CTFAgent(), ReconAgent(), ExploitAgent(), ReportAgent()]


def pick_agent(task: str) -> BaseAgent:
    for agent in AGENTS:
        if agent.can_handle(task):
            return agent
    # Default: use ReconAgent for anything with a target IP/domain, else ExploitAgent
    if re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b|\.[a-z]{2,}\b", task):
        return ReconAgent()
    return ExploitAgent()


def run(task: str, agent_name: str = "auto", context: dict = None) -> dict:
    ctx = context or {}
    steps = []

    if agent_name == "auto":
        agent = pick_agent(task)
    else:
        agent_map = {a.name: a for a in AGENTS}
        agent = agent_map.get(agent_name, pick_agent(task))

    log.info(f"[coordinator] task={task[:60]!r} -> agent={agent.name}")
    steps.append({"step": "agent_selected", "agent": agent.name,
                  "reason": "auto-detected" if agent_name == "auto" else "user-selected"})

    result = agent.run(task, ctx)
    steps.extend(result.get("steps", []))

    return {
        "ok": result.get("ok", False),
        "agent": agent.name,
        "task": task,
        "result": result.get("result", result.get("error", "")),
        "steps": steps,
        "error": result.get("error"),
    }
