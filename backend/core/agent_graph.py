from __future__ import annotations

from dataclasses import dataclass

from backend.core.state_machine import HermesState


@dataclass(frozen=True)
class AgentNode:
    id: str
    label: str
    description: str
    state: HermesState | None = None


@dataclass(frozen=True)
class AgentLink:
    source: str
    target: str
    states: tuple[HermesState, ...]


AGENT_NODES: tuple[AgentNode, ...] = (
    AgentNode(
        id="client",
        label="Client Intake",
        description="Entry point before the orchestrator hands work to personas.",
        state=HermesState.WAITING_FOR_CLIENT,
    ),
    AgentNode(
        id="po",
        label="Product Owner",
        description="Defines the problem, audience, and outcome.",
        state=HermesState.PO_ANALYSIS,
    ),
    AgentNode(
        id="ba",
        label="Business Analyst",
        description="Turns the request into technical analysis and architecture.",
        state=HermesState.BA_PLANNING,
    ),
    AgentNode(
        id="architect",
        label="Architect",
        description="Clarifies technical boundaries, contracts, and solution tradeoffs.",
        state=HermesState.ARCHITECT_REVIEW,
    ),
    AgentNode(
        id="pm",
        label="Project Manager",
        description="Breaks work into ordered tasks and manages flow.",
        state=HermesState.PM_BREAKDOWN,
    ),
    AgentNode(
        id="dev",
        label="Developer",
        description="Implements code or documentation changes.",
        state=HermesState.DEV_CODING,
    ),
    AgentNode(
        id="ux",
        label="UX/UI Reviewer",
        description="Reviews interaction design, accessibility, and interface quality.",
        state=HermesState.UX_REVIEW,
    ),
    AgentNode(
        id="security",
        label="Security Reviewer",
        description="Reviews auth, secrets, trust boundaries, and delivery risk.",
        state=HermesState.SECURITY_REVIEW,
    ),
    AgentNode(
        id="qa",
        label="QA",
        description="Runs checks and decides whether work loops or passes.",
        state=HermesState.QA_TESTING,
    ),
    AgentNode(
        id="librarian",
        label="Librarian",
        description="Synchronizes and cleans documentation artifacts.",
        state=HermesState.LIBRARIAN_SYNC,
    ),
    AgentNode(
        id="paused",
        label="Paused",
        description="Manual hold mode controlled from the dashboard.",
        state=HermesState.PAUSED,
    ),
)

AGENT_LINKS: tuple[AgentLink, ...] = (
    AgentLink("client", "po", (HermesState.WAITING_FOR_CLIENT,)),
    AgentLink("po", "ba", (HermesState.PO_ANALYSIS,)),
    AgentLink("ba", "architect", (HermesState.BA_PLANNING,)),
    AgentLink("ba", "pm", (HermesState.BA_PLANNING,)),
    AgentLink("architect", "pm", (HermesState.ARCHITECT_REVIEW,)),
    AgentLink("architect", "dev", (HermesState.ARCHITECT_REVIEW,)),
    AgentLink("pm", "architect", (HermesState.PM_BREAKDOWN,)),
    AgentLink("pm", "ux", (HermesState.PM_BREAKDOWN,)),
    AgentLink("pm", "dev", (HermesState.PM_BREAKDOWN,)),
    AgentLink("dev", "architect", (HermesState.DEV_CODING,)),
    AgentLink("dev", "ux", (HermesState.DEV_CODING,)),
    AgentLink("dev", "security", (HermesState.DEV_CODING,)),
    AgentLink("dev", "qa", (HermesState.DEV_CODING,)),
    AgentLink("ux", "pm", (HermesState.UX_REVIEW,)),
    AgentLink("ux", "dev", (HermesState.UX_REVIEW,)),
    AgentLink("security", "dev", (HermesState.SECURITY_REVIEW,)),
    AgentLink("security", "qa", (HermesState.SECURITY_REVIEW,)),
    AgentLink("qa", "pm", (HermesState.QA_TESTING,)),
    AgentLink("qa", "dev", (HermesState.QA_TESTING,)),
    AgentLink("qa", "security", (HermesState.QA_TESTING,)),
    AgentLink("qa", "paused", (HermesState.QA_TESTING,)),
    AgentLink("librarian", "pm", (HermesState.LIBRARIAN_SYNC,)),
    AgentLink("librarian", "paused", (HermesState.LIBRARIAN_SYNC,)),
    AgentLink("client", "paused", (HermesState.WAITING_FOR_CLIENT,)),
    AgentLink("po", "paused", (HermesState.PO_ANALYSIS,)),
    AgentLink("ba", "paused", (HermesState.BA_PLANNING,)),
    AgentLink("architect", "paused", (HermesState.ARCHITECT_REVIEW,)),
    AgentLink("pm", "paused", (HermesState.PM_BREAKDOWN,)),
    AgentLink("dev", "paused", (HermesState.DEV_CODING,)),
    AgentLink("ux", "paused", (HermesState.UX_REVIEW,)),
    AgentLink("security", "paused", (HermesState.SECURITY_REVIEW,)),
    AgentLink("paused", "architect", (HermesState.PAUSED,)),
    AgentLink("paused", "pm", (HermesState.PAUSED,)),
    AgentLink("paused", "dev", (HermesState.PAUSED,)),
    AgentLink("paused", "ux", (HermesState.PAUSED,)),
    AgentLink("paused", "security", (HermesState.PAUSED,)),
    AgentLink("paused", "qa", (HermesState.PAUSED,)),
)

STATE_TO_AGENT_ID = {
    node.state: node.id
    for node in AGENT_NODES
    if node.state is not None
}


def build_agent_graph(current_state: HermesState) -> dict[str, object]:
    current_agent_id = STATE_TO_AGENT_ID[current_state]

    return {
        "currentState": current_state.value,
        "currentAgentId": current_agent_id,
        "nodes": [
            {
                "id": node.id,
                "label": node.label,
                "description": node.description,
                "state": node.state.value if node.state else None,
                "isCurrent": node.id == current_agent_id,
            }
            for node in AGENT_NODES
        ],
        "links": [
            {
                "source": link.source,
                "target": link.target,
                "states": [state.value for state in link.states],
                "isActive": current_state in link.states,
            }
            for link in AGENT_LINKS
        ],
    }
