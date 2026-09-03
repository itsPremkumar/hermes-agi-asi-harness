"""FormForge — dynamic form builder."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FieldType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    SELECT = "select"
    CHECKBOX = "checkbox"
    TEXTAREA = "textarea"


@dataclass
class FormField:
    id: str
    name: str
    field_type: FieldType
    label: str
    required: bool = False
    options: list[str] = field(default_factory=list)


@dataclass
class Form:
    id: str
    name: str
    fields: list[FormField] = field(default_factory=list)


class FormForge:
    """Build dynamic forms."""

    def __init__(self):
        self.id = str(uuid.uuid4())
        self._forms: dict[str, Form] = {}

    def create(self, name: str) -> Form:
        form = Form(id=str(uuid.uuid4()), name=name)
        self._forms[form.id] = form
        return form

    def add_field(self, form_id: str, name: str, field_type: FieldType, label: str, required: bool = False) -> FormField | None:
        if form_id in self._forms:
            field = FormField(id=str(uuid.uuid4()), name=name, field_type=field_type, label=label, required=required)
            self._forms[form_id].fields.append(field)
            return field
        return None

    def get(self, form_id: str) -> Form | None:
        return self._forms.get(form_id)

    def list_all(self) -> list[Form]:
        return list(self._forms.values())

    def count(self) -> int:
        return len(self._forms)
