"""
Repository Digital Twin — Understand any codebase before modifying it.

Represents: files, modules, packages, dependencies, APIs, schemas, databases,
configuration, tests, CI/CD, deployment, conventions, history, runtime telemetry.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class SymbolType(str, Enum):
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    VARIABLE = "variable"
    IMPORT = "import"
    INTERFACE = "interface"
    TYPE = "type"
    CONSTANT = "constant"


class EdgeType(str, Enum):
    IMPORTS = "imports"
    CALLS = "calls"
    INHERITS = "inherits"
    IMPLEMENTS = "implements"
    READS = "reads"
    WRITES = "writes"
    PUBLISHES = "publishes"
    SUBSCRIBES = "subscribes"
    CONFIGURES = "configures"
    TESTS = "tests"
    BUILDS = "builds"
    DEPLOYS = "deploys"


class Confidence(str, Enum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    ASSUMED = "assumed"
    UNKNOWN = "unknown"
    STALE = "stale"
    CONFLICTING = "conflicting"


@dataclass
class Symbol:
    name: str
    symbol_type: SymbolType
    file_path: str
    line_number: int
    docstring: str = ""
    signature: str = ""
    confidence: Confidence = Confidence.OBSERVED
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    source: str
    target: str
    edge_type: EdgeType
    confidence: Confidence = Confidence.OBSERVED
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FileNode:
    path: str
    language: str
    size_bytes: int
    lines: int
    symbols: List[Symbol] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    hash_sha256: str = ""
    last_modified: float = 0.0
    test_coverage: float = 0.0


@dataclass
class BuildSystem:
    name: str  # make, cmake, npm, poetry, cargo, etc.
    config_file: str = ""
    build_command: str = ""
    test_command: str = ""
    dependencies: List[str] = field(default_factory=list)


@dataclass
class TestSystem:
    framework: str  # pytest, jest, go test, etc.
    test_dirs: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)
    coverage_tool: str = ""


@dataclass
class CIDeployment:
    platform: str  # github-actions, gitlab-ci, jenkins, etc.
    config_files: List[str] = field(default_factory=list)
    environments: List[str] = field(default_factory=list)
    deployment_targets: List[str] = field(default_factory=list)


@dataclass
class Convention:
    name: str
    description: str
    pattern: str
    confidence: Confidence = Confidence.INFERRED


class RepositoryDigitalTwin:
    """Complete digital twin of a software repository."""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.id = str(uuid.uuid4())
        self.name = self.repo_path.name
        self.created_at = time.time()
        
        # Core structure
        self.files: Dict[str, FileNode] = {}
        self.symbols: Dict[str, Symbol] = {}
        self.edges: List[Edge] = []
        self.modules: Dict[str, List[str]] = {}  # module_name → [file_paths]
        
        # Build/test/CI
        self.build_system: Optional[BuildSystem] = None
        self.test_system: Optional[TestSystem] = None
        self.ci_deployment: Optional[CIDeployment] = None
        
        # Metadata
        self.conventions: List[Convention] = []
        self.entry_points: List[str] = []
        self.api_surface: List[Symbol] = []
        self.dependency_graph: Dict[str, List[str]] = {}
        self.technical_debt: List[Dict[str, Any]] = []
        self.known_bugs: List[Dict[str, Any]] = []
        
        # History
        self.commit_count = 0
        self.contributor_count = 0
        self.age_days = 0
        
    def discover(self) -> 'RepositoryDigitalTwin':
        """Run full repository discovery."""
        self._discover_files()
        self._build_symbol_table()
        self._build_code_graph()
        self._discover_build_system()
        self._discover_test_system()
        self._discover_ci()
        self._discover_entry_points()
        self._infer_conventions()
        self._analyze_git_history()
        return self
    
    def _discover_files(self):
        """Discover all files in the repository."""
        import hashlib
        
        for root, dirs, files in os.walk(self.repo_path):
            # Skip common non-project directories
            dirs[:] = [d for d in dirs if d not in {
                '.git', '__pycache__', 'node_modules', '.venv', 'venv',
                '.tox', '.eggs', 'build', 'dist', '.mypy_cache'
            }]
            
            for filename in files:
                filepath = Path(root) / filename
                rel_path = str(filepath.relative_to(self.repo_path))
                
                try:
                    stat = filepath.stat()
                    content = filepath.read_text(errors='ignore')
                    lines = content.count('\n')
                    
                    # Detect language
                    language = self._detect_language(filename)
                    
                    file_node = FileNode(
                        path=rel_path,
                        language=language,
                        size_bytes=stat.st_size,
                        lines=lines,
                        hash_sha256=hashlib.sha256(content.encode()).hexdigest()[:16],
                        last_modified=stat.st_mtime,
                    )
                    
                    self.files[rel_path] = file_node
                    
                except (OSError, UnicodeDecodeError):
                    continue
    
    def _detect_language(self, filename: str) -> str:
        """Detect programming language from filename."""
        ext_map = {
            '.py': 'python', '.pyi': 'python',
            '.js': 'javascript', '.jsx': 'javascript', '.mjs': 'javascript',
            '.ts': 'typescript', '.tsx': 'typescript',
            '.java': 'java', '.kt': 'kotlin', '.scala': 'scala',
            '.go': 'go', '.rs': 'rust',
            '.c': 'c', '.h': 'c', '.cpp': 'cpp', '.hpp': 'cpp',
            '.rb': 'ruby', '.php': 'php',
            '.swift': 'swift', '.m': 'objective-c',
            '.sql': 'sql',
            '.html': 'html', '.css': 'css', '.scss': 'css',
            '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml', '.toml': 'toml',
            '.md': 'markdown', '.rst': 'rst',
            '.sh': 'shell', '.bash': 'shell',
            '.tf': 'terraform', '.hcl': 'terraform',
            '.dockerfile': 'docker', 'Dockerfile': 'docker',
        }
        
        basename = os.path.basename(filename)
        if basename in ext_map:
            return ext_map[basename]
        
        ext = os.path.splitext(filename)[1].lower()
        return ext_map.get(ext, 'unknown')
    
    def _build_symbol_table(self):
        """Build symbol table from source files."""
        for filepath, file_node in self.files.items():
            if file_node.language == 'python':
                self._index_python_symbols(filepath, file_node)
            elif file_node.language in ('javascript', 'typescript'):
                self._index_js_symbols(filepath, file_node)
            # Add more languages as needed
    
    def _index_python_symbols(self, filepath: str, file_node: FileNode):
        """Index Python symbols."""
        full_path = self.repo_path / filepath
        try:
            content = full_path.read_text(errors='ignore')
            lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                # Classes
                class_match = re.match(r'^class\s+(\w+)', line)
                if class_match:
                    symbol = Symbol(
                        name=class_match.group(1),
                        symbol_type=SymbolType.CLASS,
                        file_path=filepath,
                        line_number=i,
                    )
                    file_node.symbols.append(symbol)
                    self.symbols[f"{filepath}::{class_match.group(1)}"] = symbol
                
                # Functions
                func_match = re.match(r'^(?:async\s+)?def\s+(\w+)', line)
                if func_match:
                    symbol = Symbol(
                        name=func_match.group(1),
                        symbol_type=SymbolType.FUNCTION,
                        file_path=filepath,
                        line_number=i,
                    )
                    file_node.symbols.append(symbol)
                    self.symbols[f"{filepath}::{func_match.group(1)}"] = symbol
                
                # Imports
                import_match = re.match(r'^(?:from\s+(\S+)\s+)?import\s+(\S+)', line)
                if import_match:
                    module = import_match.group(1) or import_match.group(2)
                    file_node.imports.append(module)
                
        except (OSError, UnicodeDecodeError):
            pass
    
    def _index_js_symbols(self, filepath: str, file_node: FileNode):
        """Index JavaScript/TypeScript symbols."""
        full_path = self.repo_path / filepath
        try:
            content = full_path.read_text(errors='ignore')
            lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                # Functions
                func_match = re.match(r'^(?:export\s+)?(?:async\s+)?function\s+(\w+)', line)
                if func_match:
                    symbol = Symbol(
                        name=func_match.group(1),
                        symbol_type=SymbolType.FUNCTION,
                        file_path=filepath,
                        line_number=i,
                    )
                    file_node.symbols.append(symbol)
                    self.symbols[f"{filepath}::{func_match.group(1)}"] = symbol
                
                # Classes
                class_match = re.match(r'^(?:export\s+)?class\s+(\w+)', line)
                if class_match:
                    symbol = Symbol(
                        name=class_match.group(1),
                        symbol_type=SymbolType.CLASS,
                        file_path=filepath,
                        line_number=i,
                    )
                    file_node.symbols.append(symbol)
                    self.symbols[f"{filepath}::{class_match.group(1)}"] = symbol
                
                # Imports
                import_match = re.match(r'^import\s+.*from\s+[\'"]([^\'"]+)[\'"]', line)
                if import_match:
                    file_node.imports.append(import_match.group(1))
                
        except (OSError, UnicodeDecodeError):
            pass
    
    def _build_code_graph(self):
        """Build code dependency graph."""
        for filepath, file_node in self.files.items():
            for imp in file_node.imports:
                # Find which file this import resolves to
                target = self._resolve_import(imp, filepath)
                if target:
                    edge = Edge(
                        source=filepath,
                        target=target,
                        edge_type=EdgeType.IMPORTS,
                    )
                    self.edges.append(edge)
                    
                    # Track in dependency graph
                    if filepath not in self.dependency_graph:
                        self.dependency_graph[filepath] = []
                    self.dependency_graph[filepath].append(target)
    
    def _resolve_import(self, import_path: str, from_file: str) -> Optional[str]:
        """Resolve an import path to a file in the repository."""
        # Handle relative imports
        if import_path.startswith('.'):
            base = Path(from_file).parent
            parts = import_path.split('.')
            for part in parts:
                if part == '':
                    base = base.parent
                else:
                    base = base / part
                    # Check for file
                    for ext in ['', '.py', '.js', '.ts', '/__init__.py', '/index.js']:
                        candidate = str(base) + ext
                        if candidate in self.files:
                            return candidate
        
        # Handle absolute imports
        parts = import_path.replace('-', '_').split('.')
        for ext in ['', '.py', '/__init__.py']:
            candidate = str(Path(*parts)) + ext
            if candidate in self.files:
                return candidate
        
        return None
    
    def _discover_build_system(self):
        """Discover the build system."""
        build_files = {
            'Makefile': ('make', 'make'),
            'CMakeLists.txt': ('cmake', 'cmake --build .'),
            'package.json': ('npm', 'npm test'),
            'pyproject.toml': ('poetry', 'poetry run pytest'),
            'setup.py': ('setuptools', 'python -m pytest'),
            'setup.cfg': ('setuptools', 'python -m pytest'),
            'Cargo.toml': ('cargo', 'cargo test'),
            'go.mod': ('go', 'go test ./...'),
            'build.gradle': ('gradle', 'gradle test'),
            'pom.xml': ('maven', 'mvn test'),
        }
        
        for filename, (name, test_cmd) in build_files.items():
            if (self.repo_path / filename).exists():
                self.build_system = BuildSystem(
                    name=name,
                    config_file=filename,
                    test_command=test_cmd,
                )
                break
    
    def _discover_test_system(self):
        """Discover the test framework."""
        test_dirs = ['tests', 'test', '__tests__', 'spec']
        test_patterns = ['test_*.py', '*_test.py', '*.test.js', '*.spec.ts']
        
        discovered_dirs = []
        discovered_files = []
        
        for test_dir in test_dirs:
            dir_path = self.repo_path / test_dir
            if dir_path.is_dir():
                discovered_dirs.append(test_dir)
        
        for pattern in test_patterns:
            for test_file in self.repo_path.rglob(pattern):
                rel_path = str(test_file.relative_to(self.repo_path))
                discovered_files.append(rel_path)
        
        if discovered_dirs or discovered_files:
            framework = "pytest" if any(f.endswith('.py') for f in discovered_files) else "jest"
            self.test_system = TestSystem(
                framework=framework,
                test_dirs=discovered_dirs,
                test_files=discovered_files,
            )
    
    def _discover_ci(self):
        """Discover CI/CD configuration."""
        ci_files = [
            '.github/workflows',
            '.gitlab-ci.yml',
            'Jenkinsfile',
            '.circleci/config.yml',
            '.travis.yml',
        ]
        
        for ci_path in ci_files:
            full_path = self.repo_path / ci_path
            if full_path.exists():
                platform = "github-actions" if "github" in ci_path else \
                          "gitlab-ci" if "gitlab" in ci_path else \
                          "jenkins" if "Jenkins" in ci_path else "other"
                self.ci_deployment = CIDeployment(
                    platform=platform,
                    config_files=[ci_path],
                )
                break
    
    def _discover_entry_points(self):
        """Discover application entry points."""
        entry_point_files = [
            'main.py', 'app.py', 'server.py', 'index.js', 'index.ts',
            'manage.py', 'wsgi.py', 'asgi.py', 'app/__init__.py',
            'src/main.py', 'src/app.py', 'src/index.ts',
        ]
        
        for ep in entry_point_files:
            if (self.repo_path / ep).exists():
                self.entry_points.append(ep)
    
    def _infer_conventions(self):
        """Infer coding conventions from the codebase."""
        # Check for type hints
        has_type_hints = False
        for file_node in self.files.values():
            if file_node.language == 'python':
                full_path = self.repo_path / file_node.path
                try:
                    content = full_path.read_text(errors='ignore')
                    if '-> ' in content or ': ' in content:
                        has_type_hints = True
                        break
                except:
                    pass
        
        if has_type_hints:
            self.conventions.append(Convention(
                name="type_hints",
                description="Uses Python type hints",
                pattern="def foo(x: int) -> str",
            ))
        
        # Check for async patterns
        has_async = False
        for file_node in list(self.files.values())[:20]:
            full_path = self.repo_path / file_node.path
            try:
                content = full_path.read_text(errors='ignore')
                if 'async def' in content or 'await ' in content:
                    has_async = True
                    break
            except:
                pass
        
        if has_async:
            self.conventions.append(Convention(
                name="async_await",
                description="Uses async/await pattern",
                pattern="async def foo(): await bar()",
            ))
    
    def _analyze_git_history(self):
        """Analyze git history for repository metadata."""
        try:
            result = subprocess.run(
                ['git', 'log', '--oneline'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                self.commit_count = len(result.stdout.strip().split('\n'))
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        try:
            result = subprocess.run(
                ['git', 'shortlog', '-sn', '--all'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                self.contributor_count = len(result.stdout.strip().split('\n'))
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
    
    def get_blast_radius(self, filepath: str) -> List[str]:
        """Compute blast radius of changing a file."""
        visited = set()
        queue = [filepath]
        
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            
            # Find all files that depend on this file
            for edge in self.edges:
                if edge.target == current and edge.source not in visited:
                    queue.append(edge.source)
        
        return list(visited - {filepath})
    
    def get_symbol(self, name: str) -> Optional[Symbol]:
        """Get a symbol by name."""
        return self.symbols.get(name)
    
    def get_symbols_by_type(self, symbol_type: SymbolType) -> List[Symbol]:
        """Get all symbols of a given type."""
        return [s for s in self.symbols.values() if s.symbol_type == symbol_type]
    
    def get_file_dependencies(self, filepath: str) -> List[str]:
        """Get all dependencies of a file."""
        return self.dependency_graph.get(filepath, [])
    
    def get_reverse_dependencies(self, filepath: str) -> List[str]:
        """Get all files that depend on this file."""
        return [src for src, deps in self.dependency_graph.items() if filepath in deps]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get repository statistics."""
        languages = {}
        for f in self.files.values():
            lang = f.language
            languages[lang] = languages.get(lang, 0) + 1
        
        total_lines = sum(f.lines for f in self.files.values())
        
        return {
            "total_files": len(self.files),
            "total_symbols": len(self.symbols),
            "total_edges": len(self.edges),
            "total_lines": total_lines,
            "languages": languages,
            "modules": len(self.modules),
            "conventions": len(self.conventions),
            "entry_points": len(self.entry_points),
            "commits": self.commit_count,
            "contributors": self.contributor_count,
            "build_system": self.build_system.name if self.build_system else None,
            "test_framework": self.test_system.framework if self.test_system else None,
            "ci_platform": self.ci_deployment.platform if self.ci_deployment else None,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "path": str(self.repo_path),
            "stats": self.get_stats(),
            "entry_points": self.entry_points,
            "build_system": self.build_system.__dict__ if self.build_system else None,
            "test_system": self.test_system.__dict__ if self.test_system else None,
            "ci_deployment": self.ci_deployment.__dict__ if self.ci_deployment else None,
            "conventions": [c.__dict__ for c in self.conventions],
        }
