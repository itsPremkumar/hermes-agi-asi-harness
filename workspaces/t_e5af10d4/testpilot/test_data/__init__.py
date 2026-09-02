"""Test data management — synthetic data generation."""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from faker import Faker

from testpilot.models import SyntheticDataConfig


class SyntheticDataGenerator:
    """Generates synthetic test data using Faker."""

    def __init__(self, config: SyntheticDataConfig | None = None) -> None:
        self.config = config or SyntheticDataConfig()
        self.fake = Faker(self.config.locale)
        if self.config.seed is not None:
            self.fake.seed_instance(self.config.seed)

    def generate_from_schema(
        self, schema: dict[str, Any], count: int | None = None
    ) -> list[dict[str, Any]]:
        """Generate data from a JSON schema definition."""
        count = count or self.config.count
        return [self._generate_record(schema) for _ in range(count)]

    def _generate_record(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Generate a single record matching the schema."""
        record: dict[str, Any] = {}
        properties = schema.get("properties", schema)

        for field_name, field_def in properties.items():
            record[field_name] = self._generate_field(field_name, field_def)

        return record

    def _generate_field(self, name: str, field_def: dict[str, Any]) -> Any:
        """Generate a single field value."""
        if "const" in field_def:
            return field_def["const"]
        if "enum" in field_def:
            return self.fake.random_element(field_def["enum"])

        field_type = field_def.get("type", "string")
        faker_mapping = field_def.get("faker")

        if faker_mapping:
            return self._call_faker(faker_mapping)

        if field_type == "string":
            return self._generate_string(name, field_def)
        elif field_type == "integer":
            return self.fake.random_int(
                min=field_def.get("minimum", 0),
                max=field_def.get("maximum", 10000),
            )
        elif field_type == "number":
            return round(
                self.fake.pyfloat(
                    min_value=field_def.get("minimum", 0),
                    max_value=field_def.get("maximum", 1000),
                ),
                field_def.get("precision", 2),
            )
        elif field_type == "boolean":
            return self.fake.boolean()
        elif field_type == "array":
            items_schema = field_def.get("items", {"type": "string"})
            min_len = field_def.get("minItems", 1)
            max_len = field_def.get("maxItems", 5)
            length = self.fake.random_int(min=min_len, max=max_len)
            return [self._generate_field(f"{name}_item", items_schema) for _ in range(length)]
        elif field_type == "object":
            return self._generate_record(field_def)
        else:
            return None

    def _generate_string(self, name: str, field_def: dict[str, Any]) -> str:
        """Generate a string value based on field definition."""
        fmt = field_def.get("format", "")

        if fmt == "email" or "email" in name.lower():
            return self.fake.email()
        elif fmt == "uri" or "url" in name.lower():
            return self.fake.url()
        elif fmt == "date":
            return self.fake.date_iso()
        elif fmt == "date-time":
            return self.fake.iso8601()
        elif fmt == "uuid":
            return self.fake.uuid4()
        elif "name" in name.lower():
            return self.fake.name()
        elif "phone" in name.lower():
            return self.fake.phone_number()
        elif "address" in name.lower():
            return self.fake.address().replace("\n", ", ")
        elif "city" in name.lower():
            return self.fake.city()
        elif "country" in name.lower():
            return self.fake.country()
        elif "zip" in name.lower() or "postal" in name.lower():
            return self.fake.postcode()
        elif "company" in name.lower():
            return self.fake.company()
        elif "text" in name.lower() or "description" in name.lower():
            return self.fake.paragraph()
        elif "color" in name.lower():
            return self.fake.hex_color()
        else:
            max_len = field_def.get("maxLength", 50)
            return self.fake.pystr(min_chars=5, max_chars=min_len)

    @staticmethod
    def _call_faker(method_path: str) -> Any:
        """Call a Faker method by dotted path (e.g., 'person.name')."""
        parts = method_path.split(".")
        fake = Faker()
        obj: Any = fake
        for part in parts:
            obj = getattr(obj, part, None)
            if obj is None:
                return None
        if callable(obj):
            return obj()
        return obj

    def generate_users(self, count: int = 10) -> list[dict[str, Any]]:
        """Generate user records."""
        return [
            {
                "id": i + 1,
                "username": self.fake.user_name(),
                "email": self.fake.email(),
                "full_name": self.fake.name(),
                "date_of_birth": self.fake.date_of_birth(minimum_age=18, maximum_age=80).isoformat(),
                "is_active": self.fake.boolean(chance_of_getting_true=80),
                "created_at": self.fake.date_time_this_decade().isoformat(),
            }
            for i in range(count)
        ]

    def generate_products(self, count: int = 20) -> list[dict[str, Any]]:
        """Generate product records."""
        return [
            {
                "id": i + 1,
                "name": self.fake.catch_phrase(),
                "sku": self.fake.bothify(text="???-####"),
                "price": round(self.fake.pyfloat(min_value=1, max_value=999, right_digits=2), 2),
                "category": self.fake.random_element(
                    ["Electronics", "Clothing", "Books", "Home", "Sports"]
                ),
                "in_stock": self.fake.boolean(chance_of_getting_true=70),
                "description": self.fake.sentence(),
            }
            for i in range(count)
        ]

    def generate_orders(self, count: int = 50, max_user_id: int = 10) -> list[dict[str, Any]]:
        """Generate order records."""
        statuses = ["pending", "confirmed", "shipped", "delivered", "cancelled"]
        return [
            {
                "id": i + 1,
                "user_id": self.fake.random_int(min=1, max=max_user_id),
                "status": self.fake.random_element(statuses),
                "total_amount": round(self.fake.pyfloat(min_value=10, max_value=500, right_digits=2), 2),
                "created_at": self.fake.date_time_this_year().isoformat(),
                "items_count": self.fake.random_int(min=1, max=5),
            }
            for i in range(count)
        ]

    def to_json(self, data: list[dict[str, Any]], path: str | Path) -> Path:
        """Write generated data to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return path

    def to_csv(self, data: list[dict[str, Any]], path: str | Path) -> Path:
        """Write generated data to a CSV file."""
        import csv

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if not data:
            path.write_text("", encoding="utf-8")
            return path

        headers = list(data[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)

        return path

    def determinstic_id(self, seed_value: str) -> str:
        """Generate a deterministic ID from a seed value."""
        return hashlib.sha256(seed_value.encode()).hexdigest()[:16]


def generate_from_yaml_schema(
    schema_path: str,
    output_path: str | None = None,
    count: int = 10,
    locale: str = "en_US",
    seed: int | None = None,
) -> list[dict[str, Any]]:
    """Generate synthetic data from a YAML schema file."""
    import yaml

    config = SyntheticDataConfig(locale=locale, seed=seed, count=count)
    generator = SyntheticDataGenerator(config)
    schema = yaml.safe_load(Path(schema_path).read_text(encoding="utf-8"))
    data = generator.generate_from_schema(schema, count)

    if output_path:
        output_ext = Path(output_path).suffix.lower()
        if output_ext == ".csv":
            generator.to_csv(data, output_path)
        else:
            generator.to_json(data, output_path)

    return data
