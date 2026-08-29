"""Tests for synthetic data generation."""
import json
from pathlib import Path

from testpilot.test_data import SyntheticDataGenerator, SyntheticDataConfig


def test_generate_users() -> None:
    """Should generate user records."""
    config = SyntheticDataConfig(seed=42)
    gen = SyntheticDataGenerator(config)
    users = gen.generate_users(5)

    assert len(users) == 5
    assert all("email" in u for u in users)
    assert all("username" in u for u in users)


def test_generate_products() -> None:
    """Should generate product records."""
    config = SyntheticDataConfig(seed=42)
    gen = SyntheticDataGenerator(config)
    products = gen.generate_products(10)

    assert len(products) == 10
    assert all("name" in p for p in products)
    assert all("price" in p for p in products)
    assert all(p["price"] > 0 for p in products)


def test_generate_orders() -> None:
    """Should generate order records."""
    config = SyntheticDataConfig(seed=42)
    gen = SyntheticDataGenerator(config)
    orders = gen.generate_orders(20, max_user_id=5)

    assert len(orders) == 20
    assert all(1 <= o["user_id"] <= 5 for o in orders)


def test_deterministic_with_seed() -> None:
    """Same seed should produce same data."""
    config = SyntheticDataConfig(seed=123)
    gen1 = SyntheticDataGenerator(config)
    gen2 = SyntheticDataGenerator(SyntheticDataConfig(seed=123))

    data1 = gen1.generate_users(3)
    data2 = gen2.generate_users(3)

    assert data1 == data2


def test_to_json(tmp_path: Path) -> None:
    """Should write data to JSON file."""
    config = SyntheticDataConfig(seed=42)
    gen = SyntheticDataGenerator(config)
    users = gen.generate_users(3)

    output = tmp_path / "users.json"
    gen.to_json(users, output)

    assert output.exists()
    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert len(loaded) == 3


def test_to_csv(tmp_path: Path) -> None:
    """Should write data to CSV file."""
    config = SyntheticDataConfig(seed=42)
    gen = SyntheticDataGenerator(config)
    users = gen.generate_users(3)

    output = tmp_path / "users.csv"
    gen.to_csv(users, output)

    assert output.exists()
    content = output.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    assert len(lines) == 4  # header + 3 records


def test_generate_from_schema() -> None:
    """Should generate data matching a schema."""
    schema = {
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer", "minimum": 18, "maximum": 65},
            "active": {"type": "boolean"},
        }
    }
    config = SyntheticDataConfig(seed=42)
    gen = SyntheticDataGenerator(config)
    data = gen.generate_from_schema(schema, count=5)

    assert len(data) == 5
    for record in data:
        assert "name" in record
        assert isinstance(record["age"], int)
        assert 18 <= record["age"] <= 65
        assert isinstance(record["active"], bool)
