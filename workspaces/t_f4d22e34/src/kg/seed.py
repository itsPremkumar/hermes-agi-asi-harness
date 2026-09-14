"""Data loader: seed the KG with initial nodes and edges for all 16 verticals."""

from __future__ import annotations

from kg import (
    KGNode,
    KGEdge,
    Vertical,
    NodeType,
    EdgeType,
    add_node_to_graph,
    add_edge_to_graph,
    nx,
)


def seed_graph(graph: nx.DiGraph) -> list[str]:
    """Seed the graph with initial nodes and edges across all 16 verticals."""
    errors: list[str] = []

    # --- ML Algorithms ---
    ml_nodes = [
        KGNode(id="linear_regression", label="Linear Regression", node_type=NodeType.ALGORITHM, vertical=Vertical.ML_ALGORITHMS, description="Simple linear model for regression tasks"),
        KGNode(id="logistic_regression", label="Logistic Regression", node_type=NodeType.ALGORITHM, vertical=Vertical.ML_ALGORITHMS, description="Classification algorithm using sigmoid function"),
        KGNode(id="decision_tree", label="Decision Tree", node_type=NodeType.ALGORITHM, vertical=Vertical.ML_ALGORITHMS, description="Tree-based classification/regression"),
        KGNode(id="random_forest", label="Random Forest", node_type=NodeType.ALGORITHM, vertical=Vertical.ML_ALGORITHMS, description="Ensemble of decision trees"),
        KGNode(id="svm", label="Support Vector Machine", node_type=NodeType.ALGORITHM, vertical=Vertical.ML_ALGORITHMS, description="Maximum margin classifier"),
        KGNode(id="knn", label="K-Nearest Neighbors", node_type=NodeType.ALGORITHM, vertical=Vertical.ML_ALGORITHMS, description="Instance-based learning"),
        KGNode(id="gradient_boosting", label="Gradient Boosting", node_type=NodeType.ALGORITHM, vertical=Vertical.ML_ALGORITHMS, description="Sequential ensemble of weak learners"),
        KGNode(id="pca", label="Principal Component Analysis", node_type=NodeType.TECHNIQUE, vertical=Vertical.ML_ALGORITHMS, description="Dimensionality reduction via eigendecomposition"),
        KGNode(id="kmeans", label="K-Means Clustering", node_type=NodeType.ALGORITHM, vertical=Vertical.ML_ALGORITHMS, description="Unsupervised clustering algorithm"),
    ]
    for n in ml_nodes:
        errs = add_node_to_graph(graph, n)
        errors.extend(errs)

    # --- Deep Learning ---
    dl_nodes = [
        KGNode(id="mlp", label="Multi-Layer Perceptron", node_type=NodeType.ARCHITECTURE, vertical=Vertical.DEEP_LEARNING, description="Fully connected feedforward neural network"),
        KGNode(id="cnn", label="Convolutional Neural Network", node_type=NodeType.ARCHITECTURE, vertical=Vertical.DEEP_LEARNING, description="Neural network with convolutional layers for spatial data"),
        KGNode(id="rnn", label="Recurrent Neural Network", node_type=NodeType.ARCHITECTURE, vertical=Vertical.DEEP_LEARNING, description="Neural network for sequential data"),
        KGNode(id="lstm", label="Long Short-Term Memory", node_type=NodeType.ARCHITECTURE, vertical=Vertical.DEEP_LEARNING, description="RNN variant with gating mechanisms"),
        KGNode(id="transformer", label="Transformer", node_type=NodeType.ARCHITECTURE, vertical=Vertical.DEEP_LEARNING, description="Attention-based neural architecture"),
        KGNode(id="gan", label="Generative Adversarial Network", node_type=NodeType.ARCHITECTURE, vertical=Vertical.DEEP_LEARNING, description="Generator-discriminator framework for generative modeling"),
        KGNode(id="resnet", label="Residual Network", node_type=NodeType.ARCHITECTURE, vertical=Vertical.DEEP_LEARNING, description="Deep network with skip connections"),
    ]
    for n in dl_nodes:
        errs = add_node_to_graph(graph, n)
        errors.extend(errs)

    # --- NLP ---
    nlp_nodes = [
        KGNode(id="tokenization", label="Tokenization", node_type=NodeType.TECHNIQUE, vertical=Vertical.NLP, description="Text segmentation into tokens"),
        KGNode(id="word_embedding", label="Word Embeddings", node_type=NodeType.TECHNIQUE, vertical=Vertical.NLP, description="Dense vector representations of words"),
        KGNode(id="attention_mechanism", label="Attention Mechanism", node_type=NodeType.TECHNIQUE, vertical=Vertical.NLP, description="Weighted context aggregation mechanism"),
        KGNode(id="bert", label="BERT", node_type=NodeType.ARCHITECTURE, vertical=Vertical.NLP, description="Bidirectional encoder representations from transformers"),
        KGNode(id="gpt", label="GPT", node_type=NodeType.ARCHITECTURE, vertical=Vertical.NLP, description="Generative pre-trained transformer"),
        KGNode(id="t5", label="T5", node_type=NodeType.ARCHITECTURE, vertical=Vertical.NLP, description="Text-to-text transfer transformer"),
    ]
    for n in nlp_nodes:
        errs = add_node_to_graph(graph, n)
        errors.extend(errs)

    # --- Computer Vision ---
    cv_nodes = [
        KGNode(id="image_classification", label="Image Classification", node_type=NodeType.TASK, vertical=Vertical.COMPUTER_VISION, description="Assigning labels to images"),
        KGNode(id="object_detection", label="Object Detection", node_type=NodeType.TASK, vertical=Vertical.COMPUTER_VISION, description="Locating and classifying objects in images"),
        KGNode(id="segmentation", label="Image Segmentation", node_type=NodeType.TASK, vertical=Vertical.COMPUTER_VISION, description="Pixel-level classification of images"),
        KGNode(id="yolo", label="YOLO", node_type=NodeType.ARCHITECTURE, vertical=Vertical.COMPUTER_VISION, description="Real-time object detection architecture"),
        KGNode(id="optical_flow", label="Optical Flow", node_type=NodeType.TECHNIQUE, vertical=Vertical.COMPUTER_VISION, description="Motion estimation between frames"),
    ]
    for n in cv_nodes:
        errs = add_node_to_graph(graph, n)
        errors.extend(errs)

    # --- Reinforcement Learning ---
    rl_nodes = [
        KGNode(id="q_learning", label="Q-Learning", node_type=NodeType.ALGORITHM, vertical=Vertical.REINFORCEMENT_LEARNING, description="Value-based RL algorithm"),
        KGNode(id="policy_gradient", label="Policy Gradient", node_type=NodeType.ALGORITHM, vertical=Vertical.REINFORCEMENT_LEARNING, description="Direct policy optimization"),
        KGNode(id="ppo", label="Proximal Policy Optimization", node_type=NodeType.ALGORITHM, vertical=Vertical.REINFORCEMENT_LEARNING, description="Stable policy gradient method"),
        KGNode(id="markov_decision_process", label="Markov Decision Process", node_type=NodeType.CONCEPT, vertical=Vertical.REINFORCEMENT_LEARNING, description="Mathematical framework for sequential decision making"),
        KGNode(id="actor_critic", label="Actor-Critic", node_type=NodeType.ALGORITHM, vertical=Vertical.REINFORCEMENT_LEARNING, description="Combined value and policy optimization"),
    ]
    for n in rl_nodes:
        errs = add_node_to_graph(graph, n)
        errors.extend(errs)

    # --- Data Engineering ---
    de_nodes = [
        KGNode(id="etl_pipeline", label="ETL Pipeline", node_type=NodeType.TECHNIQUE, vertical=Vertical.DATA_ENGINEERING, description="Extract-Transform-Load data pipeline"),
        KGNode(id="feature_store", label="Feature Store", node_type=NodeType.FRAMEWORK, vertical=Vertical.DATA_ENGINEERING, description="Centralized feature management system"),
        KGNode(id="data_validation", label="Data Validation", node_type=NodeType.TECHNIQUE, vertical=Vertical.DATA_ENGINEERING, description="Schema and quality checks for data"),
        KGNode(id="streaming_ingest", label="Streaming Ingestion", node_type=NodeType.TECHNIQUE, vertical=Vertical.DATA_ENGINEERING, description="Real-time data ingestion from streams"),
        KGNode(id="data_versioning", label="Data Versioning", node_type=NodeType.TECHNIQUE, vertical=Vertical.DATA_ENGINEERING, description="Version control for datasets"),
    ]
    for n in de_nodes:
        errs = add_node_to_graph(graph, n)
        errors.extend(errs)

    # --- MLOps ---
    mlops_nodes = [
        KGNode(id="model_serving", label="Model Serving", node_type=NodeType.TECHNIQUE, vertical=Vertical.MLOPS, description="Deploying models for inference"),
        KGNode(id="model_monitoring", label="Model Monitoring", node_type=NodeType.TECHNIQUE, vertical=Vertical.MLOPS, description="Tracking model performance in production"),
        KGNode(id="drift_detection", label="Drift Detection", node_type=NodeType.TECHNIQUE, vertical=Vertical.MLOPS, description="Detecting distribution shift in data/model"),
        KGNode(id="model_registry", label="Model Registry", node_type=NodeType.FRAMEWORK, vertical=Vertical.MLOPS, description="Centralized model artifact management"),
        KGNode(id="pipeline_orchestration", label="Pipeline Orchestration", node_type=NodeType.TECHNIQUE, vertical=Vertical.MLOPS, description="Coordinating multi-step ML pipelines"),
    ]
    for n in mlops_nodes:
        errs = add_node_to_graph(graph, n)
        errors.extend(errs)

    # --- AI Ethics ---
    ethics_nodes = [
        KGNode(id="fairness_metrics", label="Fairness Metrics", node_type=NodeType.METRIC, vertical=Vertical.AI_ETHICS, description="Quantifying algorithmic fairness"),
        KGNode(id="bias_detection", label="Bias Detection", node_type=NodeType.TECHNIQUE, vertical=Vertical.AI_ETHICS, description="Identifying systematic biases in models"),
        KGNode(id="explainability", label="Explainability", node_type=NodeType.CONCEPT, vertical=Vertical.AI_ETHICS, description="Making model decisions interpretable"),
        KGNode(id="model_cards", label="Model Cards", node_type=NodeType.TECHNIQUE, vertical=Vertical.AI_ETHICS, description="Documentation for model behavior and limitations"),
        KGNode(id="gdpr_ai", label="GDPR & AI Compliance", node_type=NodeType.CONCEPT, vertical=Vertical.AI_ETHICS, description="Regulatory compliance for AI systems"),
    ]
    for n in ethics_nodes:
        errs = add_node_to_graph(graph, n)
        errors.extend(errs)

    # --- Knowledge Representation ---
    kr_nodes = [
        KGNode(id="semantic_web", label="Semantic Web", node_type=NodeType.CONCEPT, vertical=Vertical.KNOWLEDGE_REPRESENTATION, description="Web of linked data"),
        KGNode(id="rdf", label="RDF", node_type=NodeType.TECHNIQUE, vertical=Vertical.KNOWLEDGE_REPRESENTATION, description="Resource Description Framework"),
        KGNode(id="ontology_engineering", label="Ontology Engineering", node_type=NodeType.TECHNIQUE, vertical=Vertical.KNOWLEDGE_REPRESENTATION, description="Building formal domain ontologies"),
        KGNode(id="description_logic", label="Description Logic", node_type=NodeType.CONCEPT, vertical=Vertical.KNOWLEDGE_REPRESENTATION, description="Formal logic for knowledge representation"),
        KGNode(id="entity_linking", label="Entity Linking", node_type=NodeType.TECHNIQUE, vertical=Vertical.KNOWLEDGE_REPRESENTATION, description="Linking mentions to knowledge base entities"),
    ]
    for n in kr_nodes:
        errs = add_node_to_graph(graph, n)
        errors.extend(errs)

    # --- Neural Foundations ---
    nf_nodes = [
        KGNode(id="backpropagation", label="Backpropagation", node_type=NodeType.TECHNIQUE, vertical=Vertical.NEURAL_FOUNDATIONS, description="Gradient computation via chain rule"),
        KGNode(id="gradient_descent", label="Gradient Descent", node_type=NodeType.ALGORITHM, vertical=Vertical.NEURAL_FOUNDATIONS, description="Iterative optimization algorithm"),
        KGNode(id="activation_functions", label="Activation Functions", node_type=NodeType.CONCEPT, vertical=Vertical.NEURAL_FOUNDATIONS, description="Non-linear functions in neural networks"),
        KGNode(id="batch_normalization", label="Batch Normalization", node_type=NodeType.TECHNIQUE, vertical=Vertical.NEURAL_FOUNDATIONS, description="Normalizing layer inputs for training stability"),
        KGNode(id="dropout_regularization", label="Dropout Regularization", node_type=NodeType.TECHNIQUE, vertical=Vertical.NEURAL_FOUNDATIONS, description="Random unit dropping for regularization"),
    ]
    for n in nf_nodes:
        errs = add_node_to_graph(graph, n)
        errors.extend(errs)

    # --- Generative AI ---
    gen_nodes = [
        KGNode(id="llm", label="Large Language Model", node_type=NodeType.ARCHITECTURE, vertical=Vertical.GENERATIVE_AI, description="Massive transformer language models"),
        KGNode(id="prompt_engineering", label="Prompt Engineering", node_type=NodeType.TECHNIQUE, vertical=Vertical.GENERATIVE_AI, description="Crafting effective prompts for LLMs"),
        KGNode(id="rlhf", label="Reinforcement Learning from Human Feedback", node_type=NodeType.TECHNIQUE, vertical=Vertical.GENERATIVE_AI, description="Aligning models with human preferences"),
        KGNode(id="rag", label="Retrieval-Augmented Generation", node_type=NodeType.TECHNIQUE, vertical=Vertical.GENERATIVE_AI, description="Combining retrieval with generation"),
        KGNode(id="diffusion_models", label="Diffusion Models", node_type=NodeType.ARCHITECTURE, vertical=Vertical.GENERATIVE_AI, description="Score-based generative models"),
        KGNode(id="vae", label="Variational Autoencoder", node_type=NodeType.ARCHITECTURE, vertical=Vertical.GENERATIVE_AI, description="Latent variable generative model"),
    ]
    for n in gen_nodes:
        errs = add_node_to_graph(graph, n)
        errors.extend(errs)

    # --- Robotics ---
    robot_nodes = [
        KGNode(id="slam", label="SLAM", node_type=NodeType.TECHNIQUE, vertical=Vertical.ROBOTICS, description="Simultaneous Localization and Mapping"),
        KGNode(id="path_planning", label="Path Planning", node_type=NodeType.TECHNIQUE, vertical=Vertical.ROBOTICS, description="Computing optimal robot trajectories"),
        KGNode(id="robot_manipulation", label="Robot Manipulation", node_type=NodeType.TASK, vertical=Vertical.ROBOTICS, description="Grasping and manipulating objects"),
        KGNode(id="sensor_fusion", label="Sensor Fusion", node_type=NodeType.TECHNIQUE, vertical=Vertical.ROBOTICS, description="Combining multiple sensor streams"),
        KGNode(id="kinematics", label="Robot Kinematics", node_type=NodeType.CONCEPT, vertical=Vertical.ROBOTICS, description="Motion of robotic systems"),
    ]
    for n in robot_nodes:
        errs = add_node_to_graph(graph, n)
        errors.extend(errs)

    # --- AI Safety ---
    safety_nodes = [
        KGNode(id="ai_alignment", label="AI Alignment", node_type=NodeType.CONCEPT, vertical=Vertical.AI_SAFETY, description="Ensuring AI systems pursue intended goals"),
        KGNode(id="interpretability", label="Interpretability", node_type=NodeType.CONCEPT, vertical=Vertical.AI_SAFETY, description="Understanding model internal mechanisms"),
        KGNode(id="reward_hacking", label="Reward Hacking", node_type=NodeType.CONCEPT, vertical=Vertical.AI_SAFETY, description="Agents exploiting reward specification flaws"),
        KGNode(id="constitutional_ai", label="Constitutional AI", node_type=NodeType.TECHNIQUE, vertical=Vertical.AI_SAFETY, description="Training with explicit principles"),
        KGNode(id="red_teaming", label="Red Teaming", node_type=NodeType.TECHNIQUE, vertical=Vertical.AI_SAFETY, description="Adversarial testing of AI systems"),
    ]
    for n in safety_nodes:
        errs = add_node_to_graph(graph, n)
        errors.extend(errs)

    # --- Optimization ---
    opt_nodes = [
        KGNode(id="convex_optimization", label="Convex Optimization", node_type=NodeType.CONCEPT, vertical=Vertical.OPTIMIZATION, description="Optimization over convex functions"),
        KGNode(id="bayesian_optimization", label="Bayesian Optimization", node_type=NodeType.ALGORITHM, vertical=Vertical.OPTIMIZATION, description="Sample-efficient black-box optimization"),
        KGNode(id="genetic_algorithm", label="Genetic Algorithm", node_type=NodeType.ALGORITHM, vertical=Vertical.OPTIMIZATION, description="Evolution-inspired search algorithm"),
        KGNode(id="hyperparameter_tuning", label="Hyperparameter Tuning", node_type=NodeType.TECHNIQUE, vertical=Vertical.OPTIMIZATION, description="Optimizing model hyperparameters"),
        KGNode(id="evolutionary_strategy", label="Evolutionary Strategy", node_type=NodeType.ALGORITHM, vertical=Vertical.OPTIMIZATION, description="Black-box optimization via evolution"),
    ]
    for n in opt_nodes:
        errs = add_node_to_graph(graph, n)
        errors.extend(errs)

    # --- Probabilistic Methods ---
    prob_nodes = [
        KGNode(id="bayesian_network", label="Bayesian Network", node_type=NodeType.CONCEPT, vertical=Vertical.PROBABILISTIC_METHODS, description="Probabilistic graphical model with directed edges"),
        KGNode(id="mcmc", label="MCMC", node_type=NodeType.ALGORITHM, vertical=Vertical.PROBABILISTIC_METHODS, description="Markov Chain Monte Carlo sampling"),
        KGNode(id="variational_inference", label="Variational Inference", node_type=NodeType.TECHNIQUE, vertical=Vertical.PROBABILISTIC_METHODS, description="Approximate Bayesian inference via optimization"),
        KGNode(id="gaussian_process", label="Gaussian Process", node_type=NodeType.CONCEPT, vertical=Vertical.PROBABILISTIC_METHODS, description="Non-parametric Bayesian approach"),
        KGNode(id="hidden_markov_model", label="Hidden Markov Model", node_type=NodeType.CONCEPT, vertical=Vertical.PROBABILISTIC_METHODS, description="State-space probabilistic model"),
    ]
    for n in prob_nodes:
        errs = add_node_to_graph(graph, n)
        errors.extend(errs)

    # --- Multi-Agent Systems ---
    mas_nodes = [
        KGNode(id="agent_coordination", label="Agent Coordination", node_type=NodeType.CONCEPT, vertical=Vertical.MULTI_AGENT_SYSTEMS, description="Orchestrating multiple AI agents"),
        KGNode(id="negotiation_protocol", label="Negotiation Protocol", node_type=NodeType.PROTOCOL, vertical=Vertical.MULTI_AGENT_SYSTEMS, description="Protocols for multi-agent negotiation"),
        KGNode(id="task_allocation", label="Task Allocation", node_type=NodeType.TECHNIQUE, vertical=Vertical.MULTI_AGENT_SYSTEMS, description="Assigning tasks to agents optimally"),
        KGNode(id="consensus_protocol", label="Consensus Protocol", node_type=NodeType.PROTOCOL, vertical=Vertical.MULTI_AGENT_SYSTEMS, description="Achieving agreement among agents"),
        KGNode(id="swarm_intelligence", label="Swarm Intelligence", node_type=NodeType.CONCEPT, vertical=Vertical.MULTI_AGENT_SYSTEMS, description="Collective behavior from decentralized agents"),
    ]
    for n in mas_nodes:
        errs = add_node_to_graph(graph, n)
        errors.extend(errs)

    # --- Cross-vertical edges ---
    cross_edges = [
        KGEdge(source="transformer", target="bert", edge_type=EdgeType.IMPLEMENTS),
        KGEdge(source="transformer", target="gpt", edge_type=EdgeType.IMPLEMENTS),
        KGEdge(source="transformer", target="llm", edge_type=EdgeType.EXTENDS),
        KGEdge(source="attention_mechanism", target="transformer", edge_type=EdgeType.DEPENDS_ON),
        KGEdge(source="backpropagation", target="gradient_descent", edge_type=EdgeType.DEPENDS_ON),
        KGEdge(source="cnn", target="image_classification", edge_type=EdgeType.APPLIED_TO),
        KGEdge(source="cnn", target="object_detection", edge_type=EdgeType.APPLIED_TO),
        KGEdge(source="cnn", target="resnet", edge_type=EdgeType.EXTENDS),
        KGEdge(source="gradient_descent", target="backpropagation", edge_type=EdgeType.PROTOCOL_FOR),
        KGEdge(source="gan", target="diffusion_models", edge_type=EdgeType.COMPETES_WITH),
        KGEdge(source="llm", target="prompt_engineering", edge_type=EdgeType.PROTOCOL_FOR),
        KGEdge(source="llm", target="rlhf", edge_type=EdgeType.DEPENDS_ON),
        KGEdge(source="llm", target="rag", edge_type=EdgeType.COMPLEMENTS),
        KGEdge(source="reinforcement_learning", target="ai_alignment", edge_type=EdgeType.RELATED_TO) if False else KGEdge(source="q_learning", target="markov_decision_process", edge_type=EdgeType.IMPLEMENTS),
        KGEdge(source="fairness_metrics", target="model_cards", edge_type=EdgeType.EVALUATED_BY),
        KGEdge(source="probabilistic_graphical_model", target="bayesian_network", edge_type=EdgeType.IMPLEMENTS) if False else KGEdge(source="bayesian_network", target="mcmc", edge_type=EdgeType.EVALUATED_BY),
        KGEdge(source="agent_coordination", target="negotiation_protocol", edge_type=EdgeType.PROTOCOL_FOR),
        KGEdge(source="agent_coordination", target="task_allocation", edge_type=EdgeType.DEPENDS_ON),
        KGEdge(source="feature_store", target="pipeline_orchestration", edge_type=EdgeType.COMPLEMENTS),
        KGEdge(source="model_serving", target="model_monitoring", edge_type=EdgeType.COMPLEMENTS),
        KGEdge(source="data_validation", target="etl_pipeline", edge_type=EdgeType.DEPENDS_ON),
        KGEdge(source="ontology_engineering", target="entity_linking", edge_type=EdgeType.DEPENDS_ON),
        KGEdge(source="slam", target="sensor_fusion", edge_type=EdgeType.DEPENDS_ON),
        KGEdge(source="path_planning", target="robot_manipulation", edge_type=EdgeType.DEPENDS_ON),
        KGEdge(source="ai_alignment", target="constitutional_ai", edge_type=EdgeType.IMPLEMENTS),
        KGEdge(source="ai_alignment", target="interpretability", edge_type=EdgeType.DEPENDS_ON),
        KGEdge(source="reward_hacking", target="ai_alignment", edge_type=EdgeType.COMPETES_WITH),
        KGEdge(source="hyperparameter_tuning", target="bayesian_optimization", edge_type=EdgeType.IMPLEMENTS),
        KGEdge(source="hidden_markov_model", target="mcmc", edge_type=EdgeType.EVALUATED_BY),
        KGEdge(source="variational_inference", target="gaussian_process", edge_type=EdgeType.COMPLEMENTS),
        KGEdge(source="swarm_intelligence", target="agent_coordination", edge_type=EdgeType.EXTENDS),
    ]
    for e in cross_edges:
        errs = add_edge_to_graph(graph, e)
        errors.extend(errs)

    return errors
