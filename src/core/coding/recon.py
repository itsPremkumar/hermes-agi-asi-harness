"""
Repository Reconnaissance — Discover build system, test system, CI/CD, conventions.
"""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReconStage(str, Enum):
    INIT = "init"
    STRUCTURE_DISCOVERED = "structure_discovered"
    BUILD_DISCOVERED = "build_discovered"
    TEST_DISCOVERED = "test_discovered"
    CI_DISCOVERED = "ci_discovered"
    CONVENTIONS_DISCOVERED = "conventions_discovered"
    COMPLETED = "completed"


@dataclass
class ReconResult:
    id: str
    repo_path: str
    stage: ReconStage = ReconStage.INIT
    files: list[str] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    build_system: str = ""
    test_framework: str = ""
    ci_platform: list[str] = field(default_factory=list)
    conventions: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    completed_at: float | None = None


class RepositoryRecon:
    """Run repository reconnaissance workflow."""
    
    def __init__(self):
        self.id = str(uuid.uuid4())
    
    def run(self, repo_path: str) -> ReconResult:
        """Run full reconnaissance."""
        result = ReconResult(id=str(uuid.uuid4()), repo_path=repo_path)
        
        try:
            # Stage 1: Structure
            result.stage = ReconStage.STRUCTURE_DISCOVERED
            result.files = self._discover_files(repo_path)
            
            # Stage 2: Build system
            result.stage = ReconStage.BUILD_DISCOVERED
            result.build_system = self._detect_build_system(repo_path)
            
            # Stage 3: Test system
            result.stage = ReconStage.TEST_DISCOVERED
            result.test_framework = self._detect_test_framework(repo_path)
            
            # Stage 4: CI/CD
            result.stage = ReconStage.CI_DISCOVERED
            result.ci_platform = self._detect_ci(repo_path)
            
            # Stage 5: Conventions
            result.stage = ReconStage.CONVENTIONS_DISCOVERED
            result.conventions = self._detect_conventions(repo_path)
            
            # Stage 6: Dependencies
            result.dependencies = self._detect_dependencies(repo_path)
            
            # Entry points
            result.entry_points = self._detect_entry_points(repo_path)
            
            result.stage = ReconStage.COMPLETED
            result.completed_at = time.time()
            
        except Exception as e:
            result.errors.append(str(e))
        
        return result
    
    def _discover_files(self, repo_path: str) -> list[str]:
        """Discover all source files."""
        files = []
        for root, dirs, filenames in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}]
            for f in filenames:
                if not f.startswith('.'):
                    files.append(os.path.join(root, f))
        return files
    
    def _detect_build_system(self, repo_path: str) -> str:
        """Detect build system."""
        build_files = {
            'Makefile': 'make',
            'CMakeLists.txt': 'cmake',
            'package.json': 'npm',
            'pyproject.toml': 'poetry',
            'setup.py': 'setuptools',
            'Cargo.toml': 'cargo',
            'go.mod': 'go',
            'build.gradle': 'gradle',
            'pom.xml': 'maven',
        }
        
        for filename, name in build_files.items():
            if os.path.exists(os.path.join(repo_path, filename)):
                return name
        return "unknown"
    
    def _detect_test_framework(self, repo_path: str) -> str:
        """Detect test framework."""
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}]
            for f in files:
                if f.startswith('test_') and f.endswith('.py'):
                    return "pytest"
                if f.endswith(('.test.js', '.spec.ts')):
                    return "jest"
                if f.endswith('_test.go'):
                    return "go_test"
        return "unknown"
    
    def _detect_ci(self, repo_path: str) -> list[str]:
        """Detect CI/CD platforms."""
        ci = []
        if os.path.exists(os.path.join(repo_path, '.github', 'workflows')):
            ci.append("github-actions")
        if os.path.exists(os.path.join(repo_path, '.gitlab-ci.yml')):
            ci.append("gitlab-ci")
        if os.path.exists(os.path.join(repo_path, 'Jenkinsfile')):
            ci.append("jenkins")
        if os.path.exists(os.path.join(repo_path, '.circleci')):
            ci.append("circleci")
        return ci
    
    def _detect_conventions(self, repo_path: str) -> list[str]:
        """Detect coding conventions."""
        conventions = []
        
        # Check for type hints
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}]
            for f in files:
                if f.endswith('.py'):
                    filepath = os.path.join(root, f)
                    try:
                        content = open(filepath, errors='ignore').read()
                        if '-> ' in content and ': ' in content:
                            conventions.append("type_hints")
                            break
                    except Exception:
                        pass
        
        # Check for async
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}]
            for f in files:
                if f.endswith('.py'):
                    filepath = os.path.join(root, f)
                    try:
                        content = open(filepath, errors='ignore').read()
                        if 'async def' in content or 'await ' in content:
                            conventions.append("async_await")
                            break
                    except Exception:
                        pass
        
        return list(set(conventions))
    
    def _detect_dependencies(self, repo_path: str) -> list[str]:
        """Detect dependencies."""
        deps = []
        
        requirements = os.path.join(repo_path, 'requirements.txt')
        if os.path.exists(requirements):
            try:
                with open(requirements) as f:
                    deps.extend(line.strip() for line in f if line.strip() and not line.startswith('#'))
            except Exception:
                pass
        
        package_json = os.path.join(repo_path, 'package.json')
        if os.path.exists(package_json):
            try:
                import json
                with open(package_json) as f:
                    pkg = json.load(f)
                    deps.extend(pkg.get('dependencies', {}).keys())
            except Exception:
                pass
        
        return deps
    
    def _detect_entry_points(self, repo_path: str) -> list[str]:
        """Detect application entry points."""
        entry_points = []
        candidates = [
            'main.py', 'app.py', 'server.py', 'index.js', 'index.ts',
            'manage.py', 'wsgi.py', 'asgi.py', 'src/main.py', 'src/app.py',
        ]
        
        for candidate in candidates:
            if os.path.exists(os.path.join(repo_path, candidate)):
                entry_points.append(candidate)
        
        return entry_points
    
    def get_state(self) -> dict[str, Any]:
        return {
            "id": self.id,
        }
