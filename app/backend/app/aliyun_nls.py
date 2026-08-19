import base64
import hashlib
import hmac
import json
import time
from typing import Optional
from urllib.parse import quote, urlencode
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

        token, expire_time = self._create_token()
        self._cached_token = token
        self._cached_expire_time = expire_time
        return token

    def synthesize_tts(self, text: str) -> Optional[bytes]:
        token = self.get_token()
        if not token or not settings.aliyun_nls_app_key:
            return None

        payload = urlencode(
            {
                "appkey": settings.aliyun_nls_app_key,
                "text": text[:300],
                "format": "mp3",
                "sample_rate": "16000",
                "voice": settings.aliyun_tts_voice,
            }
        ).encode("utf-8")
        request = Request(
            "https://nls-gateway-ap-southeast-1.aliyuncs.com/stream/v1/tts",
            data=payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-NLS-Token": token,
            },
            method="POST",
        )
        with urlopen(request, timeout=20) as response:
            content_type = response.headers.get("Content-Type", "")
            body = response.read()
            if "audio" not in content_type:
                raise RuntimeError(body.decode("utf-8", errors="ignore"))
            return body

    def _create_token(self) -> tuple[str, int]:
        params = {
            "AccessKeyId": settings.aliyun_access_key_id,
            "Action": "CreateToken",
            "Format": "JSON",
            "RegionId": "ap-southeast-1",
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
        request = Request(f"https://nlsmeta.ap-southeast-1.aliyuncs.com/?{query}", method="GET")
        with urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
        token = data["Token"]["Id"]
        expire_time = int(data["Token"]["ExpireTime"])
        return token, expire_time

    @staticmethod
    def _percent_encode(value: object) -> str:
        return quote(str(value), safe="").replace("+", "%20").replace("*", "%2A").replace("%7E", "~")


aliyun_nls = AliyunNlsClient()
