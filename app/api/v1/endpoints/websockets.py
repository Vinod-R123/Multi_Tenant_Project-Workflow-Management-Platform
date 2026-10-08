import logging
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from app.core.security import decode_token
from app.core.websocket_manager import ws_manager
from app.db.session import SessionLocal
from app.models.organization_member import OrganizationMember
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSockets"])


@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(...),
    org_id: int = Query(...)
):
    db = SessionLocal()
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=1008, reason="Invalid token type")
            return

        user_id = int(payload.get("sub", 0))
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            await websocket.close(code=1008, reason="User inactive or not found")
            return

        if not user.is_super_admin:
            member = (
                db.query(OrganizationMember)
                .filter(
                    OrganizationMember.organization_id == org_id,
                    OrganizationMember.user_id == user_id,
                    OrganizationMember.is_active == True
                )
                .first()
            )
            if not member:
                await websocket.close(code=1008, reason="Not an active member of organization")
                return

    except Exception as e:
        logger.warning(f"WebSocket auth failed: {e}")
        await websocket.close(code=1008, reason="Authentication failed")
        return
    finally:
        db.close()

    await ws_manager.connect(websocket, user_id, org_id)
    try:
        while True:
            # Keep connection alive, listen for client pings or messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id, org_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket, user_id, org_id)
