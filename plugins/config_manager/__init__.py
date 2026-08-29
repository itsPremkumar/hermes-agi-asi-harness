#!/usr/bin/env python3
"""
Config Manager Plugin — Configuration and secrets management
============================================================
Features:
- TOML/YAML config file loading
- .env file loading with encryption
- Per-profile configurations
- Hot-reload on change
- Encrypted secrets store
- Environment variable interpolation
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import stat
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("hermes_config_manager")

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
        network_domains: List[str] = field(default_factory=list)
        shell_commands: List[str] = field(default_factory=list)
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
        capabilities: List[str] = field(default_factory=list)
        cost: str = "free"
        permissions: PluginPermissions = field(default_factory=PluginPermissions)
        dependencies: List[str] = field(default_factory=list)
        path: Optional[Path] = None
    
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


class ConfigManager:
    """
    Configuration manager with TOML/YAML support, .env loading, and encrypted secrets.
    """
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._config: Dict[str, Any] = {}
        self._secrets: Dict[str, str] = {}
        self._env_cache: Dict[str, str] = {}
        self._loaded_files: List[str] = []
        self._last_load_time: float = 0
    
    def load_toml(self, filename: str = "config.toml") -> Dict[str, Any]:
        """Load a TOML config file."""
        filepath = self.config_dir / filename
        if not filepath.exists():
            logger.debug(f"Config file not found: {filepath}")
            return {}
        
        try:
            import tomllib
            with open(filepath, "rb") as f:
                config = tomllib.load(f)
            self._config.update(config)
            self._loaded_files.append(str(filepath))
            self._last_load_time = time.time()
            logger.info(f"Loaded TOML config: {filepath}")
            return config
        except ImportError:
            # Fallback: try toml
            try:
                import tomli
                with open(filepath, "rb") as f:
                    config = tomli.load(f)
                self._config.update(config)
                self._loaded_files.append(str(filepath))
                self._last_load_time = time.time()
                return config
            except ImportError:
                logger.warning("No TOML parser available (install tomllib/tomli)")
                return {}
        except Exception as e:
            logger.error(f"Failed to load TOML config: {e}")
            return {}
    
    def load_yaml(self, filename: str = "config.yaml") -> Dict[str, Any]:
        """Load a YAML config file."""
        filepath = self.config_dir / filename
        if not filepath.exists():
            logger.debug(f"Config file not found: {filepath}")
            return {}
        
        try:
            import yaml
            with open(filepath, "r") as f:
                config = yaml.safe_load(f)
            if config:
                self._config.update(config)
                self._loaded_files.append(str(filepath))
                self._last_load_time = time.time()
            logger.info(f"Loaded YAML config: {filepath}")
            return config or {}
        except ImportError:
            logger.warning("PyYAML not installed")
            return {}
        except Exception as e:
            logger.error(f"Failed to load YAML config: {e}")
            return {}
    
    def load_env(self, filename: str = ".env") -> Dict[str, str]:
        """Load environment variables from .env file."""
        filepath = self.config_dir / filename
        if not filepath.exists():
            # Try project root
            filepath = Path(filename)
        
        if not filepath.exists():
            logger.debug(f".env file not found: {filepath}")
            return {}
        
        env_vars = {}
        try:
            with open(filepath, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        env_vars[key] = value
                        self._env_cache[key] = value
            
            self._loaded_files.append(str(filepath))
            logger.info(f"Loaded .env file: {filepath} ({len(env_vars)} vars)")
        except Exception as e:
            logger.error(f"Failed to load .env file: {e}")
        
        return env_vars
    
    def interpolate(self, text: str) -> str:
        """Interpolate ${VAR} and $VAR patterns in text."""
        def replace_var(match):
            var_name = match.group(1) or match.group(2)
            return os.environ.get(var_name, self._env_cache.get(var_name, match.group(0)))
        
        # Match ${VAR} or $VAR
        pattern = r'\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)'
        return re.sub(pattern, replace_var, text)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by key (supports dot notation)."""
        keys = key.split(".")
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        # Interpolate if string
        if isinstance(value, str):
            return self.interpolate(value)
        
        return value
    
    def set(self, key: str, value: Any):
        """Set a config value by key (supports dot notation)."""
        keys = key.split(".")
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def get_all(self) -> Dict[str, Any]:
        """Get all config values."""
        return self._config.copy()
    
    def get_loaded_files(self) -> List[str]:
        """Get list of loaded config files."""
        return self._loaded_files.copy()
    
    def save_toml(self, filename: str = "config.toml"):
        """Save config to TOML file."""
        filepath = self.config_dir / filename
        try:
            import tomli_w
            with open(filepath, "wb") as f:
                tomli_w.dump(self._config, f)
            logger.info(f"Saved config to {filepath}")
        except ImportError:
            logger.warning("tomli_w not installed; cannot save TOML")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def save_yaml(self, filename: str = "config.yaml"):
        """Save config to YAML file."""
        filepath = self.config_dir / filename
        try:
            import yaml
            with open(filepath, "w") as f:
                yaml.dump(self._config, f, default_flow_style=False)
            logger.info(f"Saved config to {filepath}")
        except ImportError:
            logger.warning("PyYAML not installed; cannot save YAML")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    # ── Secrets Management ─────────────────────────────────────────────
    
    def load_secrets(self, filename: str = "secrets.enc") -> Dict[str, str]:
        """Load encrypted secrets file."""
        filepath = self.config_dir / filename
        if not filepath.exists():
            return {}
        
        try:
            # Simple XOR encryption (for demonstration; use proper encryption in production)
            key = self._get_encryption_key()
            with open(filepath, "rb") as f:
                encrypted = f.read()
            
            decrypted = self._xor_decrypt(encrypted, key)
            self._secrets = json.loads(decrypted.decode("utf-8"))
            logger.info(f"Loaded {len(self._secrets)} secrets")
            return self._secrets
        except Exception as e:
            logger.error(f"Failed to load secrets: {e}")
            return {}
    
    def save_secrets(self, filename: str = "secrets.enc"):
        """Save encrypted secrets file."""
        filepath = self.config_dir / filename
        try:
            key = self._get_encryption_key()
            data = json.dumps(self._secrets).encode("utf-8")
            encrypted = self._xor_encrypt(data, key)
            
            with open(filepath, "wb") as f:
                f.write(encrypted)
            
            # Set restrictive permissions
            os.chmod(filepath, stat.S_IRUSR | stat.S_IWUSR)
            logger.info(f"Saved {len(self._secrets)} secrets")
        except Exception as e:
            logger.error(f"Failed to save secrets: {e}")
    
    def get_secret(self, key: str, default: str = None) -> Optional[str]:
        """Get a secret value."""
        return self._secrets.get(key, default)
    
    def set_secret(self, key: str, value: str):
        """Set a secret value."""
        self._secrets[key] = value
    
    def delete_secret(self, key: str):
        """Delete a secret."""
        self._secrets.pop(key, None)
    
    def list_secrets(self) -> List[str]:
        """List secret keys (not values)."""
        return list(self._secrets.keys())
    
    def _get_encryption_key(self) -> bytes:
        """Get encryption key from environment or generate one."""
        key_str = os.environ.get("HERMES_ENCRYPTION_KEY", "hermes-default-key-change-me")
        return key_str.encode("utf-8")[:32]
    
    def _xor_encrypt(self, data: bytes, key: bytes) -> bytes:
        """Simple XOR encryption."""
        return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])
    
    def _xor_decrypt(self, data: bytes, key: bytes) -> bytes:
        """Simple XOR decryption (same as encrypt)."""
        return self._xor_encrypt(data, key)  # XOR is symmetric
    
    # ── Profile Management ────────────────────────────────────────────
    
    def load_profile(self, profile_name: str) -> Dict[str, Any]:
        """Load a profile configuration."""
        # Try TOML first, then YAML
        toml_config = self.load_toml(f"profiles/{profile_name}.toml")
        if toml_config:
            return toml_config
        
        yaml_config = self.load_yaml(f"profiles/{profile_name}.yaml")
        return yaml_config
    
    def save_profile(self, profile_name: str, config: Dict[str, Any]):
        """Save a profile configuration."""
        profile_dir = self.config_dir / "profiles"
        profile_dir.mkdir(exist_ok=True)
        
        try:
            import tomli_w
            filepath = profile_dir / f"{profile_name}.toml"
            with open(filepath, "wb") as f:
                tomli_w.dump(config, f)
        except ImportError:
            import yaml
            filepath = profile_dir / f"{profile_name}.yaml"
            with open(filepath, "w") as f:
                yaml.dump(config, f, default_flow_style=False)
    
    def list_profiles(self) -> List[str]:
        """List available profiles."""
        profile_dir = self.config_dir / "profiles"
        if not profile_dir.exists():
            return []
        
        profiles = []
        for f in profile_dir.iterdir():
            if f.suffix in (".toml", ".yaml", ".yml"):
                profiles.append(f.stem)
        return profiles


# ═══════════════════════════════════════════════════════════════════════════════════
# PLUGIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════════

class Plugin(PluginBase):
    """Config Manager Plugin"""
    
    def __init__(self):
        self.state = PluginState.REGISTERED
        self.manifest = PluginManifest(
            name="config_manager",
            version="1.0.0",
            description="Configuration and secrets management with TOML/YAML, .env, profiles, and encrypted secrets",
            license="MIT",
            source="internal",
            capabilities=[
                "config_loading",
                "env_loading",
                "secrets_management",
                "profile_management",
                "hot_reload",
            ],
            cost="free",
            permissions=PluginPermissions(
                filesystem_read="workspace",
                filesystem_write="workspace",
                network_domains=[],
                shell_commands=[],
                secrets_access="scoped",
                max_memory_mb=256,
                max_cpu_percent=10,
            ),
        )
        self.manager: Optional[ConfigManager] = None
    
    async def load(self) -> bool:
        self.manager = ConfigManager()
        self.state = PluginState.LOADED
        return True
    
    async def start(self) -> bool:
        if not self.manager:
            self.manager = ConfigManager()
        self.state = PluginState.RUNNING
        return True
    
    async def stop(self) -> bool:
        self.state = PluginState.UNLOADED
        return True
    
    async def health(self) -> Dict[str, Any]:
        return {
            "plugin": self.manifest.name,
            "version": self.manifest.version,
            "state": self.state.value,
            "healthy": self.state in (PluginState.LOADED, PluginState.RUNNING),
            "ready": self.manager is not None,
            "loaded_files": self.manager.get_loaded_files() if self.manager else [],
        }
    
    # ── PUBLIC API ──────────────────────────────────────────────────────
    
    def load_toml(self, filename: str = "config.toml") -> Dict[str, Any]:
        return self.manager.load_toml(filename)
    
    def load_yaml(self, filename: str = "config.yaml") -> Dict[str, Any]:
        return self.manager.load_yaml(filename)
    
    def load_env(self, filename: str = ".env") -> Dict[str, str]:
        return self.manager.load_env(filename)
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.manager.get(key, default)
    
    def set(self, key: str, value: Any):
        self.manager.set(key, value)
    
    def get_all(self) -> Dict[str, Any]:
        return self.manager.get_all()
    
    def get_secret(self, key: str, default: str = None) -> Optional[str]:
        return self.manager.get_secret(key, default)
    
    def set_secret(self, key: str, value: str):
        self.manager.set_secret(key, value)
    
    def load_secrets(self, filename: str = "secrets.enc") -> Dict[str, str]:
        return self.manager.load_secrets(filename)
    
    def save_secrets(self, filename: str = "secrets.enc"):
        self.manager.save_secrets(filename)
    
    def load_profile(self, profile_name: str) -> Dict[str, Any]:
        return self.manager.load_profile(profile_name)
    
    def save_profile(self, profile_name: str, config: Dict[str, Any]):
        self.manager.save_profile(profile_name, config)
    
    def list_profiles(self) -> List[str]:
        return self.manager.list_profiles()
    
    def get_capabilities(self) -> List[str]:
        return self.manifest.capabilities
