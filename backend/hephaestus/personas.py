from __future__ import annotations

from pathlib import Path

from backend.core.state_machine import HermesState

PERSONA_DOCS: dict[HermesState, str] = {
    HermesState.PO_ANALYSIS: "docs/agents/po_persona.md",
    HermesState.BA_PLANNING: "docs/agents/ba_persona.md",
    HermesState.PM_BREAKDOWN: "docs/agents/pm_persona.md",
    HermesState.DEV_CODING: "docs/agents/dev_persona.md",
    HermesState.QA_TESTING: "docs/agents/qa_persona.md",
    HermesState.LIBRARIAN_SYNC: "docs/agents/librarian_persona.md",
}


def build_persona_prompt(
    *,
    project_root: str,
    task_title: str,
    task_description: str,
    state: HermesState,
    recent_events: list[dict[str, object]],
) -> str:
    base = [
        "You are Hermes execution engine under Hephaestus supervision.",
        f"Current workflow state: {state.value}",
        f"Task title: {task_title}",
        f"Task description: {task_description}",
        "Return XML handoff tags only (<file>, <doc_update>, <execute>, <transition_to>).",
    ]

    doc_path = PERSONA_DOCS.get(state)
    if doc_path:
        full_path = Path(project_root).resolve() / doc_path
        if full_path.exists():
            base.append("Persona contract:")
            base.append(full_path.read_text(encoding="utf-8"))

    if recent_events:
        base.append("Recent run events:")
        for event in recent_events[-6:]:
            base.append(f"- {event.get('event_type')}: {event.get('payload')}")

    return "\n\n".join(base)
