"""CanvasUI Dashboard Component System.

A comprehensive dashboard UI framework with design tokens, component library,
and documentation site generator.
"""
from __future__ import annotations

from .design_tokens import (
    Theme, LightTheme, DarkTheme,
    ColorTokens, TypographyTokens, SpacingTokens,
    ElevationTokens, RadiusTokens, BreakpointTokens, MotionTokens,
    TokenRegistry, create_default_registry, default_registry,
)
from .components import (
    Component, Button,
    FormField, TextInput, TextArea, Select, Checkbox, RadioGroup, Form,
    Column, Table,
    Chart, BarChart, LineChart, PieChart, AreaChart,
    Card, Modal,
    NavItem, Navbar, Sidebar, Breadcrumb,
    Badge, Avatar, Progress, Spinner, Tooltip, Tabs,
    Alert, Divider,
    Container, Grid, Flex, Stack,
)
from .docs_site import DocsSite, create_default_site

__version__ = "1.0.0"

__all__ = [
    # Design tokens
    "Theme", "LightTheme", "DarkTheme",
    "ColorTokens", "TypographyTokens", "SpacingTokens",
    "ElevationTokens", "RadiusTokens", "BreakpointTokens", "MotionTokens",
    "TokenRegistry", "create_default_registry", "default_registry",
    # Components
    "Component", "Button",
    "FormField", "TextInput", "TextArea", "Select", "Checkbox", "RadioGroup", "Form",
    "Column", "Table",
    "Chart", "BarChart", "LineChart", "PieChart", "AreaChart",
    "Card", "Modal",
    "NavItem", "Navbar", "Sidebar", "Breadcrumb",
    "Badge", "Avatar", "Progress", "Spinner", "Tooltip", "Tabs",
    "Alert", "Divider",
    "Container", "Grid", "Flex", "Stack",
    # Docs site
    "DocsSite", "create_default_site",
]
