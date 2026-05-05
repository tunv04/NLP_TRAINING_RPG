from __future__ import annotations

import re
import unicodedata


class TextNormalizer:
    @staticmethod
    def remove_accents(text: object) -> str:
        if text is None:
            return ""

        value = str(text).replace("Đ", "D").replace("đ", "d")
        normalized = unicodedata.normalize("NFD", value)
        return "".join(
            char for char in normalized if unicodedata.category(char) != "Mn"
        )

    @classmethod
    def normalize(cls, text: object) -> str:
        value = cls.remove_accents(text).lower()
        value = re.sub(r"[^a-z0-9\s]", " ", value)
        value = re.sub(r"\s+", " ", value)
        return value.strip()
