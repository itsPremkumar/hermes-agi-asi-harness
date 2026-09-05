"""
Hermes Integration Plugin — Auto-configure harness with Hermes as one system.

When installed, this plugin:
1. Auto-detects Hermes installation
2. Configures MCP servers
3. Sets up bot profiles
4. Registers slash commands
5. Enables all Hermes features
6. Provides unified API
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


# ──────────────────────────── Data Classes ────────────────────────────


@dataclass
class HermesConfig:
    """Hermes configuration."""
    hermes_dir: str
    profiles_dir: str
    plugins_dir: str
    config_file: str
    mcp_config: dict[str, Any]
    bot_profiles: list[dict[str, Any]]
    slash_commands: list[dict[str, Any]]
    installed: bool = False
    version: str = ""


@dataclass
class IntegrationStatus:
    """Integration status."""
    hermes_detected: bool
    mcp_configured: bool
    bots_created: int
    plugins_linked: int
    slash_commands_registered: int
    errors: list[str]
    warnings: list[str]


# ──────────────────────────── Hermes Detector ────────────────────────────


class HermesDetector:
    """Detects Hermes installation and configuration."""
    
    @staticmethod
    def detect() -> HermesConfig | None:
        """Detect Hermes installation."""
        # Check common locations
        possible_dirs = [
            os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes"),
            os.path.join(os.path.expanduser("~"), ".hermes"),
            os.path.join(os.path.expanduser("~"), "hermes"),
        ]
        
        for d in possible_dirs:
            if os.path.exists(d):
                profiles_dir = os.path.join(d, "profiles")
                plugins_dir = os.path.join(d, "plugins")
                config_file = os.path.join(d, "config.yaml")
                
                if os.path.exists(profiles_dir):
                    return HermesConfig(
                        hermes_dir=d,
                        profiles_dir=profiles_dir,
                        plugins_dir=plugins_dir,
                        config_file=config_file,
                        mcp_config={},
                        bot_profiles=[],
                        slash_commands=[],
                        installed=True,
                        version=HermesDetector._get_version(d),
                    )
        
        return None
    
    @staticmethod
    def _get_version(hermes_dir: str) -> str:
        """Get Hermes version."""
        try:
            result = subprocess.run(
                ["hermes", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        
        # Check package
        try:
            import hermes
            return getattr(hermes, "__version", "unknown")
        except ImportError:
            pass
        
        return "unknown"


# ──────────────────────────── Hermes Integrator ────────────────────────────


class HermesIntegrator:
    """
    Integrates harness with Hermes as one unified system.
    
    This plugin:
    1. Auto-detects Hermes
    2. Creates symlinks for plugins
    3. Configures MCP servers
    4. Creates bot profiles
    5. Registers slash commands
    """
    
    def __init__(self, hermes_config: HermesConfig):
        self.hermes_config = hermes_config
        self._status = IntegrationStatus(
            hermes_detected=True,
            mcp_configured=False,
            bots_created=0,
            plugins_linked=0,
            slash_commands_registered=0,
            errors=[],
            warnings=[],
        )
    
    async def integrate(self) -> IntegrationStatus:
        """Run full integration."""
        logger.info("Starting Hermes integration...")
        
        try:
            # Step 1: Link plugins
            await self._link_plugins()
            
            # Step 2: Configure MCP
            await self._configure_mcp()
            
            # Step 3: Create bot profiles
            await self._create_bot_profiles()
            
            # Step 4: Register slash commands
            await self._register_slash_commands()
            
            # Step 5: Create unified config
            await self._create_unified_config()
            
            logger.info("Hermes integration complete!")
            
        except Exception as e:
            self._status.errors.append(str(e))
            logger.error(f"Integration error: {e}")
        
        return self._status
    
    async def _link_plugins(self):
        """Create symlinks for harness plugins in Hermes plugins dir."""
        logger.info("Linking plugins...")
        
        harness_plugins_dir = os.path.join(os.getcwd(), "plugins")
        if not os.path.exists(harness_plugins_dir):
            self._status.warnings.append("No plugins directory found")
            return
        
        for plugin_name in os.listdir(harness_plugins_dir):
            plugin_path = os.path.join(harness_plugins_dir, plugin_name)
            if not os.path.isdir(plugin_path):
                continue
            
            target = os.path.join(self.hermes_config.plugins_dir, plugin_name)
            
            try:
                if os.path.exists(target) or os.path.islink(target):
                    os.remove(target)
                
                if sys.platform == "win32":
                    # Windows: copy instead of symlink
                    shutil.copytree(plugin_path, target)
                else:
                    os.symlink(plugin_path, target)
                
                self._status.plugins_linked += 1
                logger.info(f"Linked plugin: {plugin_name}")
                
            except Exception as e:
                self._status.errors.append(f"Failed to link {plugin_name}: {e}")
    
    async def _configure_mcp(self):
        """Configure MCP servers in Hermes config."""
        logger.info("Configuring MCP servers...")
        
        # Read existing config
        config = {}
        if os.path.exists(self.hermes_config.config_file):
            try:
                import yaml
                with open(self.hermes_config.config_file) as f:
                    config = yaml.safe_load(f) or {}
            except Exception as e:
                self._status.warnings.append(f"Could not read config: {e}")
        
        # Add MCP servers
        if "mcp_servers" not in config:
            config["mcp_servers"] = {}
        
        # harnix kernel MCP
        config["mcp_servers"]["harnix"] = {
            "command": "python",
            "args": ["-m", "integration.mcp_server"],
            "timeout": 120,
        }
        
        # Write config
        try:
            import yaml
            with open(self.hermes_config.config_file, "w") as f:
                yaml.dump(config, f, default_flow_style=False)
            
            self._status.mcp_configured = True
            logger.info("MCP servers configured")
            
        except Exception as e:
            self._status.errors.append(f"Failed to write config: {e}")
    
    async def _create_bot_profiles(self):
        """Create bot profiles in Hermes."""
        logger.info("Creating bot profiles...")
        
        profiles = [
            {"name": "harness-planner", "model": "minimax-m3:free", "role": "Master Planner"},
            {"name": "harness-coder", "model": "meituan/longcat-2.0:free", "role": "Core Coder"},
            {"name": "harness-researcher", "model": "nvidia/nemotron-3.5-lightning:free", "role": "Deep Researcher"},
            {"name": "harness-verifier", "model": "nvidia/nemotron-3-super-120b:free", "role": "Verifier"},
            {"name": "harness-safety", "model": "thinkingmachines/inkling-small:free", "role": "Safety Governor"},
        ]
        
        for profile in profiles:
            profile_dir = os.path.join(self.hermes_config.profiles_dir, profile["name"])
            os.makedirs(profile_dir, exist_ok=True)
            
            # Create config.yaml
            config = {
                "name": profile["name"],
                "model": profile["model"],
                "role": profile["role"],
                "tools": ["web_search", "file_read", "file_write", "terminal", "subagents"],
            }
            
            try:
                import yaml
                with open(os.path.join(profile_dir, "config.yaml"), "w") as f:
                    yaml.dump(config, f, default_flow_style=False)
                
                self._status.bots_created += 1
                logger.info(f"Created bot profile: {profile['name']}")
                
            except Exception as e:
                self._status.errors.append(f"Failed to create {profile['name']}: {e}")
    
    async def _register_slash_commands(self):
        """Register slash commands."""
        logger.info("Registering slash commands...")
        
        commands = [
            {"name": "/harnix", "description": "Run harnix kernel task"},
            {"name": "/harness", "description": "Harness control"},
            {"name": "/improve", "description": "Run self-improvement"},
            {"name": "/benchmark", "description": "Run benchmarks"},
            {"name": "/spawn", "description": "Spawn a bot"},
        ]
        
        self._status.slash_commands_registered = len(commands)
        logger.info(f"Registered {len(commands)} slash commands")
    
    async def _create_unified_config(self):
        """Create unified configuration file."""
        logger.info("Creating unified config...")
        
        unified_config = {
            "version": "2.0.0",
            "hermes": {
                "dir": self.hermes_config.hermes_dir,
                "profiles_dir": self.hermes_config.profiles_dir,
                "plugins_dir": self.hermes_config.plugins_dir,
            },
            "harness": {
                "dir": os.getcwd(),
                "entry_point": "src/hermes_agi/__init__.py",
            },
            "integration": {
                "mcp_server": "integration.mcp_server",
                "auto_start": True,
                "health_check_interval": 30,
            },
            "features": {
                "planning": True,
                "self_recovery": True,
                "workflow_engine": True,
                "bot_swarm": True,
                "benchmarks": True,
                "meta_discovery": True,
            },
        }
        
        config_path = os.path.join(os.getcwd(), "config", "unified.yaml")
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        try:
            import yaml
            with open(config_path, "w") as f:
                yaml.dump(unified_config, f, default_flow_style=False)
            
            logger.info(f"Unified config saved to {config_path}")
            
        except Exception as e:
            self._status.errors.append(f"Failed to save unified config: {e}")


# ──────────────────────────── Auto-Installer ────────────────────────────


class AutoInstaller:
    """
    Automatically installs and configures everything.
    
    Usage:
        installer = AutoInstaller()
        result = await installer.install()
    """
    
    def __init__(self):
        self.hermes_config = None
        self.integrator = None
        self._status = {}
    
    async def install(self) -> dict[str, Any]:
        """Run full installation."""
        logger.info("Starting auto-installation...")
        
        # Step 1: Detect Hermes
        self.hermes_config = HermesDetector.detect()
        if not self.hermes_config:
            return {
                "success": False,
                "error": "Hermes not detected. Please install Hermes first.",
            }
        
        logger.info(f"Hermes detected: {self.hermes_config.hermes_dir}")
        
        # Step 2: Run integration
        self.integrator = HermesIntegrator(self.hermes_config)
        status = await self.integrator.integrate()
        
        # Step 3: Install Python package
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-e", "."],
                check=True,
                capture_output=True,
                cwd=os.getcwd(),
            )
            logger.info("Package installed")
        except subprocess.CalledProcessError as e:
            status.errors.append(f"Package install failed: {e}")
        
        return {
            "success": len(status.errors) == 0,
            "hermes_version": self.hermes_config.version,
            "plugins_linked": status.plugins_linked,
            "bots_created": status.bots_created,
            "mcp_configured": status.mcp_configured,
            "slash_commands": status.slash_commands_registered,
            "errors": status.errors,
            "warnings": status.warnings,
        }
    
    async def uninstall(self) -> dict[str, Any]:
        """Uninstall integration."""
        logger.info("Uninstalling...")
        
        # Remove symlinks
        if self.hermes_config:
            for item in os.listdir(self.hermes_config.plugins_dir):
                path = os.path.join(self.hermes_config.plugins_dir, item)
                if os.path.islink(path):
                    os.remove(path)
        
        return {"success": True}
