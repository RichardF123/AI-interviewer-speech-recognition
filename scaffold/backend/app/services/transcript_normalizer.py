import re


class TranscriptNormalizer:
    def normalize(self, text: str) -> str:
        cleaned = text.strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = cleaned.replace("呃", "").replace("嗯", "")
        if cleaned and cleaned[-1] not in "。！？!?":
            cleaned += "。"
        return cleaned

