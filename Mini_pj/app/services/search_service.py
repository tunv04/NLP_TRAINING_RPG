from __future__ import annotations

from rapidfuzz import fuzz

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

    def search(self, query: str, limit: int = 10) -> list[dict[str, object]]:
        normalized_query = self.normalizer.normalize(query)
        if len(normalized_query) < 2:
            return []

        hits: dict[int, dict[str, object]] = {}

        for product in self.product_repository.search_basic(normalized_query):
            hits[product.id] = self._to_result(
                product=product,
                score=self._basic_score(product, normalized_query),
                match_type="basic",
            )

        for product in self.product_repository.list_all_with_comments():
            fuzzy_score = self._fuzzy_score(product, normalized_query)
            if fuzzy_score < self.fuzzy_threshold:
                continue

            current = hits.get(product.id)
            if current is None:
                hits[product.id] = self._to_result(
                    product=product,
                    score=fuzzy_score,
                    match_type="fuzzy",
                )
            elif fuzzy_score > float(current["score"]):
                current["score"] = fuzzy_score

        results = sorted(
            hits.values(),
            key=lambda item: (-float(item["score"]), str(item["name"]).lower()),
        )
        return results[:limit]

    def _basic_score(self, product: Product, normalized_query: str) -> float:
        scores: list[float] = []

        if product.normalized_name == normalized_query:
            scores.append(100.0)
        elif normalized_query in (product.normalized_name or ""):
            scores.append(95.0)

        if normalized_query in (product.normalized_description or ""):
            scores.append(85.0)

        for comment in product.comments:
            if normalized_query in (comment.normalized_content or ""):
                scores.append(80.0)

        return max(scores, default=70.0)

    def _fuzzy_score(self, product: Product, normalized_query: str) -> float:
        weighted_scores: list[float] = []

        fields: list[tuple[str | None, float]] = [
            (product.normalized_name, 1.0),
            (product.normalized_description, 0.86),
        ]
        fields.extend((comment.normalized_content, 0.82) for comment in product.comments)

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
                    "author": comment.author,
                    "rating": comment.rating,
                    "content": comment.content,
                    "date": comment.date,
                }
                for comment in comments[:3]
            ],
            "score": round(score, 2),
            "match_type": match_type,
        }
