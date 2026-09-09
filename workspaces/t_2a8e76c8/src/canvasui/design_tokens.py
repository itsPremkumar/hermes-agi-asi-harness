"""Design tokens and theme system for CanvasUI Dashboard.

Provides a comprehensive token system covering color, typography, spacing,
elevation, radius, breakpoints, and motion. Supports light/dark themes with
full token inheritance and resolution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Color Tokens ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ColorTokens:
    """Color palette tokens."""
    # Primary
    primary_50: str = "#eff6ff"
    primary_100: str = "#dbeafe"
    primary_200: str = "#bfdbfe"
    primary_300: str = "#93c5fd"
    primary_400: str = "#60a5fa"
    primary_500: str = "#3b82f6"
    primary_600: str = "#2563eb"
    primary_700: str = "#1d4ed8"
    primary_800: str = "#1e40af"
    primary_900: str = "#1e3a8a"

    # Neutral
    neutral_0: str = "#ffffff"
    neutral_50: str = "#f9fafb"
    neutral_100: str = "#f3f4f6"
    neutral_200: str = "#e5e7eb"
    neutral_300: str = "#d1d5db"
    neutral_400: str = "#9ca3af"
    neutral_500: str = "#6b7280"
    neutral_600: str = "#4b5563"
    neutral_700: str = "#374151"
    neutral_800: str = "#1f2937"
    neutral_900: str = "#111827"
    neutral_950: str = "#030712"

    # Semantic
    success_50: str = "#ecfdf5"
    success_500: str = "#10b981"
    success_700: str = "#047857"
    warning_50: str = "#fffbeb"
    warning_500: str = "#f59e0b"
    warning_700: str = "#b45309"
    error_50: str = "#fef2f2"
    error_500: str = "#ef4444"
    error_700: str = "#b91c1c"
    info_50: str = "#eff6ff"
    info_500: str = "#3b82f6"
    info_700: str = "#1d4ed8"


# ── Typography Tokens ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class TypographyTokens:
    """Typography scale tokens."""
    font_family_sans: str = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    font_family_mono: str = "'JetBrains Mono', 'Fira Code', Consolas, monospace"

    font_size_xs: str = "0.75rem"    # 12px
    font_size_sm: str = "0.875rem"   # 14px
    font_size_base: str = "1rem"     # 16px
    font_size_lg: str = "1.125rem"   # 18px
    font_size_xl: str = "1.25rem"    # 20px
    font_size_2xl: str = "1.5rem"    # 24px
    font_size_3xl: str = "1.875rem"  # 30px
    font_size_4xl: str = "2.25rem"   # 36px

    font_weight_normal: int = 400
    font_weight_medium: int = 500
    font_weight_semibold: int = 600
    font_weight_bold: int = 700

    line_height_tight: float = 1.25
    line_height_normal: float = 1.5
    line_height_relaxed: float = 1.75

    letter_spacing_tight: str = "-0.025em"
    letter_spacing_normal: str = "0em"
    letter_spacing_wide: str = "0.025em"


# ── Spacing Tokens ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SpacingTokens:
    """Spacing scale tokens (4px base unit)."""
    space_0: str = "0px"
    space_1: str = "4px"
    space_2: str = "8px"
    space_3: str = "12px"
    space_4: str = "16px"
    space_5: str = "20px"
    space_6: str = "24px"
    space_8: str = "32px"
    space_10: str = "40px"
    space_12: str = "48px"
    space_16: str = "64px"
    space_20: str = "80px"
    space_24: str = "96px"


# ── Elevation Tokens ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class ElevationTokens:
    """Elevation/shadow tokens."""
    shadow_sm: str = "0 1px 2px 0 rgb(0 0 0 / 0.05)"
    shadow_md: str = "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)"
    shadow_lg: str = "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)"
    shadow_xl: str = "0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)"
    shadow_2xl: str = "0 25px 50px -12px rgb(0 0 0 / 0.25)"


# ── Radius Tokens ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RadiusTokens:
    """Border radius tokens."""
    radius_none: str = "0px"
    radius_sm: str = "2px"
    radius_md: str = "6px"
    radius_lg: str = "8px"
    radius_xl: str = "12px"
    radius_2xl: str = "16px"
    radius_full: str = "9999px"


# ── Breakpoint Tokens ────────────────────────────────────────────────────

@dataclass(frozen=True)
class BreakpointTokens:
    """Responsive breakpoint tokens."""
    breakpoint_sm: str = "640px"
    breakpoint_md: str = "768px"
    breakpoint_lg: str = "1024px"
    breakpoint_xl: str = "1280px"
    breakpoint_2xl: str = "1536px"


# ── Motion Tokens ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MotionTokens:
    """Animation/motion tokens."""
    duration_fast: str = "150ms"
    duration_normal: str = "250ms"
    duration_slow: str = "350ms"
    easing_linear: str = "linear"
    easing_ease_in: str = "cubic-bezier(0.4, 0, 1, 1)"
    easing_ease_out: str = "cubic-bezier(0, 0, 0.2, 1)"
    easing_ease_in_out: str = "cubic-bezier(0.4, 0, 0.2, 1)"


# ── Theme ─────────────────────────────────────────────────────────────────

@dataclass
class Theme:
    """Complete theme with all token categories."""
    name: str = "light"
    colors: ColorTokens = field(default_factory=ColorTokens)
    typography: TypographyTokens = field(default_factory=TypographyTokens)
    spacing: SpacingTokens = field(default_factory=SpacingTokens)
    elevation: ElevationTokens = field(default_factory=ElevationTokens)
    radius: RadiusTokens = field(default_factory=RadiusTokens)
    breakpoints: BreakpointTokens = field(default_factory=BreakpointTokens)
    motion: MotionTokens = field(default_factory=MotionTokens)

    # Semantic color mappings (resolved from colors)
    background: str = "#ffffff"
    surface: str = "#f9fafb"
    surface_hover: str = "#f3f4f6"
    text_primary: str = "#111827"
    text_secondary: str = "#6b7280"
    text_disabled: str = "#9ca3af"
    border: str = "#e5e7eb"
    border_focus: str = "#3b82f6"

    def resolve(self, token_path: str) -> str:
        """Resolve a dot-notation token path to its value.

        Examples:
            theme.resolve('colors.primary_500') -> '#3b82f6'
            theme.resolve('spacing.space_4') -> '16px'
            theme.resolve('background') -> '#ffffff'
        """
        parts = token_path.split(".")
        obj: Any = self
        for part in parts:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            elif isinstance(obj, dict) and part in obj:
                obj = obj[part]
            else:
                raise KeyError(f"Token not found: {token_path}")
        return str(obj)

    def to_dict(self) -> dict[str, Any]:
        """Convert theme to a flat dictionary of all tokens."""
        result = {}
        # Top-level semantic tokens
        for key in ("background", "surface", "surface_hover", "text_primary",
                     "text_secondary", "text_disabled", "border", "border_focus"):
            result[key] = getattr(self, key)
        # Nested token groups
        for group_name in ("colors", "typography", "spacing", "elevation",
                           "radius", "breakpoints", "motion"):
            group = getattr(self, group_name)
            for key, value in group.__dict__.items():
                result[f"{group_name}.{key}"] = value
        return result


class LightTheme(Theme):
    """Light mode theme."""

    def __init__(self):
        super().__init__(
            name="light",
            background="#ffffff",
            surface="#f9fafb",
            surface_hover="#f3f4f6",
            text_primary="#111827",
            text_secondary="#6b7280",
            text_disabled="#9ca3af",
            border="#e5e7eb",
            border_focus="#3b82f6",
        )


class DarkTheme(Theme):
    """Dark mode theme."""

    def __init__(self):
        super().__init__(
            name="dark",
            colors=ColorTokens(
                primary_500="#6366f1",
                primary_600="#4f46e5",
                primary_400="#818cf8",
                primary_300="#a5b4fc",
                primary_200="#c7d2fe",
                primary_100="#e0e7ff",
                primary_50="#eef2ff",
                primary_700="#4338ca",
                primary_800="#3730a3",
                primary_900="#312e81",
                neutral_0="#0a0a0a",
                neutral_50="#171717",
                neutral_100="#1f1f1f",
                neutral_200="#2d2d2d",
                neutral_300="#404040",
                neutral_400="#525252",
                neutral_500="#737373",
                neutral_600="#a3a3a3",
                neutral_700="#d4d4d4",
                neutral_800="#e5e5e5",
                neutral_900="#f5f5f5",
                neutral_950="#fafafa",
                success_50="#052e16",
                success_500="#22c55e",
                success_700="#15803d",
                warning_50="#422006",
                warning_500="#eab308",
                warning_700="#a16207",
                error_50="#450a0a",
                error_500="#f87171",
                error_700="#b91c1c",
                info_50="#172554",
                info_500="#60a5fa",
                info_700="#1d4ed8",
            ),
            background="#0f0f23",
            surface="#1a1a2e",
            surface_hover="#25253e",
            text_primary="#f9fafb",
            text_secondary="#9ca3af",
            text_disabled="#6b7280",
            border="#374151",
            border_focus="#6366f1",
        )


# ── Token Registry ────────────────────────────────────────────────────────

class TokenRegistry:
    """Registry for managing multiple themes."""

    def __init__(self):
        self._themes: dict[str, Theme] = {}
        self._active: str = "light"

    def register(self, theme: Theme) -> None:
        """Register a theme."""
        self._themes[theme.name] = theme

    def get(self, name: str | None = None) -> Theme:
        """Get a theme by name, or the active theme."""
        key = name or self._active
        if key not in self._themes:
            raise KeyError(f"Theme '{key}' not registered")
        return self._themes[key]

    def set_active(self, name: str) -> None:
        """Set the active theme."""
        if name not in self._themes:
            raise KeyError(f"Theme '{name}' not registered")
        self._active = name

    @property
    def active(self) -> str:
        """Get the active theme name."""
        return self._active

    def list_themes(self) -> list[str]:
        """List all registered theme names."""
        return list(self._themes.keys())


# ── Default Registry ──────────────────────────────────────────────────────

def create_default_registry() -> TokenRegistry:
    """Create a registry with light and dark themes pre-registered."""
    registry = TokenRegistry()
    registry.register(LightTheme())
    registry.register(DarkTheme())
    return registry


# Module-level default registry
default_registry = create_default_registry()
