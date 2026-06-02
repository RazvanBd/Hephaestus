from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Set


class HermesState(str, Enum):
    WAITING_FOR_CLIENT = "WAITING_FOR_CLIENT"
    PO_ANALYSIS = "PO_ANALYSIS"
    BA_PLANNING = "BA_PLANNING"
    ARCHITECT_REVIEW = "ARCHITECT_REVIEW"
    PM_BREAKDOWN = "PM_BREAKDOWN"
    DEV_CODING = "DEV_CODING"
    UX_REVIEW = "UX_REVIEW"
    SECURITY_REVIEW = "SECURITY_REVIEW"
    QA_TESTING = "QA_TESTING"
    LIBRARIAN_SYNC = "LIBRARIAN_SYNC"
    PAUSED = "PAUSED"


@dataclass
class StateMachine:
    current_state: HermesState = HermesState.WAITING_FOR_CLIENT
    graph: Dict[HermesState, Set[HermesState]] = field(
        default_factory=lambda: {
            HermesState.WAITING_FOR_CLIENT: {HermesState.PO_ANALYSIS},
            HermesState.PO_ANALYSIS: {HermesState.BA_PLANNING},
            HermesState.BA_PLANNING: {HermesState.PM_BREAKDOWN, HermesState.ARCHITECT_REVIEW},
            HermesState.ARCHITECT_REVIEW: {HermesState.PM_BREAKDOWN, HermesState.DEV_CODING},
            HermesState.PM_BREAKDOWN: {
                HermesState.DEV_CODING,
                HermesState.ARCHITECT_REVIEW,
                HermesState.UX_REVIEW,
            },
            HermesState.DEV_CODING: {
                HermesState.QA_TESTING,
                HermesState.ARCHITECT_REVIEW,
                HermesState.UX_REVIEW,
                HermesState.SECURITY_REVIEW,
            },
            HermesState.UX_REVIEW: {HermesState.PM_BREAKDOWN, HermesState.DEV_CODING},
            HermesState.SECURITY_REVIEW: {HermesState.DEV_CODING, HermesState.QA_TESTING},
            HermesState.QA_TESTING: {
                HermesState.PM_BREAKDOWN,
                HermesState.DEV_CODING,
                HermesState.SECURITY_REVIEW,
                HermesState.PAUSED,
            },
            HermesState.LIBRARIAN_SYNC: {HermesState.PM_BREAKDOWN, HermesState.PAUSED},
            HermesState.PAUSED: {
                HermesState.ARCHITECT_REVIEW,
                HermesState.PM_BREAKDOWN,
                HermesState.DEV_CODING,
                HermesState.UX_REVIEW,
                HermesState.SECURITY_REVIEW,
                HermesState.QA_TESTING,
            },
        }
    )

    def can_transition(self, to_state: HermesState) -> bool:
        if to_state == HermesState.PAUSED:
            return True
        return to_state in self.graph.get(self.current_state, set())

    def transition(self, to_state: HermesState) -> tuple[HermesState, HermesState]:
        if not self.can_transition(to_state):
            raise ValueError(f"Invalid transition: {self.current_state} -> {to_state}")
        old_state = self.current_state
        self.current_state = to_state
        return old_state, self.current_state
