# Hermes Orchestrator - State Machine & Event Bus

## States
`WAITING_FOR_CLIENT`, `PO_ANALYSIS`, `BA_PLANNING`, `PM_BREAKDOWN`, `DEV_CODING`, `QA_TESTING`, `LIBRARIAN_SYNC`, `PAUSED`.

## Event Bus events
- `AgentTriggered`
- `PromptAssembled`
- `LLMResponseReceived`
- `FileModified`
- `StateTransition`
- `CommandExecuted`
