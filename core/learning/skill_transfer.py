"""
Skill Transfer — Cross-domain skill abstraction.

A skill should be represented abstractly:
  "verify external state after mutation"

Then applied to:
  GitHub, Calendar, Database, Cloud, Robotics

This enables cross-domain transfer.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AbstractSkill:
    """A skill represented abstractly, independent of domain."""
    id: str
    name: str
    description: str
    preconditions: list[str]
    steps: list[dict[str, Any]]
    postconditions: list[str]
    verification_methods: list[str]
    source_domains: list[str] = field(default_factory=list)
    target_domains: list[str] = field(default_factory=list)
    transfer_count: int = 0
    success_rate: float = 0.5


@dataclass
class SkillInstance:
    """A concrete skill instance applied to a specific domain."""
    id: str
    skill_id: str
    domain: str
    parameters: dict[str, Any]
    success_count: int = 0
    failure_count: int = 0
    last_used: float = 0.0


class SkillTransfer:
    """Transfer skills across domains."""

    def __init__(self):
        self.skills: dict[str, AbstractSkill] = {}
        self.instances: dict[str, SkillInstance] = {}

    def define_skill(self, name: str, description: str,
                     preconditions: list[str], steps: list[dict[str, Any]],
                     postconditions: list[str],
                     verification_methods: list[str],
                     source_domains: list[str] | None = None) -> AbstractSkill:
        skill = AbstractSkill(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            preconditions=preconditions,
            steps=steps,
            postconditions=postconditions,
            verification_methods=verification_methods,
            source_domains=source_domains or [],
        )
        self.skills[skill.id] = skill
        return skill

    def instantiate_skill(self, skill_id: str, domain: str,
                          parameters: dict[str, Any]) -> SkillInstance:
        instance = SkillInstance(
            id=str(uuid.uuid4()),
            skill_id=skill_id,
            domain=domain,
            parameters=parameters,
            last_used=time.time(),
        )
        self.instances[instance.id] = instance
        return instance

    def transfer_skill(self, skill_id: str, target_domain: str,
                       parameters: dict[str, Any] | None = None) -> SkillInstance | None:
        """Transfer an abstract skill to a new domain."""
        skill = self.skills.get(skill_id)
        if not skill:
            return None
        
        instance = self.instantiate_skill(
            skill_id=skill_id,
            domain=target_domain,
            parameters=parameters or {},
        )
        
        skill.target_domains.append(target_domain)
        skill.transfer_count += 1
        
        return instance

    def find_applicable_skills(self, domain: str,
                               available_preconditions: list[str]) -> list[AbstractSkill]:
        """Find skills applicable in a given domain."""
        applicable = []
        for skill in self.skills.values():
            if domain in skill.source_domains or domain in skill.target_domains:
                # Check preconditions
                if all(p in available_preconditions for p in skill.preconditions):
                    applicable.append(skill)
        return applicable

    def get_skill(self, skill_id: str) -> AbstractSkill | None:
        return self.skills.get(skill_id)

    def get_instances_for_domain(self, domain: str) -> list[SkillInstance]:
        return [i for i in self.instances.values() if i.domain == domain]

    def get_state(self) -> dict[str, Any]:
        return {
            "abstract_skills": len(self.skills),
            "instances": len(self.instances),
            "total_transfers": sum(s.transfer_count for s in self.skills.values()),
        }
