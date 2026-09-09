"""Component library for CanvasUI Dashboard.

Provides production-ready UI components: buttons, forms, tables, charts,
cards, modals, navigation, and utility components. All components support
theming via the design token system.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from .design_tokens import Theme, LightTheme


# ── Base Component ────────────────────────────────────────────────────────

@dataclass
class Component:
    """Base class for all UI components."""
    id: str = field(default_factory=lambda: f"comp_{uuid.uuid4().hex[:8]}")
    name: str = ""
    visible: bool = True
    enabled: bool = True
    classes: list[str] = field(default_factory=list)
    styles: dict[str, str] = field(default_factory=dict)
    children: list["Component"] = field(default_factory=list)
    parent: "Component | None" = None
    _handlers: dict[str, list[Callable]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_child(self, child: "Component") -> "Component":
        """Add a child component."""
        child.parent = self
        self.children.append(child)
        return child

    def remove_child(self, child: "Component") -> None:
        """Remove a child component."""
        self.children = [c for c in self.children if c is not child]

    def find(self, name: str) -> "Component | None":
        """Find a component by name (recursive)."""
        if self.name == name:
            return self
        for child in self.children:
            found = child.find(name)
            if found:
                return found
        return None

    def on(self, event: str, handler: Callable) -> None:
        """Register an event handler."""
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    def trigger(self, event: str, **kwargs) -> None:
        """Trigger an event on this component."""
        for handler in self._handlers.get(event, []):
            handler(self, **kwargs)
        if self.parent:
            self.parent.trigger(event, **kwargs)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "visible": self.visible,
            "enabled": self.enabled,
            "classes": self.classes,
            "styles": self.styles,
            "children": [c.to_dict() for c in self.children],
        }


# ── Button Component ──────────────────────────────────────────────────────

@dataclass
class Button(Component):
    """Button component with variants and sizes."""
    text: str = "Button"
    variant: str = "primary"  # primary, secondary, outline, ghost, danger
    size: str = "md"          # sm, md, lg
    icon: str = ""
    loading: bool = False
    disabled: bool = False

    def __post_init__(self):
        if not self.name:
            self.name = f"btn_{uuid.uuid4().hex[:6]}"

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            text=self.text,
            variant=self.variant,
            size=self.size,
            icon=self.icon,
            loading=self.loading,
            disabled=self.disabled,
        )
        return d


# ── Form Components ───────────────────────────────────────────────────────

@dataclass
class FormField(Component):
    """Base form field component."""
    label: str = ""
    placeholder: str = ""
    required: bool = False
    error: str = ""
    value: str = ""

    def validate(self) -> bool:
        """Validate the field value."""
        if self.required and not self.value:
            self.error = f"{self.label or 'This field'} is required"
            return False
        self.error = ""
        return True

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            label=self.label,
            placeholder=self.placeholder,
            required=self.required,
            error=self.error,
            value=self.value,
        )
        return d


@dataclass
class TextInput(FormField):
    """Text input field."""
    input_type: str = "text"  # text, email, password, number, tel, url
    min_length: int = 0
    max_length: int = 0

    def validate(self) -> bool:
        if not super().validate():
            return False
        if self.min_length and len(self.value) < self.min_length:
            self.error = f"Minimum {self.min_length} characters required"
            return False
        if self.max_length and len(self.value) > self.max_length:
            self.error = f"Maximum {self.max_length} characters allowed"
            return False
        return True


@dataclass
class TextArea(FormField):
    """Multi-line text input."""
    rows: int = 4
    min_length: int = 0
    max_length: int = 0

    def validate(self) -> bool:
        if not super().validate():
            return False
        if self.min_length and len(self.value) < self.min_length:
            self.error = f"Minimum {self.min_length} characters required"
            return False
        if self.max_length and len(self.value) > self.max_length:
            self.error = f"Maximum {self.max_length} characters allowed"
            return False
        return True


@dataclass
class Select(FormField):
    """Dropdown select field."""
    options: list[dict[str, str]] = field(default_factory=list)
    multiple: bool = False

    def validate(self) -> bool:
        if self.required and not self.value:
            self.error = f"{self.label or 'This field'} is required"
            return False
        self.error = ""
        return True


@dataclass
class Checkbox(FormField):
    """Checkbox field."""
    checked: bool = False

    def validate(self) -> bool:
        if self.required and not self.checked:
            self.error = "This field must be checked"
            return False
        self.error = ""
        return True


@dataclass
class RadioGroup(FormField):
    """Radio button group."""
    options: list[dict[str, str]] = field(default_factory=list)

    def validate(self) -> bool:
        if self.required and not self.value:
            self.error = "Please select an option"
            return False
        self.error = ""
        return True


@dataclass
class Form(Component):
    """Form container with validation."""
    title: str = ""
    fields: list[FormField] = field(default_factory=list)
    submit_label: str = "Submit"

    def add_field(self, field: FormField) -> FormField:
        """Add a field to the form."""
        self.add_child(field)
        self.fields.append(field)
        return field

    def validate(self) -> bool:
        """Validate all fields."""
        valid = True
        for f in self.fields:
            if not f.validate():
                valid = False
        return valid

    def get_values(self) -> dict[str, str]:
        """Get all field values as a dict."""
        return {f.name: f.value for f in self.fields if f.name}

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            title=self.title,
            submit_label=self.submit_label,
            fields=[f.to_dict() for f in self.fields],
        )
        return d


# ── Table Component ───────────────────────────────────────────────────────

@dataclass
class Column:
    """Table column definition."""
    key: str
    label: str
    sortable: bool = False
    width: str = ""
    align: str = "left"  # left, center, right


@dataclass
class Table(Component):
    """Data table component with sorting and pagination."""
    columns: list[Column] = field(default_factory=list)
    data: list[dict[str, Any]] = field(default_factory=list)
    sortable: bool = True
    paginated: bool = False
    page_size: int = 10
    current_page: int = 0
    sort_key: str = ""
    sort_direction: str = "asc"  # asc, desc

    def add_column(self, key: str, label: str, **kwargs) -> Column:
        """Add a column definition."""
        col = Column(key=key, label=label, **kwargs)
        self.columns.append(col)
        return col

    def set_data(self, data: list[dict[str, Any]]) -> None:
        """Set table data."""
        self.data = data
        self.current_page = 0

    def sort_by(self, key: str) -> None:
        """Sort by column key."""
        if self.sort_key == key:
            self.sort_direction = "desc" if self.sort_direction == "asc" else "asc"
        else:
            self.sort_key = key
            self.sort_direction = "asc"
        reverse = self.sort_direction == "desc"
        self.data.sort(key=lambda row: str(row.get(key, "")), reverse=reverse)

    @property
    def page_count(self) -> int:
        """Get total page count."""
        if not self.paginated or self.page_size <= 0:
            return 1
        return max(1, (len(self.data) + self.page_size - 1) // self.page_size)

    @property
    def visible_data(self) -> list[dict[str, Any]]:
        """Get data for the current page."""
        if not self.paginated:
            return self.data
        start = self.current_page * self.page_size
        end = start + self.page_size
        return self.data[start:end]

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            columns=[{"key": c.key, "label": c.label, "sortable": c.sortable} for c in self.columns],
            row_count=len(self.data),
            current_page=self.current_page,
            page_count=self.page_count,
            sort_key=self.sort_key,
            sort_direction=self.sort_direction,
        )
        return d


# ── Chart Components ──────────────────────────────────────────────────────

@dataclass
class Chart(Component):
    """Base chart component."""
    title: str = ""
    width: int = 400
    height: int = 300
    theme: Theme = field(default_factory=LightTheme)

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(title=self.title, width=self.width, height=self.height)
        return d


@dataclass
class BarChart(Chart):
    """Bar chart component."""
    data: list[dict[str, Any]] = field(default_factory=list)
    x_key: str = "label"
    y_key: str = "value"
    horizontal: bool = False
    stacked: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            chart_type="bar",
            data=self.data,
            x_key=self.x_key,
            y_key=self.y_key,
            horizontal=self.horizontal,
            stacked=self.stacked,
        )
        return d


@dataclass
class LineChart(Chart):
    """Line chart component."""
    series: list[dict[str, Any]] = field(default_factory=list)
    x_key: str = "x"
    show_area: bool = False
    smooth: bool = True

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            chart_type="line",
            series=self.series,
            x_key=self.x_key,
            show_area=self.show_area,
            smooth=self.smooth,
        )
        return d


@dataclass
class PieChart(Chart):
    """Pie/donut chart component."""
    data: list[dict[str, Any]] = field(default_factory=list)
    label_key: str = "label"
    value_key: str = "value"
    donut: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            chart_type="pie",
            data=self.data,
            label_key=self.label_key,
            value_key=self.value_key,
            donut=self.donut,
        )
        return d


@dataclass
class AreaChart(Chart):
    """Area chart component."""
    series: list[dict[str, Any]] = field(default_factory=list)
    x_key: str = "x"
    stacked: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            chart_type="area",
            series=self.series,
            x_key=self.x_key,
            stacked=self.stacked,
        )
        return d


# ── Card Component ────────────────────────────────────────────────────────

@dataclass
class Card(Component):
    """Card container component."""
    title: str = ""
    subtitle: str = ""
    elevation: str = "md"  # sm, md, lg, xl
    padding: str = "md"   # none, sm, md, lg

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            title=self.title,
            subtitle=self.subtitle,
            elevation=self.elevation,
            padding=self.padding,
        )
        return d


# ── Modal Component ───────────────────────────────────────────────────────

@dataclass
class Modal(Component):
    """Modal dialog component."""
    title: str = ""
    size: str = "md"  # sm, md, lg, xl, full
    open: bool = False
    closable: bool = True

    def show(self) -> None:
        """Show the modal."""
        self.open = True
        self.trigger("show")

    def hide(self) -> None:
        """Hide the modal."""
        self.open = False
        self.trigger("hide")

    def toggle(self) -> None:
        """Toggle modal visibility."""
        if self.open:
            self.hide()
        else:
            self.show()

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            title=self.title,
            size=self.size,
            open=self.open,
            closable=self.closable,
        )
        return d


# ── Navigation Components ─────────────────────────────────────────────────

@dataclass
class NavItem:
    """Navigation item."""
    label: str
    href: str = "#"
    icon: str = ""
    active: bool = False
    children: list["NavItem"] = field(default_factory=list)


@dataclass
class Navbar(Component):
    """Top navigation bar."""
    brand: str = ""
    items: list[NavItem] = field(default_factory=list)

    def add_item(self, label: str, href: str = "#", **kwargs) -> NavItem:
        """Add a navigation item."""
        item = NavItem(label=label, href=href, **kwargs)
        self.items.append(item)
        return item

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            brand=self.brand,
            items=[{"label": i.label, "href": i.href, "active": i.active} for i in self.items],
        )
        return d


@dataclass
class Sidebar(Component):
    """Side navigation."""
    items: list[NavItem] = field(default_factory=list)
    collapsed: bool = False

    def add_item(self, label: str, href: str = "#", **kwargs) -> NavItem:
        """Add a sidebar item."""
        item = NavItem(label=label, href=href, **kwargs)
        self.items.append(item)
        return item

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            items=[{"label": i.label, "href": i.href, "active": i.active} for i in self.items],
            collapsed=self.collapsed,
        )
        return d


@dataclass
class Breadcrumb(Component):
    """Breadcrumb navigation."""
    items: list[NavItem] = field(default_factory=list)

    def add_item(self, label: str, href: str = "#") -> NavItem:
        """Add a breadcrumb item."""
        item = NavItem(label=label, href=href)
        self.items.append(item)
        return item

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            items=[{"label": i.label, "href": i.href} for i in self.items],
        )
        return d


# ── Utility Components ────────────────────────────────────────────────────

@dataclass
class Badge(Component):
    """Badge/label component."""
    text: str = ""
    variant: str = "default"  # default, success, warning, error, info
    size: str = "sm"          # sm, md, lg

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(text=self.text, variant=self.variant, size=self.size)
        return d


@dataclass
class Avatar(Component):
    """Avatar component."""
    src: str = ""
    alt: str = ""
    initials: str = ""
    size: str = "md"  # xs, sm, md, lg, xl

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(src=self.src, alt=self.alt, initials=self.initials, size=self.size)
        return d


@dataclass
class Progress(Component):
    """Progress bar component."""
    value: float = 0.0
    max: float = 100.0
    variant: str = "primary"  # primary, success, warning, error
    show_label: bool = False

    @property
    def percentage(self) -> float:
        """Get progress percentage."""
        if self.max <= 0:
            return 0.0
        return min(100.0, (self.value / self.max) * 100)

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            value=self.value,
            max=self.max,
            percentage=self.percentage,
            variant=self.variant,
            show_label=self.show_label,
        )
        return d


@dataclass
class Spinner(Component):
    """Loading spinner component."""
    size: str = "md"  # sm, md, lg
    variant: str = "primary"

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(size=self.size, variant=self.variant)
        return d


@dataclass
class Tooltip(Component):
    """Tooltip component."""
    text: str = ""
    position: str = "top"  # top, bottom, left, right

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(text=self.text, position=self.position)
        return d


@dataclass
class Tabs(Component):
    """Tabbed navigation component."""
    tabs: list[dict[str, str]] = field(default_factory=list)
    active_tab: str = ""

    def add_tab(self, id: str, label: str) -> None:
        """Add a tab."""
        self.tabs.append({"id": id, "label": label})
        if not self.active_tab:
            self.active_tab = id

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(tabs=self.tabs, active_tab=self.active_tab)
        return d


@dataclass
class Alert(Component):
    """Alert/notification component."""
    title: str = ""
    message: str = ""
    variant: str = "info"  # info, success, warning, error
    dismissible: bool = True
    visible: bool = True

    def dismiss(self) -> None:
        """Dismiss the alert."""
        self.visible = False
        self.trigger("dismiss")

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            title=self.title,
            message=self.message,
            variant=self.variant,
            dismissible=self.dismissible,
        )
        return d


@dataclass
class Divider(Component):
    """Horizontal or vertical divider."""
    orientation: str = "horizontal"  # horizontal, vertical
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(orientation=self.orientation, label=self.label)
        return d


# ── Layout Components ─────────────────────────────────────────────────────

@dataclass
class Container(Component):
    """Page container with max-width."""
    max_width: str = "xl"  # sm, md, lg, xl, 2xl, full

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(max_width=self.max_width)
        return d


@dataclass
class Grid(Component):
    """CSS Grid layout."""
    columns: int = 3
    gap: str = "md"  # none, sm, md, lg

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(columns=self.columns, gap=self.gap)
        return d


@dataclass
class Flex(Component):
    """Flexbox layout."""
    direction: str = "row"       # row, column
    justify: str = "flex-start"  # flex-start, center, flex-end, space-between, space-around
    align: str = "stretch"       # flex-start, center, flex-end, stretch
    gap: str = "md"              # none, sm, md, lg
    wrap: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            direction=self.direction,
            justify=self.justify,
            align=self.align,
            gap=self.gap,
            wrap=self.wrap,
        )
        return d


@dataclass
class Stack(Component):
    """Vertical stack layout."""
    gap: str = "md"     # none, sm, md, lg
    align: str = "stretch"  # stretch, flex-start, center, flex-end

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(gap=self.gap, align=self.align)
        return d
