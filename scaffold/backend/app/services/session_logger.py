import logging
from typing import Any


logger = logging.getLogger("interview_voice")


class SessionLogger:
    """结构化日志占位。生产应写入 PostgreSQL，并按授权保存音频对象。"""

    async def persist_event(
        self,
        session_id: str,
        event_type: str,
        payload: dict[str, Any],
        turn_id: str | None = None,
    ) -> None:
        logger.info(
            "voice_event",
            extra={
                "session_id": session_id,
                "turn_id": turn_id,
                "event_type": event_type,
                "payload": payload,
            },
        )

