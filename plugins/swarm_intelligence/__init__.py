#!/usr/bin/env python3
"""
Swarm Intelligence Plugin — Decentralized agent swarm
=====================================================
Features:
- Create and manage swarm of agents
- Particle swarm optimization (PSO)
- Collective decision making
- Emergent behavior simulation
- Distributed problem solving
"""

from __future__ import annotations

import asyncio
import logging
import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("hermes_swarm_intelligence")

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


@dataclass
class Particle:
    """A particle in the swarm."""
    id: int
    position: List[float]
    velocity: List[float]
    best_position: List[float]
    best_score: float = float('-inf')


class SwarmIntelligence:
    """Swarm intelligence with PSO."""
    
    def __init__(self, dimensions: int = 2, num_particles: int = 10, 
                 inertia: float = 0.7, cognitive: float = 1.5, social: float = 1.5):
        self.dimensions = dimensions
        self.num_particles = num_particles
        self.inertia = inertia
        self.cognitive = cognitive
        self.social = social
        self.particles: List[Particle] = []
        self.global_best_position: Optional[List[float]] = None
        self.global_best_score = float('-inf')
        self.history: List[Dict[str, Any]] = []
    
    def initialize(self, bounds: Tuple[float, float] = (-10, 10)):
        """Initialize the swarm."""
        self.particles = []
        for i in range(self.num_particles):
            position = [random.uniform(*bounds) for _ in range(self.dimensions)]
            velocity = [random.uniform(-1, 1) for _ in range(self.dimensions)]
            particle = Particle(
                id=i,
                position=position,
                velocity=velocity,
                best_position=position.copy(),
                best_score=float('-inf'),
            )
            self.particles.append(particle)
    
    def optimize(self, objective: Callable[[List[float]], float], 
                 iterations: int = 50, bounds: Tuple[float, float] = (-10, 10)) -> Dict[str, Any]:
        """Run PSO optimization."""
        if not self.particles:
            self.initialize(bounds)
        
        for iteration in range(iterations):
            for particle in self.particles:
                # Evaluate
                score = objective(particle.position)
                
                # Update personal best
                if score > particle.best_score:
                    particle.best_score = score
                    particle.best_position = particle.position.copy()
                
                # Update global best
                if score > self.global_best_score:
                    self.global_best_score = score
                    self.global_best_position = particle.position.copy()
            
            # Update velocities and positions
            for particle in self.particles:
                for d in range(self.dimensions):
                    r1 = random.random()
                    r2 = random.random()
                    
                    cognitive_vel = self.cognitive * r1 * (particle.best_position[d] - particle.position[d])
                    social_vel = self.social * r2 * (self.global_best_position[d] - particle.position[d])
                    
                    particle.velocity[d] = (self.inertia * particle.velocity[d] + 
                                           cognitive_vel + social_vel)
                    particle.position[d] += particle.velocity[d]
                    
                    # Clamp to bounds
                    particle.position[d] = max(bounds[0], min(bounds[1], particle.position[d]))
            
            # Record history
            self.history.append({
                "iteration": iteration,
                "best_score": self.global_best_score,
                "best_position": self.global_best_position.copy() if self.global_best_position else None,
            })
        
        return {
            "success": True,
            "best_position": self.global_best_position,
            "best_score": self.global_best_score,
            "iterations": iterations,
            "particles": self.num_particles,
        }
    
    def get_convergence(self) -> List[float]:
        """Get best score per iteration."""
        return [h["best_score"] for h in self.history]
    
    def collective_decision(self, options: List[str], votes: Dict[int, str]) -> Dict[str, Any]:
        """Simple collective decision by voting."""
        vote_counts: Dict[str, int] = {}
        for option in options:
            vote_counts[option] = 0
        
        for particle_id, vote in votes.items():
            if vote in vote_counts:
                vote_counts[vote] += 1
        
        winner = max(vote_counts.items(), key=lambda x: x[1])
        
        return {
            "winner": winner[0],
            "votes": vote_counts,
            "total_votes": sum(vote_counts.values()),
        }


# ═══════════════════════════════════════════════════════════════════════════════════
# PLUGIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════════

class Plugin(PluginBase):
    """Swarm Intelligence Plugin"""
    
    def __init__(self):
        self.state = PluginState.REGISTERED
        self.manifest = PluginManifest(
            name="swarm_intelligence",
            version="1.0.0",
            description="Particle swarm optimization, collective decision-making, and emergent behavior simulation",
            license="MIT",
            source="internal",
            capabilities=["pso_optimization", "collective_decision", "swarm_coordination"],
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
        self.swarm: Optional[SwarmIntelligence] = None
    
    async def load(self) -> bool:
        self.swarm = SwarmIntelligence()
        self.state = PluginState.LOADED
        return True
    
    async def start(self) -> bool:
        if not self.swarm:
            self.swarm = SwarmIntelligence()
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
            "ready": self.swarm is not None,
        }
    
    # ── PUBLIC API ──────────────────────────────────────────────────────
    
    def initialize(self, dimensions: int = 2, num_particles: int = 10, bounds: Tuple[float, float] = (-10, 10)):
        self.swarm = SwarmIntelligence(dimensions=dimensions, num_particles=num_particles)
        self.swarm.initialize(bounds)
    
    def optimize(self, objective: Callable[[List[float]], float], iterations: int = 50, bounds: Tuple[float, float] = (-10, 10)) -> Dict[str, Any]:
        return self.swarm.optimize(objective, iterations, bounds)
    
    def get_convergence(self) -> List[float]:
        return self.swarm.get_convergence()
    
    def collective_decision(self, options: List[str], votes: Dict[int, str]) -> Dict[str, Any]:
        return self.swarm.collective_decision(options, votes)
    
    def get_capabilities(self) -> List[str]:
        return self.manifest.capabilities
