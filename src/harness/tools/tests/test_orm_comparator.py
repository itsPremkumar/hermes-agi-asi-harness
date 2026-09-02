"""Tests for ORM Comparator."""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src"))

from harness.tools.orm_comparator import (
    ORMComparator,
    ORMProfile,
    ComparisonResult,
)


class TestORMProfile:
    def test_create(self):
        orm = ORMProfile("SQLAlchemy", "Python")
        assert orm.name == "SQLAlchemy"
        assert orm.score_performance == 0.0

    def test_create_with_scores(self):
        orm = ORMProfile("SQLAlchemy", "Python", 8.0, 9.0, 9.0, 7.0, 8.0)
        assert orm.score_performance == 8.0


class TestORMComparator:
    def test_create(self):
        comparator = ORMComparator()
        assert comparator is not None

    def test_add_orm(self):
        comparator = ORMComparator()
        comparator.add_orm(ORMProfile("SQLAlchemy", "Python"))
        assert "SQLAlchemy" in comparator._orms

    def test_compare_empty(self):
        comparator = ORMComparator()
        result = comparator.compare()
        assert result.winner == "none"

    def test_compare(self):
        comparator = ORMComparator()
        comparator.add_orm(ORMProfile("SQLAlchemy", "Python", 8.0, 9.0, 9.0, 7.0, 8.0))
        comparator.add_orm(ORMProfile("Prisma", "TypeScript", 7.0, 8.0, 7.0, 9.0, 9.0))
        result = comparator.compare()
        assert result.winner == "SQLAlchemy"
        assert len(result.scores) == 2

    def test_get_recommendation(self):
        comparator = ORMComparator()
        comparator.add_orm(ORMProfile("SQLAlchemy", "Python", 8.0, 9.0, 9.0, 7.0, 8.0))
        comparator.add_orm(ORMProfile("Prisma", "TypeScript", 7.0, 8.0, 7.0, 9.0, 9.0))
        rec = comparator.get_recommendation("balanced")
        assert "SQLAlchemy" in rec


class TestComparisonResult:
    def test_create(self):
        result = ComparisonResult([], "none", "reason", {})
        assert result.winner == "none"
