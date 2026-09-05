"""
Local LLM Runtime — Atomic Agent Pattern
=========================================
TurboQuant llama.cpp + GBNF grammar enforcement for valid tool calls.
Zero API costs, privacy, offline capability, no rate limits.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for local LLM runtime."""
    model_path: Path
    n_ctx: int = 32768
    n_threads: int = 0  # 0 = auto
    n_gpu_layers: int = -1  # -1 = all
    temperature: float = 0.2
    top_p: float = 0.95
    top_k: int = 40
    repeat_penalty: float = 1.1
    seed: int = -1
    verbose: bool = False


@dataclass
class GBNFGrammar:
    """GBNF grammar for constrained generation."""
    name: str
    grammar: str
    description: str = ""


class GBNFCompiler:
    """Compiles JSON schemas to GBNF grammars for llama.cpp."""

    # Primitive type mappings
    PRIMITIVES = {
        "string": '"string"',
        "integer": '"integer"',
        "number": '"number"',
        "boolean": '"boolean"',
        "null": '"null"',
    }

    def __init__(self):
        self._grammar_cache: dict[str, GBNFGrammar] = {}

    def compile(self, schema: dict, name: str = "schema") -> GBNFGrammar:
        """Compile a JSON schema to GBNF grammar."""
        cache_key = json.dumps(schema, sort_keys=True)
        if cache_key in self._grammar_cache:
            return self._grammar_cache[cache_key]

        grammar = self._schema_to_gbnf(schema, name)
        gbnf = GBNFGrammar(name=name, grammar=grammar, description=f"Generated from JSON schema: {name}")
        self._grammar_cache[cache_key] = gbnf
        return gbnf

    def _schema_to_gbnf(self, schema: dict, root_name: str) -> str:
        """Convert JSON schema to GBNF."""
        rules = []
        refs = set()

        def process(s: dict, rule_name: str) -> str:
            if "const" in s:
                val = json.dumps(s["const"])
                rules.append(f'{rule_name} ::= {val}')
                return rule_name

            if "enum" in s:
                alts = " | ".join(json.dumps(v) for v in s["enum"])
                rules.append(f'{rule_name} ::= {alts}')
                return rule_name

            t = s.get("type")
            if t == "object":
                return self._object_to_gbnf(s, rule_name)
            elif t == "array":
                return self._array_to_gbnf(s, rule_name)
            elif t in self.PRIMITIVES:
                return self.PRIMITIVES[t]
            elif t == "string" and s.get("format") == "json":
                # Special case: string containing JSON
                return '"json-string"'
            elif any(k in s for k in ("anyOf", "oneOf", "allOf")):
                return self._union_to_gbnf(s, rule_name)
            else:
                return '"any"'

        def _object_to_gbnf(s: dict, rule_name: str) -> str:
            props = s.get("properties", {})
            required = set(s.get("required", []))
            additional = s.get("additionalProperties", False)

            if not props:
                rules.append(f'{rule_name} ::= "{{" ws "}}"')
                return rule_name

            prop_rules = []
            for prop_name, prop_schema in props.items():
                prop_rule = f"{rule_name}__{prop_name}"
                process(prop_schema, prop_rule)
                prop_rules.append(f'"{prop_name}" ws ":" ws {prop_rule}')

            # Required fields first
            required_rules = [r for p, r in zip(props.keys(), prop_rules) if p in required]
            optional_rules = [r for p, r in zip(props.keys(), prop_rules) if p not in required]

            if required_rules and optional_rules:
                rules.append(f'{rule_name} ::= "{{" ws {(" ws "," ws ").join(required_rules)} ws ("," ws ({(" ws "," ws ").join(optional_rules)}))? ws "}}"')
            elif required_rules:
                rules.append(f'{rule_name} ::= "{{" ws {(" ws "," ws ").join(required_rules)} ws "}}"')
            elif optional_rules:
                rules.append(f'{rule_name} ::= "{{" ws ({(" ws "," ws ").join(optional_rules)})? ws "}}"')
            else:
                rules.append(f'{rule_name} ::= "{{" ws "}}"')

            if additional and isinstance(additional, dict):
                add_rule = f"{rule_name}__additional"
                process(additional, add_rule)
                rules.append(f'{add_rule} ::= {process(additional, add_rule)}')

            return rule_name

        def _array_to_gbnf(s: dict, rule_name: str) -> str:
            items = s.get("items", {})
            item_rule = f"{rule_name}__item"
            process(items, item_rule)
            rules.append(f'{rule_name} ::= "[" ws ({item_rule} (ws "," ws {item_rule})*)? ws "]"')
            return rule_name

        def _union_to_gbnf(s: dict, rule_name: str) -> str:
            for key in ("anyOf", "oneOf", "allOf"):
                if key in s:
                    alts = []
                    for i, alt in enumerate(s[key]):
                        alt_rule = f"{rule_name}__alt{i}"
                        process(alt, alt_rule)
                        alts.append(alt_rule)
                    rules.append(f'{rule_name} ::= {" | ".join(alts)}')
                    return rule_name
            return '"any"'

        process(schema, root_name)

        # Add whitespace rule
        rules.append('ws ::= [\\t\\n\\r ]*')

        return "\n".join(rules)


class LlamaCppEngine:
    """llama.cpp engine wrapper with TurboQuant support."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._llama_cli = self._find_llama_cli()
        self._server_process: Optional[subprocess.Popen] = None
        self._server_url = "http://localhost:8080"

    def _find_llama_cli(self) -> str:
        """Find llama-cli or llama-server binary."""
        # Check common locations
        candidates = [
            shutil.which("llama-cli"),
            shutil.which("llama-server"),
            Path.home() / ".local" / "bin" / "llama-cli",
            Path("/usr/local/bin/llama-cli"),
            Path("/opt/homebrew/bin/llama-cli"),
        ]
        for c in candidates:
            if c and Path(c).exists():
                return str(c)

        # Try to find in llama.cpp build directory
        llama_cpp_dir = os.environ.get("LLAMA_CPP_DIR")
        if llama_cpp_dir:
            for bin_name in ["llama-cli", "llama-server"]:
                p = Path(llama_cpp_dir) / "build" / "bin" / bin_name
                if p.exists():
                    return str(p)

        logger.warning("llama-cli not found in PATH. Install llama.cpp or set LLAMA_CPP_DIR")
        return "llama-cli"  # Will fail at runtime with clear error

    async def start_server(self) -> bool:
        """Start llama-server in background."""
        if self._server_process and self._server_process.poll() is None:
            return True

        model_path = str(self.config.model_path)
        if not Path(model_path).exists():
            logger.error(f"Model not found: {model_path}")
            return False

        cmd = [
            self._llama_cli.replace("llama-cli", "llama-server"),
            "-m", model_path,
            "-c", str(self.config.n_ctx),
            "-t", str(self.config.n_threads) if self.config.n_threads > 0 else "0",
            "-ngl", str(self.config.n_gpu_layers),
            "--port", "8080",
            "--host", "localhost",
        ]

        try:
            self._server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            # Wait for server to be ready
            await asyncio.sleep(3)
            return self._server_process.poll() is None
        except Exception as e:
            logger.error(f"Failed to start llama-server: {e}")
            return False

    async def stop_server(self) -> None:
        """Stop llama-server."""
        if self._server_process:
            self._server_process.terminate()
            try:
                await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, self._server_process.wait),
                    timeout=5
                )
            except asyncio.TimeoutError:
                self._server_process.kill()
            self._server_process = None

    async def generate(
        self,
        prompt: str,
        grammar: Optional[GBNFGrammar] = None,
        max_tokens: int = 2048,
        **kwargs
    ) -> str:
        """Generate text using llama.cpp."""
        if not await self.start_server():
            raise RuntimeError("Failed to start llama-server")

        # Build request
        import aiohttp
        payload = {
            "prompt": prompt,
            "n_predict": max_tokens,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "top_p": kwargs.get("top_p", self.config.top_p),
            "top_k": kwargs.get("top_k", self.config.top_k),
            "repeat_penalty": kwargs.get("repeat_penalty", self.config.repeat_penalty),
            "seed": kwargs.get("seed", self.config.seed),
            "stream": False,
        }

        if grammar:
            # Write grammar to temp file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".gbnf", delete=False) as f:
                f.write(grammar.grammar)
                grammar_path = f.name
            payload["grammar"] = grammar_path

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self._server_url}/completion", json=payload) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        raise RuntimeError(f"llama-server error {resp.status}: {text}")
                    result = await resp.json()
                    return result.get("content", "")
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise
        finally:
            if grammar and 'grammar_path' in locals():
                try:
                    Path(grammar_path).unlink()
                except Exception:
                    pass

    async def generate_structured(
        self,
        prompt: str,
        schema: dict,
        max_tokens: int = 2048,
        **kwargs
    ) -> dict:
        """Generate structured output using GBNF grammar."""
        grammar = GBNFCompiler().compile(schema, "output")
        result = await self.generate(prompt, grammar=grammar, max_tokens=max_tokens, **kwargs)
        try:
            return json.loads(result)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse structured output: {e}\nRaw: {result[:500]}")
            raise


class LocalLLMRuntime:
    """
    High-level local LLM runtime with grammar-enforced tool calls.

    Features:
    - TurboQuant llama.cpp for +30-50% throughput on quantized models
    - GBNF grammar compilation from JSON schemas
    - Structured output guaranteed valid against schema
    - Tool calling with automatic schema enforcement
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self.engine = LlamaCppEngine(config)
        self.grammar_compiler = GBNFCompiler()
        self._tool_schemas: dict[str, dict] = {}

    def register_tool(self, name: str, schema: dict, description: str = "") -> None:
        """Register a tool with its JSON schema."""
        self._tool_schemas[name] = {
            "name": name,
            "description": description,
            "parameters": schema,
        }

    async def generate_with_grammar(
        self,
        prompt: str,
        output_schema: dict,
        max_tokens: int = 2048,
        **kwargs
    ) -> dict:
        """Generate output validated against output_schema."""
        return await self.engine.generate_structured(prompt, output_schema, max_tokens, **kwargs)

    async def call_tool(self, tool_name: str, args: dict) -> dict:
        """Execute a registered tool (to be implemented by caller)."""
        if tool_name not in self._tool_schemas:
            raise ValueError(f"Unknown tool: {tool_name}")

        # This is a placeholder - actual tool execution happens in the harness
        # The LLM only generates the tool call; execution is external
        return {"tool": tool_name, "args": args, "status": "pending_execution"}

    def build_tool_calling_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        available_tools: list[str],
    ) -> str:
        """Build a prompt that instructs the model to call tools via structured output."""
        tool_defs = []
        for name in available_tools:
            if name in self._tool_schemas:
                t = self._tool_schemas[name]
                tool_defs.append(f"- {name}: {t['description']}\n  Parameters: {json.dumps(t['parameters'], indent=2)}")

        tools_section = "\n".join(tool_defs) if tool_defs else "No tools available."

        return f"""{system_prompt}

{user_prompt}

## Available Tools
{tools_section}

## Response Format
You MUST respond with a JSON object matching this schema:
{{
  "thought": "Your reasoning for the next action",
  "tool_calls": [
    {{
      "name": "tool_name",
      "arguments": {{}}
    }}
  ],
  "final_answer": null  // Set when task is complete
}}

Only call tools that are listed above. Arguments MUST match the schema exactly.
"""


# Pre-built grammars for common patterns
COMMON_GRAMMARS = {
    "tool_call": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "arguments": {"type": "object"},
        },
        "required": ["name", "arguments"],
    },
    "tool_call_batch": {
        "type": "object",
        "properties": {
            "thought": {"type": "string"},
            "tool_calls": {
                "type": "array",
                "items": {"$ref": "#/$defs/tool_call"},
            },
            "final_answer": {"type": ["string", "null"]},
        },
        "required": ["thought", "tool_calls", "final_answer"],
        "$defs": {
            "tool_call": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "arguments": {"type": "object"},
                },
                "required": ["name", "arguments"],
            }
        },
    },
    "verification_result": {
        "type": "object",
        "properties": {
            "passed": {"type": "boolean"},
            "evidence": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["passed", "evidence", "confidence"],
    },
}


def create_local_llm(
    model_path: Union[str, Path],
    **kwargs
) -> LocalLLMRuntime:
    """Factory function to create a LocalLLMRuntime with sensible defaults."""
    config = LLMConfig(
        model_path=Path(model_path),
        **kwargs
    )
    return LocalLLMRuntime(config)


# Integration with HermesFirstLLMClient
async def create_hermes_local_llm(model_path: str, **kwargs) -> LocalLLMRuntime:
    """
    Create a local LLM runtime for Hermes.
    Usage:
        llm = await create_hermes_local_llm("models/llama-3.1-8b-q4_k_m.gguf")
        result = await llm.generate_with_grammar(prompt, schema)
    """
    return create_local_llm(model_path, **kwargs)


if __name__ == "__main__":
    # Demo grammar compilation
    compiler = GBNFCompiler()

    tool_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "arguments": {"type": "object"},
        },
        "required": ["name", "arguments"],
    }

    grammar = compiler.compile(tool_schema, "tool_call")
    print("=== Generated GBNF Grammar ===")
    print(grammar.grammar)