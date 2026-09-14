"""AI/ML Knowledge Graph Schema Definition.

Defines the 16 verticals, node types, edge types, and validation rules
for the AI/ML Knowledge Graph.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

import networkx as nx
from pydantic import BaseModel, Field


class Vertical(str, Enum):
    """The 16 AI/ML Knowledge Graph verticals."""

    ML_ALGORITHMS = "ml_algorithms"
    DEEP_LEARNING = "deep_learning"
    NLP = "nlp"
    COMPUTER_VISION = "computer_vision"
    REINFORCEMENT_LEARNING = "reinforcement_learning"
    DATA_ENGINEERING = "data_engineering"
    MLOPS = "mlops"
    AI_ETHICS = "ai_ethics"
    KNOWLEDGE_REPRESENTATION = "knowledge_representation"
    NEURAL_FOUNDATIONS = "neural_foundations"
    GENERATIVE_AI = "generative_ai"
    ROBOTICS = "robotics"
    AI_SAFETY = "ai_safety"
    OPTIMIZATION = "optimization"
    PROBABILISTIC_METHODS = "probabilistic_methods"
    MULTI_AGENT_SYSTEMS = "multi_agent_systems"


class NodeType(str, Enum):
    """Types of nodes in the knowledge graph."""

    CONCEPT = "concept"
    ALGORITHM = "algorithm"
    FRAMEWORK = "framework"
    PAPER = "paper"
    DATASET = "dataset"
    METRIC = "metric"
    TASK = "task"
    ARCHITECTURE = "architecture"
    TECHNIQUE = "technique"
    PROTOCOL = "protocol"


class EdgeType(str, Enum):
    """Types of edges connecting nodes."""

    DEPENDS_ON = "depends_on"
    EXTENDS = "extends"
    IMPLEMENTS = "implements"
    EVALUATED_BY = "evaluated_by"
    APPLIED_TO = "applied_to"
    DERIVED_FROM = "derived_from"
    COMPETES_WITH = "competes_with"
    COMPLEMENTS = "complements"
    VERSION_OF = "version_of"
    PROTOCOL_FOR = "protocol_for"


# Vertical metadata: name, description, key concepts
VERTICAL_METADATA: dict[Vertical, dict[str, Any]] = {
    Vertical.ML_ALGORITHMS: {
        "name": "Machine Learning Algorithms",
        "description": "Core supervised, unsupervised, and semi-supervised learning algorithms",
        "key_concepts": [
            "linear_regression", "logistic_regression", "decision_tree",
            "random_forest", "svm", "knn", "naive_bayes", "kmeans",
            "dbscan", "pca", "gradient_boosting", "xgboost",
        ],
    },
    Vertical.DEEP_LEARNING: {
        "name": "Deep Learning Architectures",
        "description": "Neural network architectures for complex pattern recognition",
        "key_concepts": [
            "mlp", "cnn", "rnn", "lstm", "gru", "autoencoder",
            "gan", "diffusion_model", "resnet", "inception", "yolo",
        ],
    },
    Vertical.NLP: {
        "name": "Natural Language Processing",
        "description": "Techniques for understanding and generating human language",
        "key_concepts": [
            "tokenization", "word_embedding", "attention", "transformer",
            "bert", "gpt", "t5", "sentiment_analysis", "ner",
            "machine_translation", "summarization", "question_answering",
        ],
    },
    Vertical.COMPUTER_VISION: {
        "name": "Computer Vision",
        "description": "Visual understanding and image processing techniques",
        "key_concepts": [
            "image_classification", "object_detection", "segmentation",
            "pose_estimation", "optical_flow", "feature_extraction",
            "convolution", "pooling", "data_augmentation",
        ],
    },
    Vertical.REINFORCEMENT_LEARNING: {
        "name": "Reinforcement Learning",
        "description": "Learning through interaction with environments via rewards",
        "key_concepts": [
            "q_learning", "policy_gradient", "actor_critic", "ppo",
            "sarsa", "markov_decision_process", "exploration_exploitation",
            "reward_shaping", "multi_agent_rl",
        ],
    },
    Vertical.DATA_ENGINEERING: {
        "name": "Data Engineering for AI/ML",
        "description": "Data pipelines, feature stores, and data quality for ML systems",
        "key_concepts": [
            "etl", "feature_store", "data_validation", "data_versioning",
            "streaming", "batch_processing", "data_lake", "schema_evolution",
        ],
    },
    Vertical.MLOPS: {
        "name": "MLOps & Model Deployment",
        "description": "Operationalizing ML models in production environments",
        "key_concepts": [
            "model_serving", "a_b_testing", "canary_deployment",
            "model_monitoring", "drift_detection", "feature_importance",
            "model_registry", "pipeline_orchestration",
        ],
    },
    Vertical.AI_ETHICS: {
        "name": "AI Ethics & Governance",
        "description": "Fairness, accountability, transparency, and regulation of AI systems",
        "key_concepts": [
            "fairness", "bias_detection", "explainability", "accountability",
            "privacy", "gdpr", "model_cards", "impact_assessment",
        ],
    },
    Vertical.KNOWLEDGE_REPRESENTATION: {
        "name": "Knowledge Representation",
        "description": "Formalisms for representing knowledge: ontologies, graphs, logic",
        "key_concepts": [
            "ontology", "semantic_web", "rdf", "owl", "description_logic",
            "knowledge_graph", "entity_linking", "reasoning",
        ],
    },
    Vertical.NEURAL_FOUNDATIONS: {
        "name": "Neural Network Foundations",
        "description": "Mathematical and computational foundations of neural networks",
        "key_concepts": [
            "backpropagation", "gradient_descent", "activation_function",
            "loss_function", "regularization", "batch_normalization",
            "dropout", "weight_initialization",
        ],
    },
    Vertical.GENERATIVE_AI: {
        "name": "Generative AI & Large Language Models",
        "description": "Models that generate text, code, images, and other content",
        "key_concepts": [
            "llm", "prompt_engineering", "fine_tuning", "rlhf",
            "instruction_tuning", "chain_of_thought", "rag",
            "diffusion", "vae", "autoregressive",
        ],
    },
    Vertical.ROBOTICS: {
        "name": "Robotics & Embodied AI",
        "description": "AI systems that interact with the physical world",
        "key_concepts": [
            "slam", "path_planning", "manipulation", "control_theory",
            "sensor_fusion", "kinematics", "reinforcement_learning_robotic",
        ],
    },
    Vertical.AI_SAFETY: {
        "name": "AI Safety & Alignment",
        "description": "Ensuring AI systems behave safely and align with human values",
        "key_concepts": [
            "alignment", "reward_hacking", "interpretability",
            "mechanistic_interpretability", "scalable_oversight",
            "constitutional_ai", "red_teaming",
        ],
    },
    Vertical.OPTIMIZATION: {
        "name": "Optimization & Search",
        "description": "Mathematical optimization techniques for AI/ML",
        "key_concepts": [
            "convex_optimization", "genetic_algorithm", "simulated_annealing",
            "bayesian_optimization", "hyperparameter_tuning",
            "evolutionary_strategy", "swarm_intelligence",
        ],
    },
    Vertical.PROBABILISTIC_METHODS: {
        "name": "Probabilistic Methods & Bayesian Inference",
        "description": "Probabilistic approaches to reasoning under uncertainty",
        "key_concepts": [
            "bayesian_network", "markov_chain", "mcmc",
            "variational_inference", "gaussian_process",
            "hidden_markov_model", "probabilistic_graphical_model",
        ],
    },
    Vertical.MULTI_AGENT_SYSTEMS: {
        "name": "Multi-Agent Systems & Coordination",
        "description": "Systems where multiple AI agents interact and coordinate",
        "key_concepts": [
            "agent_coordination", "negotiation", "auction",
            "swarm_intelligence", "communication_protocol",
            "task_allocation", "consensus", "game_theory",
        ],
    },
}


class KGNode(BaseModel):
    """A node in the AI/ML Knowledge Graph."""

    id: str = Field(..., min_length=1, description="Unique node identifier")
    label: str = Field(..., min_length=1, description="Human-readable label")
    node_type: NodeType = Field(..., description="Type of node")
    vertical: Vertical = Field(..., description="Vertical this node belongs to")
    description: str = Field(default="", description="Detailed description")
    properties: dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata")
    version: str = Field(default="1.0.0", description="Schema version of this node")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for graph serialization."""
        d = self.model_dump()
        d["node_type"] = self.node_type.value
        d["vertical"] = self.vertical.value
        return d


class KGEdge(BaseModel):
    """An edge connecting two nodes in the AI/ML Knowledge Graph."""

    source: str = Field(..., description="Source node id")
    target: str = Field(..., description="Target node id")
    edge_type: EdgeType = Field(..., description="Type of relationship")
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="Edge weight 0-1")
    properties: dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for graph serialization."""
        d = self.model_dump()
        d["edge_type"] = self.edge_type.value
        return d


def create_empty_graph() -> nx.DiGraph:
    """Create an empty AI/ML Knowledge Graph with metadata."""
    g = nx.DiGraph()
    g.graph["name"] = "AI/ML Knowledge Graph"
    g.graph["version"] = "1.0.0"
    g.graph["verticals"] = [v.value for v in Vertical]
    g.graph["node_types"] = [nt.value for nt in NodeType]
    g.graph["edge_types"] = [et.value for et in EdgeType]
    return g


def validate_node(node: KGNode) -> list[str]:
    """Validate a node against the schema. Returns list of errors."""
    errors: list[str] = []
    if not node.id:
        errors.append("Node id cannot be empty")
    if not node.label:
        errors.append("Node label cannot be empty")
    if not node.id.replace("_", "").replace("-", "").isalnum():
        errors.append(f"Node id '{node.id}' must be alphanumeric with underscores/hyphens only")
    return errors


def validate_edge(edge: KGEdge, graph: nx.DiGraph) -> list[str]:
    """Validate an edge against the schema and graph state. Returns list of errors."""
    errors: list[str] = []
    if edge.source not in graph.nodes:
        errors.append(f"Source node '{edge.source}' does not exist in graph")
    if edge.target not in graph.nodes:
        errors.append(f"Target node '{edge.target}' does not exist in graph")
    if edge.source == edge.target:
        errors.append("Self-loops are not allowed")
    if not 0.0 <= edge.weight <= 1.0:
        errors.append(f"Edge weight {edge.weight} must be between 0 and 1")
    return errors


def add_node_to_graph(graph: nx.DiGraph, node: KGNode) -> list[str]:
    """Add a node to the graph after validation. Returns errors if any."""
    errors = validate_node(node)
    if errors:
        return errors
    if node.id in graph.nodes:
        return [f"Node '{node.id}' already exists"]
    graph.add_node(node.id, **node.to_dict())
    return []


def add_edge_to_graph(graph: nx.DiGraph, edge: KGEdge) -> list[str]:
    """Add an edge to the graph after validation. Returns errors if any."""
    errors = validate_edge(edge, graph)
    if errors:
        return errors
    graph.add_edge(edge.source, edge.target, **edge.to_dict())
    return []


def get_vertical_summary(graph: nx.DiGraph) -> dict[str, int]:
    """Return count of nodes per vertical."""
    summary: dict[str, int] = {v.value: 0 for v in Vertical}
    for _, data in graph.nodes(data=True):
        v = data.get("vertical")
        if v in summary:
            summary[v] += 1
    return summary
