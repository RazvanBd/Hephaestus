from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.core.state_machine import HermesState


@dataclass(frozen=True)
class PersonaDefinition:
    name: str
    doc_path: str
    responsibility: str
    consult_when: str
    handoff_targets: tuple[HermesState, ...]


PERSONA_REGISTRY: dict[HermesState, PersonaDefinition] = {
    HermesState.PO_ANALYSIS: PersonaDefinition(
        name="Product Owner",
        doc_path="docs/agents/po_persona.md",
        responsibility="Defines the user problem, outcome, and scope.",
        consult_when="Use for product framing before technical analysis starts.",
        handoff_targets=(HermesState.BA_PLANNING,),
    ),
    HermesState.BA_PLANNING: PersonaDefinition(
        name="Business Analyst",
        doc_path="docs/agents/ba_persona.md",
        responsibility="Turns the request into technical specifications and delivery inputs.",
        consult_when="Use when requirements need structure before planning or coding.",
        handoff_targets=(HermesState.ARCHITECT_REVIEW, HermesState.PM_BREAKDOWN),
    ),
    HermesState.ARCHITECT_REVIEW: PersonaDefinition(
        name="Solution Architect",
        doc_path="docs/agents/architect_persona.md",
        responsibility="Clarifies architecture, contracts, boundaries, and tradeoffs.",
        consult_when="Use when BA, PM, Dev, or QA need missing technical direction.",
        handoff_targets=(HermesState.PM_BREAKDOWN, HermesState.DEV_CODING),
    ),
    HermesState.PM_BREAKDOWN: PersonaDefinition(
        name="Project Manager",
        doc_path="docs/agents/pm_persona.md",
        responsibility="Splits work into sequenced deliverable tasks.",
        consult_when="Use when implementation needs clarified scope, ordering, or ownership.",
        handoff_targets=(
            HermesState.ARCHITECT_REVIEW,
            HermesState.UX_REVIEW,
            HermesState.DEV_CODING,
        ),
    ),
    HermesState.DEV_CODING: PersonaDefinition(
        name="Developer",
        doc_path="docs/agents/dev_persona.md",
        responsibility="Implements the requested code and documentation changes.",
        consult_when="Use for execution after planning is clear enough to build.",
        handoff_targets=(
            HermesState.ARCHITECT_REVIEW,
            HermesState.UX_REVIEW,
            HermesState.SECURITY_REVIEW,
            HermesState.QA_TESTING,
        ),
    ),
    HermesState.UX_REVIEW: PersonaDefinition(
        name="UX/UI Reviewer",
        doc_path="docs/agents/ux_persona.md",
        responsibility="Validates user journeys, accessibility, clarity, and interface fit.",
        consult_when="Use when the feature needs interaction or usability guidance.",
        handoff_targets=(HermesState.PM_BREAKDOWN, HermesState.DEV_CODING),
    ),
    HermesState.SECURITY_REVIEW: PersonaDefinition(
        name="Security Reviewer",
        doc_path="docs/agents/security_persona.md",
        responsibility="Checks auth, permissions, input safety, secrets, and operational risk.",
        consult_when="Use before QA or whenever a change could introduce security regressions.",
        handoff_targets=(HermesState.DEV_CODING, HermesState.QA_TESTING),
    ),
    HermesState.QA_TESTING: PersonaDefinition(
        name="QA",
        doc_path="docs/agents/qa_persona.md",
        responsibility="Runs validation and decides whether work loops or is ready for approval.",
        consult_when="Use after implementation and specialist reviews need end-to-end verification.",
        handoff_targets=(
            HermesState.PM_BREAKDOWN,
            HermesState.DEV_CODING,
            HermesState.SECURITY_REVIEW,
        ),
    ),
    HermesState.LIBRARIAN_SYNC: PersonaDefinition(
        name="Librarian",
        doc_path="docs/agents/librarian_persona.md",
        responsibility="Keeps markdown documentation synchronized and cleaned up.",
        consult_when="Use when the workflow needs documentation-only consolidation.",
        handoff_targets=(HermesState.PM_BREAKDOWN,),
    ),
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
        "You may consult another agent by returning <transition_to>STATE</transition_to> when that specialty is needed.",
    ]

    definition = PERSONA_REGISTRY.get(state)
    if definition:
        base.append("Agent roster:")
        for persona_state, persona in PERSONA_REGISTRY.items():
            targets = ", ".join(target.value for target in persona.handoff_targets)
            base.append(
                f"- {persona_state.value} — {persona.name}: {persona.responsibility} "
                f"Consult when: {persona.consult_when} Handoff targets: {targets}."
            )

        full_path = Path(project_root).resolve() / definition.doc_path
        if full_path.exists():
            base.append("Persona contract:")
            base.append(full_path.read_text(encoding="utf-8"))

    if recent_events:
        base.append("Recent run events:")
        for event in recent_events[-6:]:
            base.append(f"- {event.get('event_type')}: {event.get('payload')}")

    return "\n\n".join(base)
