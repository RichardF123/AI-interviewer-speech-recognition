import base64
import hashlib
import hmac
import json
import time
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import uuid4

from app.config import settings


class AliyunNlsClient:
    def __init__(self) -> None:
        self._cached_token: Optional[str] = None
        self._cached_expire_time: int = 0

    def get_token(self) -> Optional[str]:
        if settings.aliyun_nls_token:
            return settings.aliyun_nls_token

        now = int(time.time())
        if self._cached_token and self._cached_expire_time - 300 > now:
            return self._cached_token

        if not settings.aliyun_access_key_id or not settings.aliyun_access_key_secret:
            return None

        token, expire_time = self._retry(self._create_token, "Aliyun token")
        self._cached_token = token
        self._cached_expire_time = expire_time
        return token

    def synthesize_tts(self, text: str) -> Optional[bytes]:
        token = self.get_token()
        if not token or not settings.aliyun_nls_app_key:
            return None

        payload = json.dumps(
            {
                "appkey": settings.aliyun_nls_app_key,
                "token": token,
                "text": text[:300],
                "format": "mp3",
                "sample_rate": 16000,
                "voice": settings.aliyun_tts_voice,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = Request(
            settings.aliyun_tts_endpoint,
            data=payload,
            headers={
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with self._urlopen_with_retry(request, "Aliyun TTS") as response:
                content_type = response.headers.get("Content-Type", "")
                body = response.read()
                if "audio" not in content_type:
                    raise RuntimeError(body.decode("utf-8", errors="replace"))
                return body
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Aliyun TTS HTTP {exc.code}: {body[:500]}") from exc

    def _create_token(self) -> tuple[str, int]:
        params = {
            "AccessKeyId": settings.aliyun_access_key_id,
            "Action": "CreateToken",
            "Format": "JSON",
            "RegionId": "cn-shanghai",
            "SignatureMethod": "HMAC-SHA1",
            "SignatureNonce": str(uuid4()),
            "SignatureVersion": "1.0",
            "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "Version": "2019-02-28",
        }
        canonicalized = "&".join(
            f"{self._percent_encode(key)}={self._percent_encode(params[key])}"
            for key in sorted(params)
        )
        string_to_sign = f"GET&%2F&{self._percent_encode(canonicalized)}"
        digest = hmac.new(
            f"{settings.aliyun_access_key_secret}&".encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha1,
        ).digest()
        signature = base64.b64encode(digest).decode("utf-8")
        query = f"Signature={self._percent_encode(signature)}&{canonicalized}"
        request = Request(f"https://nls-meta.cn-shanghai.aliyuncs.com/?{query}", method="GET")
        with self._urlopen_with_retry(request, "Aliyun token") as response:
            data = json.loads(response.read().decode("utf-8"))
        token = data["Token"]["Id"]
        expire_time = int(data["Token"]["ExpireTime"])
        return token, expire_time

    @staticmethod
    def _percent_encode(value: object) -> str:
        return quote(str(value), safe="").replace("+", "%20").replace("*", "%2A").replace("%7E", "~")

    def _urlopen_with_retry(self, request: Request, label: str):
        return self._retry(lambda: urlopen(request, timeout=10), label)

    @staticmethod
    def _retry(action, label: str, attempts: int = 3):
        last_error: Optional[BaseException] = None
        for attempt in range(attempts):
            try:
                return action()
            except HTTPError:
                raise
            except (TimeoutError, URLError, OSError) as exc:
                last_error = exc
                if attempt < attempts - 1:
                    time.sleep(0.35 * (attempt + 1))
        raise RuntimeError(f"{label} request failed after {attempts} attempts: {last_error}") from last_error


aliyun_nls = AliyunNlsClient()
