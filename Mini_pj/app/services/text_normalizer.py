from __future__ import annotations

import re
import unicodedata
from typing import Set


class TextNormalizer:
    # Stop words phổ biến trong query tìm kiếm thuốc
    STOP_WORDS: Set[str] = {
        "thuoc", "thuốc", "vien", "viên", "uong", "uống", "dung", "dùng",
        "cho", "cua", "của", "va", "và", "de", "để", "la", "là", "voi", "với",
        "mot", "một", "cac", "các", "nay", "này", "do", "đó", "ra", "sang",
        "tot", "tốt", "nhat", "nhất", "hieu", "hiệu", "qua", "quá"
    }

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
        """
        Normalize text cho search: 
        - Bỏ dấu
        - Lowercase
        - Giữ chữ và số
        - Loại stop words
        """
        if text is None:
            return ""

        # Bỏ dấu + lowercase
        value = cls.remove_accents(text).lower()

        # Giữ chữ cái, số và khoảng trắng
        value = re.sub(r"[^a-z0-9\s]", " ", value)

        # Chuẩn hóa khoảng trắng
        value = re.sub(r"\s+", " ", value).strip()

        if not value:
            return ""

        # Loại stop words
        words = value.split()
        filtered_words = [w for w in words if w not in cls.STOP_WORDS]

        return " ".join(filtered_words)

    @classmethod
    def get_keywords(cls, text: object) -> list[str]:
        """Trích xuất danh sách từ khóa quan trọng (dùng cho BM25 hoặc debug)"""
        normalized = cls.normalize(text)
        return [word for word in normalized.split() if len(word) > 1]

    @classmethod
    def normalize_for_display(cls, text: object) -> str:
        """Dùng khi muốn giữ nguyên ý nghĩa hiển thị (không remove stop words)"""
        if text is None:
            return ""
        value = cls.remove_accents(text).lower()
        value = re.sub(r"[^a-z0-9\s]", " ", value)
        value = re.sub(r"\s+", " ", value)
        return value.strip()