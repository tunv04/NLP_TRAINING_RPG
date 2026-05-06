# from __future__ import annotations

# from rapidfuzz import fuzz

# from app.models.product import Product
# from app.repositories.product_repository import ProductRepository
# from app.services.text_normalizer import TextNormalizer


# class SearchService:
#     def __init__(
#         self,
#         product_repository: ProductRepository,
#         normalizer: type[TextNormalizer] = TextNormalizer,
#         fuzzy_threshold: float = 76.0,
#     ) -> None:
#         self.product_repository = product_repository
#         self.normalizer = normalizer
#         self.fuzzy_threshold = fuzzy_threshold

#     def search(self, query: str, limit: int = 10) -> list[dict[str, object]]:
#         normalized_query = self.normalizer.normalize(query)
#         if len(normalized_query) < 2:
#             return []

#         hits: dict[int, dict[str, object]] = {}

#         for product in self.product_repository.search_basic(normalized_query):
#             hits[product.id] = self._to_result(
#                 product=product,
#                 score=self._basic_score(product, normalized_query),
#                 match_type="basic",
#             )

#         for product in self.product_repository.list_all_with_comments():
#             fuzzy_score = self._fuzzy_score(product, normalized_query)
#             if fuzzy_score < self.fuzzy_threshold:
#                 continue

#             current = hits.get(product.id)
#             if current is None:
#                 hits[product.id] = self._to_result(
#                     product=product,
#                     score=fuzzy_score,
#                     match_type="fuzzy",
#                 )
#             elif fuzzy_score > float(current["score"]):
#                 current["score"] = fuzzy_score

#         results = sorted(
#             hits.values(),
#             key=lambda item: (-float(item["score"]), str(item["name"]).lower()),
#         )
#         return results[:limit]

#     def _basic_score(self, product: Product, normalized_query: str) -> float:
#         scores: list[float] = []

#         if product.normalized_name == normalized_query:
#             scores.append(100.0)
#         elif normalized_query in (product.normalized_name or ""):
#             scores.append(95.0)

#         if normalized_query in (product.normalized_description or ""):
#             scores.append(85.0)

#         for comment in product.comments:
#             if normalized_query in (comment.normalized_content or ""):
#                 scores.append(80.0)

#         return max(scores, default=70.0)

#     def _fuzzy_score(self, product: Product, normalized_query: str) -> float:
#         weighted_scores: list[float] = []

#         fields: list[tuple[str | None, float]] = [
#             (product.normalized_name, 1.0),
#             (product.normalized_description, 0.86),
#         ]
#         fields.extend((comment.normalized_content, 0.82) for comment in product.comments)

#         for value, weight in fields:
#             if not value:
#                 continue
#             field_score = max(
#                 fuzz.WRatio(normalized_query, value),
#                 fuzz.partial_ratio(normalized_query, value),
#                 fuzz.token_set_ratio(normalized_query, value),
#             )
#             weighted_scores.append(field_score * weight)

#         return round(max(weighted_scores, default=0.0), 2)

#     @staticmethod
#     def _to_result(
#         product: Product,
#         score: float,
#         match_type: str,
#     ) -> dict[str, object]:
#         comments = list(product.comments)

#         return {
#             "id": product.id,
#             "name": product.name,
#             "url": product.url,
#             "description": product.description,
#             "category": product.category,
#             "price": product.price,
#             "source": product.source,
#             "comments_count": len(comments),
#             "comments": [
#                 {
#                     "id": comment.id,
#                     "author": comment.author,
#                     "rating": comment.rating,
#                     "content": comment.content,
#                     "date": comment.date,
#                 }
#                 for comment in comments[:3]
#             ],
#             "score": round(score, 2),
#             "match_type": match_type,
#         }
from __future__ import annotations

from functools import lru_cache
from typing import Dict

from rapidfuzz import fuzz
from rank_bm25 import BM25Okapi  # pip install rank-bm25

from app.models.product import Product
from app.repositories.product_repository import ProductRepository
from app.services.text_normalizer import TextNormalizer


class SearchService:
    def __init__(
        self,
        product_repository: ProductRepository,
        normalizer: type[TextNormalizer] = TextNormalizer,
        fuzzy_threshold: float = 76.0,
    ) -> None:
        self.product_repository = product_repository
        self.normalizer = normalizer
        self.fuzzy_threshold = fuzzy_threshold

        # ==================== ENHANCED SYNONYM DICTIONARY ====================
        self.synonyms: Dict[str, list[str]] = {
            "dau bung": ["dau bung", "dau buong", "dau da day", "kho tieu", "day hoi", "tron bung", "dau thung bung"],
            "tieu hoa": ["tieu hoa", "nhuan trang", "taobon", "tao bon", "day bung", "tieu chay", "phan mem", "kho tieu hoa"],
            "men vi sinh": ["men vi sinh", "probiotic", "loi khuan", "sinh khuan", "men probiotic"],
            "giam can": ["giam can", "giam mo", "dot mo", "giam beo", "giam mo bung"],
            "tang chieu cao": ["tang chieu cao", "phat trien chieu cao", "cao hon", "tang cao"],
            "tang suc de khang": ["tang suc de khang", "tang mien dich", "bo sung mien dich", "tang de khang"],
            "vitamin": ["vitamin", "vitmin", "vitamine", "vitamin d", "vitamin c"],
            "omega": ["omega", "fish oil", "dau ca", "omega 3", "omega3"],
            "magie": ["magie", "magnesium", "mg", "magie glycinate"],
            "canxi": ["canxi", "calcium"],
        }

        # Build BM25 index once
        self._build_bm25_index()

    def _build_bm25_index(self):
        """Xây dựng BM25 index một lần khi khởi tạo service"""
        products = self.product_repository.list_all_with_comments()
        self.product_list = products
        self.product_map = {p.id: p for p in products}

        corpus = []
        for p in products:
            text = f"{p.normalized_name or ''} {p.normalized_description or ''}"
            for c in p.comments:
                text += f" {c.normalized_content or ''}"
            corpus.append(text.strip().split())  # BM25 cần list of tokens

        self.bm25 = BM25Okapi(corpus)

    @lru_cache(maxsize=300)   # Cache kết quả search để tăng tốc
    def search(self, query: str, limit: int = 10) -> list[dict[str, object]]:
        normalized_query = self.normalizer.normalize(query)
        if len(normalized_query) < 2:
            return []

        hits: dict[int, dict[str, object]] = {}
        query_tokens = normalized_query.split()

        # === STAGE 1: BM25 Ranking (rất mạnh) ===
        bm25_scores = self.bm25.get_scores(query_tokens)
        for idx, bm25_score in enumerate(bm25_scores):
            if bm25_score < 0.8:  # Lọc nhiễu
                continue
            product = self.product_list[idx]
            boost = self._intent_boost(product, normalized_query, query)
            final_score = bm25_score * boost * 0.9

            hits[product.id] = self._to_result(
                product=product,
                score=final_score,
                match_type="bm25",
            )

        # === STAGE 2: Basic Search (Exact/Sub-string) ===
        for product in self.product_repository.search_basic(normalized_query):
            base_score = self._basic_score(product, normalized_query)
            boost = self._intent_boost(product, normalized_query, query)
            final_score = base_score * boost * 1.15   # Ưu tiên basic

            if product.id not in hits or final_score > float(hits[product.id]["score"]):
                hits[product.id] = self._to_result(
                    product=product,
                    score=final_score,
                    match_type="basic",
                )

        # === STAGE 3: Fuzzy Search (Fallback) ===
        for product in self.product_list:
            if product.id in hits and float(hits[product.id]["score"]) > 80:
                continue

            fuzzy_score = self._fuzzy_score(product, normalized_query)
            if fuzzy_score < self.fuzzy_threshold:
                continue

            boost = self._intent_boost(product, normalized_query, query)
            final_score = fuzzy_score * boost * 0.85

            current = hits.get(product.id)
            if current is None or final_score > float(current["score"]):
                hits[product.id] = self._to_result(
                    product=product,
                    score=final_score,
                    match_type="fuzzy",
                )

        # Final sort
        results = sorted(
            hits.values(),
            key=lambda item: (-float(item["score"]), str(item["name"]).lower()),
        )
        return results[:limit]

    def _intent_boost(self, product: Product, norm_query: str, original_query: str) -> float:
        boost = 1.0
        name_norm = (product.normalized_name or "").lower()
        desc_norm = (product.normalized_description or "").lower()
        cat_norm = (product.category or "").lower()

        # Synonym Boost
        for key, syn_list in self.synonyms.items():
            if any(s in norm_query for s in syn_list):
                if any(s in name_norm or s in desc_norm or s in cat_norm for s in syn_list):
                    boost += 1.3
                break

        # Strong Health Intent
        strong_keywords = {"dau bung", "dau da day", "tieu hoa", "nhuan trang", "taobon", "men vi sinh", 
                          "giam can", "tang chieu cao"}
        if any(kw in name_norm or kw in desc_norm or kw in cat_norm for kw in strong_keywords):
            boost += 1.25

        # "Thuốc" + Tiêu hóa boost
        if "thuoc" in original_query.lower() and any(
            x in cat_norm for x in ["tieu hoa", "nhuan trang", "vitamin", "canxi"]
        ):
            boost += 0.95

        # Multi-word match bonus
        query_words = set(norm_query.split())
        match_count = sum(1 for w in query_words if len(w) >= 3 and (w in name_norm or w in desc_norm))
        boost += match_count * 0.45

        return min(boost, 3.3)

    def _basic_score(self, product: Product, normalized_query: str) -> float:
        scores: list[float] = []
        name = product.normalized_name or ""
        desc = product.normalized_description or ""

        if normalized_query == name:
            scores.append(100.0)
        elif normalized_query in name:
            scores.append(96.0)
        elif normalized_query in desc:
            scores.append(87.0)

        if product.category and any(k in product.category.lower() 
                                   for k in ["tiêu hóa", "nhuận tràng", "táo bón"]):
            scores.append(86.0)

        for comment in product.comments:
            if normalized_query in (comment.normalized_content or ""):
                scores.append(80.0)

        return max(scores, default=67.0)

    def _fuzzy_score(self, product: Product, normalized_query: str) -> float:
        weighted_scores: list[float] = []

        fields: list[tuple[str | None, float]] = [
            (product.normalized_name, 1.0),
            (product.normalized_description, 0.83),
        ]
        fields.extend((comment.normalized_content, 0.79) for comment in product.comments)

        for value, weight in fields:
            if not value:
                continue
            field_score = max(
                fuzz.WRatio(normalized_query, value),
                fuzz.partial_ratio(normalized_query, value),
                fuzz.token_set_ratio(normalized_query, value),
            )
            weighted_scores.append(field_score * weight)

        return round(max(weighted_scores, default=0.0), 2)

    @staticmethod
    def _to_result(
        product: Product,
        score: float,
        match_type: str,
    ) -> dict[str, object]:
        comments = list(product.comments)
        return {
            "id": product.id,
            "name": product.name,
            "url": product.url,
            "description": product.description,
            "category": product.category,
            "price": product.price,
            "source": product.source,
            "comments_count": len(comments),
            "comments": [
                {
                    "id": comment.id,
                    "author": getattr(comment, "author", None),
                    "rating": getattr(comment, "rating", None),
                    "content": comment.content,
                    "date": getattr(comment, "date", None),
                }
                for comment in comments[:3]
            ],
            "score": round(score, 2),
            "match_type": match_type,
        }