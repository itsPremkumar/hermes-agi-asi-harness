"""
LLM-Powered Planning Engine — Real reasoning with actual LLM calls.

Inspired by NVIDIA AVO: sustained autonomous operation with domain knowledge.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ──────────────────────────── LLM Client ────────────────────────────


class LLMClient:
    """
    Async LLM client for making real API calls.
    Supports OpenRouter, OpenAI, and local models.
    """
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
        self.base_url = base_url or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.model = model or os.getenv("LLM_MODEL", "meituan/longcat-2.0:free")
        self._client = None
    
    async def _get_client(self):
        """Get or create async client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )
            except ImportError:
                logger.warning("openai package not installed, using mock responses")
                self._client = MockClient()
        return self._client
    
    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Send a chat completion request."""
        client = await self._get_client()
        
        try:
            response = await client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return self._fallback_response(messages)
    
    async def chat_json(
        self,
        messages: list[dict[str, str]],
        model: str = None,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Send a chat request expecting JSON response."""
        client = await self._get_client()
        
        try:
            response = await client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.error(f"LLM JSON call failed: {e}")
            return {}
    
    def _fallback_response(self, messages: list[dict[str, str]]) -> str:
        """Generate fallback response when LLM is unavailable."""
        last_msg = messages[-1]["content"] if messages else ""
        return f"LLM unavailable. Task: {last_msg[:100]}"


class MockClient:
    """Mock client for testing without API keys."""
    
    async def chat_completions_create(self, **kwargs):
        """Mock chat completion."""
        class MockResponse:
            class Choice:
                class Message:
                    content = '{"result": "mock_response", "confidence": 0.5}'
                message = Message()
            choices = [Choice()]
        return MockResponse()


# ──────────────────────────── Knowledge Base ────────────────────────────


class KnowledgeBase:
    """
    Domain-specific knowledge base for the agent.
    
    Inspired by NVIDIA AVO's knowledge base containing:
    - Programming guides
    - Architecture specifications
    - Existing implementations
    - Best practices
    """
    
    def __init__(self, kb_dir: str = None):
        self.kb_dir = kb_dir or os.path.join(os.getcwd(), "knowledge")
        self._entries: dict[str, Any] = {}
        self._index: dict[str, list[str]] = {}  # keyword -> entry_ids
        self._load()
    
    def _load(self):
        """Load knowledge base from disk."""
        if not os.path.exists(self.kb_dir):
            os.makedirs(self.kb_dir, exist_ok=True)
            self._create_default_entries()
        
        for filename in os.listdir(self.kb_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.kb_dir, filename)
                with open(filepath) as f:
                    entry = json.load(f)
                    self._entries[entry["id"]] = entry
                    # Index keywords
                    for keyword in entry.get("keywords", []):
                        keyword_lower = keyword.lower()
                        if keyword_lower not in self._index:
                            self._index[keyword_lower] = []
                        self._index[keyword_lower].append(entry["id"])
    
    def _create_default_entries(self):
        """Create default knowledge base entries."""
        entries = [
            {
                "id": "planning_best_practices",
                "title": "Planning Best Practices",
                "content": "Break complex goals into sub-goals. Use DAG for dependencies. Estimate time and cost. Identify risks.",
                "keywords": ["planning", "strategy", "goals", "decomposition"],
                "category": "methodology",
            },
            {
                "id": "safety_invariants",
                "title": "Safety Invariants",
                "content": "R0-R6 risk classification. Never fabricate evidence. Never bypass approval gates. Never allow value drift.",
                "keywords": ["safety", "risk", "invariants", "governance"],
                "category": "safety",
            },
            {
                "id": "multi_agent_patterns",
                "title": "Multi-Agent Patterns",
                "content": "Pipeline, Debate, Divide-and-Conquer, Assembly Line, Consensus, Dynamic topologies.",
                "keywords": ["agents", "swarm", "multi-agent", "orchestration"],
                "category": "architecture",
            },
            {
                "id": "plugin_development",
                "title": "Plugin Development",
                "content": "All capabilities are plugins. Use PluginBase. Define PLUGIN_METADATA. Implement lifecycle methods.",
                "keywords": ["plugins", "development", "extension"],
                "category": "development",
            },
            {
                "id": "workflow_patterns",
                "title": "Workflow Patterns",
                "content": "DAG execution. Circuit breaker. Retry with backoff. Timeout handling. Fallback chains.",
                "keywords": ["workflow", "dag", "execution", "retry"],
                "category": "architecture",
            },
        ]
        
        for entry in entries:
            filepath = os.path.join(self.kb_dir, f"{entry['id']}.json")
            with open(filepath, "w") as f:
                json.dump(entry, f, indent=2)
    
    def search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        """Search knowledge base by keywords."""
        query_lower = query.lower()
        results = []
        
        # Direct keyword match
        for keyword, entry_ids in self._index.items():
            if keyword in query_lower:
                for entry_id in entry_ids:
                    entry = self._entries.get(entry_id)
                    if entry and entry not in results:
                        results.append(entry)
        
        # Title match
        for entry in self._entries.values():
            if query_lower in entry.get("title", "").lower() and entry not in results:
                results.append(entry)
        
        return results[:max_results]
    
    def get(self, entry_id: str) -> dict[str, Any] | None:
        """Get a knowledge base entry by ID."""
        return self._entries.get(entry_id)
    
    def add(self, entry: dict[str, Any]):
        """Add a knowledge base entry."""
        self._entries[entry["id"]] = entry
        for keyword in entry.get("keywords", []):
            keyword_lower = keyword.lower()
            if keyword_lower not in self._index:
                self._index[keyword_lower] = []
            self._index[keyword_lower].append(entry["id"])


# ──────────────────────────── Evaluation Utility ────────────────────────────


class EvaluationUtility:
    """
    Feedback-driven evaluation utility.
    
    Inspired by NVIDIA AVO's evaluation utility that provides
    continuous feedback to guide the agent's search.
    """
    
    def __init__(self):
        self._metrics: dict[str, list[float]] = {}
        self._history: list[dict[str, Any]] = []
    
    def evaluate(self, task_id: str, output: Any, expected: Any = None) -> dict[str, Any]:
        """Evaluate an output against expected criteria."""
        result = {
            "task_id": task_id,
            "timestamp": time.time(),
            "score": 0.0,
            "metrics": {},
            "feedback": "",
        }
        
        # Basic quality metrics
        if isinstance(output, str):
            result["metrics"]["length"] = len(output)
            result["metrics"]["has_structure"] = "```" in output or "#" in output
            result["metrics"]["has_code"] = "def " in output or "class " in output
            result["score"] = self._score_text_output(output, expected)
        elif isinstance(output, dict):
            result["metrics"]["has_result"] = "result" in output or "status" in output
            result["metrics"]["has_data"] = len(output) > 0
            result["score"] = self._score_structured_output(output, expected)
        elif isinstance(output, (list, tuple)):
            result["metrics"]["count"] = len(output)
            result["score"] = min(len(output) / 10.0, 1.0) if expected is None else 0.8
        
        # Track metrics
        if task_id not in self._metrics:
            self._metrics[task_id] = []
        self._metrics[task_id].append(result["score"])
        
        # Generate feedback
        result["feedback"] = self._generate_feedback(result)
        
        self._history.append(result)
        return result
    
    def _score_text_output(self, output: str, expected: Any = None) -> float:
        """Score a text output."""
        score = 0.0
        
        # Length check (not too short, not too long)
        if 50 <= len(output) <= 10000:
            score += 0.3
        
        # Structure check
        if any(marker in output for marker in ["```", "#", "- ", "1. "]):
            score += 0.3
        
        # Content check
        if any(word in output.lower() for word in ["because", "therefore", "reason", "analysis"]):
            score += 0.2
        
        # Expected match
        if expected and str(expected).lower() in output.lower():
            score += 0.2
        
        return min(score, 1.0)
    
    def _score_structured_output(self, output: dict, expected: Any = None) -> float:
        """Score a structured output."""
        score = 0.0
        
        if "status" in output:
            score += 0.3
        if "result" in output:
            score += 0.3
        if len(output) > 1:
            score += 0.2
        
        return min(score, 1.0)
    
    def _generate_feedback(self, result: dict[str, Any]) -> str:
        """Generate feedback from evaluation."""
        score = result["score"]
        if score >= 0.8:
            return "Excellent quality output"
        elif score >= 0.6:
            return "Good quality, minor improvements possible"
        elif score >= 0.4:
            return "Acceptable, needs improvement"
        else:
            return "Poor quality, significant revision needed"
    
    def get_average_score(self, task_id: str = None) -> float:
        """Get average score for a task or all tasks."""
        if task_id:
            scores = self._metrics.get(task_id, [])
            return sum(scores) / len(scores) if scores else 0.0
        
        all_scores = [s for scores in self._metrics.values() for s in scores]
        return sum(all_scores) / len(all_scores) if all_scores else 0.0
    
    def get_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get evaluation history."""
        return self._history[-limit:]


# ──────────────────────────── Real Planner ────────────────────────────


class RealPlanner:
    """
    LLM-powered planning engine with real reasoning.
    
    Uses actual LLM calls for the THINK phase,
    and semantic search for feature identification.
    """
    
    def __init__(self, llm_client: LLMClient = None, knowledge_base: KnowledgeBase = None):
        self.llm = llm_client or LLMClient()
        self.kb = knowledge_base or KnowledgeBase()
        self.evaluator = EvaluationUtility()
    
    async def think_and_plan(self, goal: str, context: dict = None) -> dict[str, Any]:
        """Think and plan using real LLM reasoning."""
        # Phase 1: THINK with LLM
        thoughts = await self._think(goal, context)
        
        # Phase 2: PLAN with LLM
        plan = await self._plan(goal, thoughts)
        
        # Phase 3: EVALUATE
        evaluation = self.evaluator.evaluate(
            task_id=plan.get("plan_id", "unknown"),
            output=plan,
        )
        
        return {
            "plan_id": plan.get("plan_id"),
            "goal": goal,
            "thoughts": thoughts,
            "plan": plan,
            "evaluation": evaluation,
            "knowledge_used": self.kb.search(goal),
        }
    
    async def _think(self, goal: str, context: dict = None) -> list[dict[str, Any]]:
        """Generate real thoughts using LLM."""
        # Get relevant knowledge
        relevant_kb = self.kb.search(goal)
        kb_context = "\n".join([f"- {e['title']}: {e['content']}" for e in relevant_kb])
        
        messages = [
            {
                "role": "system",
                "content": f"""You are an expert planning AI. Analyze the given goal and generate structured thinking.
                
Relevant knowledge base:
{kb_context}

Think step by step:
1. Decompose the goal into sub-goals
2. Identify required capabilities and tools
3. Evaluate possible approaches
4. Identify risks and mitigations
5. Estimate resources needed

Respond in JSON format with:
- sub_goals: list of strings
- capabilities_needed: list of strings
- approaches: list of strings with pros/cons
- risks: list of strings with mitigations
- resource_estimate: dict with time, cost, complexity""",
            },
            {
                "role": "user",
                "content": f"Goal: {goal}\nContext: {context or {}}",
            },
        ]
        
        try:
            response = await self.llm.chat_json(messages)
            return [
                {
                    "type": "decomposition",
                    "content": response.get("sub_goals", []),
                    "confidence": 0.85,
                },
                {
                    "type": "capabilities",
                    "content": response.get("capabilities_needed", []),
                    "confidence": 0.8,
                },
                {
                    "type": "approaches",
                    "content": response.get("approaches", []),
                    "confidence": 0.75,
                },
                {
                    "type": "risks",
                    "content": response.get("risks", []),
                    "confidence": 0.7,
                },
                {
                    "type": "resources",
                    "content": response.get("resource_estimate", {}),
                    "confidence": 0.7,
                },
            ]
        except Exception as e:
            logger.error(f"Think phase failed: {e}")
            return self._fallback_thoughts(goal)
    
    async def _plan(self, goal: str, thoughts: list[dict]) -> dict[str, Any]:
        """Generate execution plan using LLM."""
        plan_id = str(uuid.uuid4())[:8]
        
        messages = [
            {
                "role": "system",
                "content": """You are an expert planning AI. Create a detailed execution plan based on the thinking analysis.

Respond in JSON format with:
- steps: list of steps, each with: id, name, description, dependencies, action, priority
- parallel_groups: list of step groups that can run in parallel
- critical_path: list of step IDs on the critical path
- estimated_total_time: number in seconds
- estimated_total_cost: number in USD""",
            },
            {
                "role": "user",
                "content": f"Goal: {goal}\nThinking: {json.dumps(thoughts, indent=2)}",
            },
        ]
        
        try:
            response = await self.llm.chat_json(messages)
            response["plan_id"] = plan_id
            return response
        except Exception as e:
            logger.error(f"Plan phase failed: {e}")
            return self._fallback_plan(goal, plan_id)
    
    def _fallback_thoughts(self, goal: str) -> list[dict[str, Any]]:
        """Generate fallback thoughts when LLM is unavailable."""
        return [
            {"type": "decomposition", "content": [f"Analyze: {goal}", "Execute", "Verify"], "confidence": 0.5},
            {"type": "capabilities", "content": ["planning", "execution"], "confidence": 0.5},
            {"type": "approaches", "content": ["Direct execution", "Iterative refinement"], "confidence": 0.5},
            {"type": "risks", "content": ["Unknown dependencies"], "confidence": 0.3},
            {"type": "resources", "content": {"time": 60, "cost": 0.01}, "confidence": 0.3},
        ]
    
    def _fallback_plan(self, goal: str, plan_id: str) -> dict[str, Any]:
        """Generate fallback plan when LLM is unavailable."""
        return {
            "plan_id": plan_id,
            "steps": [
                {"id": "s1", "name": "analyze", "description": f"Analyze {goal}", "dependencies": [], "action": "analyze", "priority": "high"},
                {"id": "s2", "name": "execute", "description": f"Execute {goal}", "dependencies": ["s1"], "action": "execute", "priority": "high"},
                {"id": "s3", "name": "verify", "description": "Verify results", "dependencies": ["s2"], "action": "verify", "priority": "medium"},
            ],
            "parallel_groups": [],
            "critical_path": ["s1", "s2", "s3"],
            "estimated_total_time": 60.0,
            "estimated_total_cost": 0.01,
        }
