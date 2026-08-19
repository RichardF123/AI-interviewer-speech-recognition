import re
import time
import uuid

from app.schemas.voice_events import AssistantTextEvent


class SpeechStyleFormatter:
    def clean_for_tts(self, text: str) -> str:
        cleaned = re.sub(r"```.*?```", "", text, flags=re.S)
        cleaned = re.sub(r"[*_#>`-]+", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def to_ssml(self, text: str, voice: str = "zh-CN-XiaoxiaoNeural") -> str:
        safe_text = self.clean_for_tts(text)
        return (
            '<speak version="1.0" xml:lang="zh-CN">'
            f'<voice name="{voice}">'
            '<prosody rate="-8%" pitch="0%">'
            f"{safe_text}"
            "</prosody></voice></speak>"
        )


class InterviewOrchestrator:
    """面试编排占位。

    生产实现应调用 LLM，并把 prompt、rubric、session state 和安全边界纳入上下文。
    """

    def __init__(self) -> None:
        self.formatter = SpeechStyleFormatter()

    async def handle_final_transcript(
        self,
        session_id: str,
        utterance_id: str,
        normalized_text: str,
    ) -> AssistantTextEvent:
        turn_id = f"t_{uuid.uuid4().hex[:8]}"
        text = "好的。那我想继续追问一下，你在这个模块里最关键的一次优化是什么？"
        return AssistantTextEvent(
            session_id=session_id,
            timestamp_ms=int(time.time() * 1000),
            turn_id=turn_id,
            text=text,
        )

