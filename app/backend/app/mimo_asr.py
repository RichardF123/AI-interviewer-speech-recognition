import base64
import io
import json
import wave
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import settings


class MimoAsrError(RuntimeError):
    pass


def pcm16le_to_wav(pcm_data: bytes, sample_rate: int = 16000, channels: int = 1) -> bytes:
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)
    return wav_buffer.getvalue()


def _extract_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
            elif isinstance(item, str):
                parts.append(item)
        return "".join(parts).strip()
    return ""


class MimoAsrClient:
    def transcribe_pcm(self, pcm_data: bytes, sample_rate: int = 16000, channels: int = 1) -> str:
        if not settings.mimo_api_key:
            raise MimoAsrError("MIMO_API_KEY is not configured")
        if not pcm_data:
            return ""

        wav_data = pcm16le_to_wav(pcm_data, sample_rate=sample_rate, channels=channels)
        audio_base64 = base64.b64encode(wav_data).decode("ascii")
        payload = {
            "model": settings.mimo_asr_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": f"data:audio/wav;base64,{audio_base64}",
                            },
                        }
                    ],
                }
            ],
            "asr_options": {
                "language": settings.mimo_asr_language,
            },
        }

        url = f"{settings.mimo_base_url.rstrip('/')}/chat/completions"
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {settings.mimo_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=18) as response:
                response_body = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise MimoAsrError(f"MiMo ASR HTTP {exc.code}: {detail[:500]}") from exc
        except URLError as exc:
            raise MimoAsrError(f"MiMo ASR network error: {exc.reason}") from exc
        except TimeoutError as exc:
            raise MimoAsrError("MiMo ASR request timed out") from exc

        try:
            data = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise MimoAsrError("MiMo ASR returned non-JSON response") from exc

        choices = data.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        return _extract_text(message.get("content"))


mimo_asr = MimoAsrClient()
