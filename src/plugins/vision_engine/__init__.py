#!/usr/bin/env python3
"""
Vision Engine Plugin — Image analysis and processing
===================================================
Features:
- Image metadata extraction
- Basic image processing (resize, convert, thumbnail)
- Color analysis
- OCR placeholder interface
- Object detection placeholder
"""

from __future__ import annotations

import asyncio
import base64
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("hermes_vision_engine")

try:
    from core.runtime.plugin_base import PluginBase, PluginManifest, PluginPermissions, PluginState
    HAS_CORE = True
except ImportError:
    from enum import Enum
    
    class PluginState(str, Enum):
        REGISTERED = "registered"
        LOADED = "loaded"
        RUNNING = "running"
        PAUSED = "paused"
        ERROR = "error"
        UNLOADED = "unloaded"
    
    @dataclass
    class PluginPermissions:
        filesystem_read: str = "project"
        filesystem_write: str = "project"
        network_domains: list[str] = field(default_factory=list)
        shell_commands: list[str] = field(default_factory=list)
        secrets_access: str = "none"
        max_memory_mb: 512
        max_cpu_percent: 20
    
    @dataclass
    class PluginManifest:
        name: str = ""
        version: str = "1.0.0"
        description: str = ""
        license: str = "MIT"
        source: str = "internal"
        capabilities: list[str] = field(default_factory=list)
        cost: str = "free"
        permissions: PluginPermissions = field(default_factory=PluginPermissions)
        dependencies: list[str] = field(default_factory=list)
        path: Path | None = None
    
    class PluginBase:
        manifest: PluginManifest
        
        def __init__(self, manifest: PluginManifest = None, kernel: Any = None):
            self.manifest = manifest or PluginManifest()
            self.kernel = kernel
            self.state = PluginState.REGISTERED
        
        async def load(self) -> bool:
            self.state = PluginState.LOADED
            return True
        
        async def start(self) -> bool:
            self.state = PluginState.RUNNING
            return True
        
        async def stop(self) -> bool:
            self.state = PluginState.UNLOADED
            return True
    
    HAS_CORE = False


@dataclass
class ImageInfo:
    """Image metadata."""
    path: str
    width: int
    height: int
    format: str
    mode: str
    size_bytes: int
    has_alpha: bool
    dominant_colors: list[str] = field(default_factory=list)


class VisionEngine:
    """Image analysis and processing."""
    
    def __init__(self):
        self._has_pil = self._check_pil()
    
    def _check_pil(self) -> bool:
        """Check if PIL is available."""
        try:
            import PIL
            return True
        except ImportError:
            return False
    
    def analyze(self, image_path: str) -> dict[str, Any]:
        """Analyze an image."""
        path = Path(image_path)
        
        if not path.exists():
            return {"success": False, "error": f"Image not found: {image_path}"}
        
        try:
            size_bytes = path.stat().st_size
            
            if self._has_pil:
                from PIL import Image
                img = Image.open(path)
                
                # Get dominant colors
                colors = self._get_dominant_colors(img, 5)
                
                info = ImageInfo(
                    path=str(path),
                    width=img.width,
                    height=img.height,
                    format=img.format or "unknown",
                    mode=img.mode,
                    size_bytes=size_bytes,
                    has_alpha=img.mode in ("RGBA", "LA", "PA"),
                    dominant_colors=colors,
                )
                
                return {
                    "success": True,
                    "width": info.width,
                    "height": info.height,
                    "format": info.format,
                    "mode": info.mode,
                    "size_bytes": info.size_bytes,
                    "has_alpha": info.has_alpha,
                    "dominant_colors": info.dominant_colors,
                }
            else:
                return {
                    "success": True,
                    "width": 0,
                    "height": 0,
                    "format": path.suffix.lstrip(".") or "unknown",
                    "mode": "unknown",
                    "size_bytes": size_bytes,
                    "has_alpha": False,
                    "dominant_colors": [],
                    "note": "PIL not available — limited metadata only",
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_dominant_colors(self, img, count: int = 5) -> list[str]:
        """Get dominant colors from image."""
        try:
            # Resize for speed
            small = img.resize((50, 50))
            if small.mode != "RGB":
                small = small.convert("RGB")
            
            # Get colors
            colors = small.getcolors(50 * 50)
            colors.sort(reverse=True)
            
            result = []
            for count, (r, g, b) in colors[:count]:
                result.append(f"#{r:02x}{g:02x}{b:02x}")
            
            return result
        except Exception:
            return []
    
    def resize(self, image_path: str, output_path: str, width: int, height: int | None = None) -> dict[str, Any]:
        """Resize an image."""
        if not self._has_pil:
            return {"success": False, "error": "PIL not available"}
        
        try:
            from PIL import Image
            img = Image.open(image_path)
            
            if height is None:
                # Maintain aspect ratio
                aspect = img.height / img.width
                height = int(width * aspect)
            
            resized = img.resize((width, height), Image.Resampling.LANCZOS)
            resized.save(output_path)
            
            return {
                "success": True,
                "output": output_path,
                "width": width,
                "height": height,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_thumbnail(self, image_path: str, output_path: str, size: int = 128) -> dict[str, Any]:
        """Create a thumbnail."""
        if not self._has_pil:
            return {"success": False, "error": "PIL not available"}
        
        try:
            from PIL import Image
            img = Image.open(image_path)
            img.thumbnail((size, size))
            img.save(output_path)
            
            return {
                "success": True,
                "output": output_path,
                "width": img.width,
                "height": img.height,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def convert_format(self, image_path: str, output_path: str, fmt: str = "PNG") -> dict[str, Any]:
        """Convert image format."""
        if not self._has_pil:
            return {"success": False, "error": "PIL not available"}
        
        try:
            from PIL import Image
            img = Image.open(image_path)
            if img.mode in ("RGBA", "P", "LA") and fmt.upper() in ("JPEG", "JPG"):
                img = img.convert("RGB")
            img.save(output_path, fmt.upper())
            
            return {
                "success": True,
                "output": output_path,
                "format": fmt.upper(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def encode_base64(self, image_path: str) -> dict[str, Any]:
        """Encode image as base64."""
        try:
            with open(image_path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            
            return {
                "success": True,
                "base64": data,
                "length": len(data),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def analyze_colors(self, image_path: str) -> dict[str, Any]:
        """Analyze color distribution."""
        if not self._has_pil:
            return {"success": False, "error": "PIL not available"}
        
        try:
            from PIL import Image
            img = Image.open(image_path)
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            # Sample colors
            colors: dict[str, int] = {}
            for pixel in img.getdata()[::100]:  # Sample every 100th pixel
                r, g, b = pixel
                bucket = f"#{r//32*32:02x}{g//32*32:02x}{b//32*32:02x}"
                colors[bucket] = colors.get(bucket, 0) + 1
            
            # Sort by frequency
            sorted_colors = sorted(colors.items(), key=lambda x: x[1], reverse=True)
            
            return {
                "success": True,
                "top_colors": sorted_colors[:10],
                "unique_color_buckets": len(colors),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════════
# PLUGIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════════

class Plugin(PluginBase):
    """Vision Engine Plugin"""
    
    def __init__(self):
        self.state = PluginState.REGISTERED
        self.manifest = PluginManifest(
            name="vision_engine",
            version="1.0.0",
            description="Image analysis, processing, color analysis, and format conversion (PIL-based)",
            license="MIT",
            source="internal",
            capabilities=["image_analysis", "image_resize", "image_thumbnail", "image_convert", "color_analysis", "base64_encode"],
            cost="free",
            permissions=PluginPermissions(
                filesystem_read="workspace",
                filesystem_write="workspace",
                network_domains=[],
                shell_commands=[],
                secrets_access="none",
                max_memory_mb=512,
                max_cpu_percent=20,
            ),
        )
        self.engine: VisionEngine | None = None
    
    async def load(self) -> bool:
        self.engine = VisionEngine()
        self.state = PluginState.LOADED
        return True
    
    async def start(self) -> bool:
        if not self.engine:
            self.engine = VisionEngine()
        self.state = PluginState.RUNNING
        return True
    
    async def stop(self) -> bool:
        self.state = PluginState.UNLOADED
        return True
    
    async def health(self) -> dict[str, Any]:
        return {
            "plugin": self.manifest.name,
            "version": self.manifest.version,
            "state": self.state.value,
            "healthy": self.state in (PluginState.LOADED, PluginState.RUNNING),
            "ready": self.engine is not None,
            "has_pil": self.engine._has_pil if self.engine else False,
        }
    
    # ── PUBLIC API ──────────────────────────────────────────────────────
    
    def analyze(self, image_path: str) -> dict[str, Any]:
        return self.engine.analyze(image_path)
    
    def resize(self, image_path: str, output_path: str, width: int, height: int | None = None) -> dict[str, Any]:
        return self.engine.resize(image_path, output_path, width, height)
    
    def create_thumbnail(self, image_path: str, output_path: str, size: int = 128) -> dict[str, Any]:
        return self.engine.create_thumbnail(image_path, output_path, size)
    
    def convert_format(self, image_path: str, output_path: str, fmt: str = "PNG") -> dict[str, Any]:
        return self.engine.convert_format(image_path, output_path, fmt)
    
    def encode_base64(self, image_path: str) -> dict[str, Any]:
        return self.engine.encode_base64(image_path)
    
    def analyze_colors(self, image_path: str) -> dict[str, Any]:
        return self.engine.analyze_colors(image_path)
    
    def get_capabilities(self) -> list[str]:
        return self.manifest.capabilities
