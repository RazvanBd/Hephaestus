from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from backend.core.orchestrator import Orchestrator
from backend.core.state_machine import HermesState
from backend.services.llm_gateway import LocalOllamaProvider
from backend.services.session_logger import SessionLogger
from backend.services.workspace_manager import WorkspaceManager

app = FastAPI(title="Hermes Orchestrator")

workspace_manager = WorkspaceManager(project_root=".")
session_logger = SessionLogger(project_root=".")
provider = LocalOllamaProvider()
orchestrator = Orchestrator(
    llm_provider=provider,
    workspace_manager=workspace_manager,
    session_logger=session_logger,
)


@app.on_event("startup")
async def startup() -> None:
    await workspace_manager.initialize_workspace()
    await session_logger.initialize_session()


@app.websocket("/ws/dashboard")
async def dashboard_socket(websocket: WebSocket) -> None:
    await orchestrator.event_bus.connect(websocket)
    await orchestrator.event_bus.publish(
        "StateTransition",
        {"old_state": None, "new_state": HermesState.WAITING_FOR_CLIENT.value},
    )
    try:
        while True:
            message = await websocket.receive_json()
            command = str(message.get("command", "")).upper()
            if command == "PAUSE":
                await orchestrator.pause()
            elif command == "RESUME":
                await orchestrator.resume()
    except WebSocketDisconnect:
        await orchestrator.event_bus.disconnect(websocket)
