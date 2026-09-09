"""Ethics reviewer module — Ethics check pipeline for AI systems."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EthicsReview:
    """An ethics review."""
    id: str
    title: str
    description: str
    status: str
    findings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class EthicsReviewer:
    """Manage ethics reviews."""

    def __init__(self) -> None:
        self._reviews: dict[str, EthicsReview] = {}

    def create(self, title: str, description: str) -> EthicsReview:
        review = EthicsReview(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            status="pending",
        )
        self._reviews[review.id] = review
        return review

    def get(self, id: str) -> EthicsReview | None:
        return self._reviews.get(id)

    def get_all(self) -> list[EthicsReview]:
        return list(self._reviews.values())

    def approve(self, id: str) -> None:
        review = self._reviews.get(id)
        if review:
            review.status = "approved"

    def reject(self, id: str) -> None:
        review = self._reviews.get(id)
        if review:
            review.status = "rejected"

    def add_finding(self, id: str, finding: str) -> None:
        review = self._reviews.get(id)
        if review:
            review.findings.append(finding)

    def add_recommendation(self, id: str, recommendation: str) -> None:
        review = self._reviews.get(id)
        if review:
            review.recommendations.append(recommendation)

    def get_by_status(self, status: str) -> list[EthicsReview]:
        return [r for r in self._reviews.values() if r.status == status]
