from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.job_service import job_service

router = APIRouter(prefix="/ws", tags=["WebSocket"])

@router.websocket("/evidence/{evidence_id}/progress")
async def websocket_progress(websocket: WebSocket, evidence_id: str):
    await websocket.accept()
    job_service.register_ws(evidence_id, websocket)
    try:
        while True:
            # Keep socket alive and receive client pings/messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        job_service.unregister_ws(evidence_id, websocket)
    except Exception:
        job_service.unregister_ws(evidence_id, websocket)
