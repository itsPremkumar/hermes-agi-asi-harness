# DeepResearch Engine — Autonomous Scientific Research Agent

A multi-agent pipeline that reads academic papers, synthesizes findings,
identifies gaps, generates novel research hypotheses, designs experiments,
and writes LaTeX research papers — all autonomously.

## Pipeline Architecture

```
Search (ArXiv + PubMed)
   ↓
Read (Summarization + Extraction)
   ↓
Synthesize (Citation Graph + Gap Analysis)
   ↓
Hypothesize (Counterfactual Reasoning)
   ↓
Validate (Experiment Design + Simulation)
   ↓
Write (LaTeX Paper Generation)
   ↓
Evaluate (Quality Assessment)
```

### Agents

| Agent | Module | Description |
|---|---|---|
| **Literature Reviewer** | `deepresearch/agents/literature_reviewer.py` | Searches ArXiv & PubMed, fetches paper metadata, summarizes key findings, builds citation graph |
| **Hypothesis Generator** | `deepresearch/agents/hypothesis_generator.py` | Counterfactual reasoning on literature gaps to produce novel, falsifiable hypotheses |
| **Experiment Designer** | `deepresearch/agents/experiment_designer.py` | Designs simulated/computational/analytical experiments with confidence intervals |
| **Paper Writer** | `deepresearch/agents/paper_writer.py` | Assembles a structured LaTeX paper with citations, bibliography, and all sections |
| **Quality Evaluator** | `deepresearch/evaluation/quality_evaluator.py` | Scores hypotheses (novelty), experiments (feasibility), and drafts (quality) |

### Tools

| Tool | Module | Description |
|---|---|---|
| **ArXiv API** | `deepresearch/tools/arxiv_api.py` | Searches and fetches papers from arXiv |
| **PubMed API** | `deepresearch/tools/pubmed_api.py` | Searches and fetches biomedical literature from PubMed |
| **Citation Graph** | `deepresearch/tools/citation_graph.py` | Builds citation network, identifies foundation papers and research gaps |

### Memory

| Component | Module | Description |
|---|---|---|
| **Research Memory** | `deepresearch/memory/research_memory.py` | SQLite-backed persistence for papers, hypotheses, experiments, drafts, and evaluations |

## Usage

### CLI

```bash
# Install the package
pip install -e .

# Run a research query
deepresearch "transformer sparse attention optimization"

# Run with a config file
deepresearch --config research_config.json

# Specify output directory
deepresearch "quantum machine learning" --output ./my_research
```

### Python API

```python
from deepresearch import ResearchPipeline, ResearchConfig

config = ResearchConfig()
pipeline = ResearchPipeline(config)
state = pipeline.run("your research query")

# Get the LaTeX paper
latex = pipeline.get_paper_latex(state)
print(f"Quality score: {state['evaluations'][-1]['overall_score']}")
```

## State Schema

The pipeline operates on a `ResearchState` TypedDict that flows through all agents:

```
ResearchState
├── query: str
├── stage: PipelineStage (search → read → synthesize → hypothesize → validate → write → done)
├── papers: list[PaperMetadata]
├── summaries: list[PaperSummary]
├── hypotheses: list[Hypothesis]
├── experiments: list[ExperimentDesign]
├── drafts: list[PaperDraft]
├── evaluations: list[EvaluationResult]
├── citation_graph: dict[str, list[str]]
└── error: Optional[str]
```

## Model Configuration

The engine is free-tier aware. Default model is `poolside/laguna-s-2.1:free`
(nous provider). Configure via environment variables:

```bash
export DR_LLM_PROVIDER=nous
export DR_API_KEY=your-api-key
export DR_MODEL=poolside/laguna-s-2.1:free
export ARXIV_EMAIL=your-email@example.com
```

Without an API key, the LLM provider falls back to deterministic responses
so the pipeline can still run offline or in tests.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest --cov=deepresearch --cov-report=term-missing

# Lint
ruff check deepresearch/ tests/
```

## Project Structure

```
deepresearch/
├── __init__.py          # Package exports
├── config.py            # ResearchConfig dataclass + defaults
├── state.py             # TypedDict schemas (ResearchState, etc.)
├── cli.py               # CLI entry point
├── providers/
│   ├── __init__.py
│   └── llm.py           # LLM abstraction with caching + fallback
├── tools/
│   ├── __init__.py
│   ├── arxiv_api.py     # ArXiv API client
│   ├── pubmed_api.py    # PubMed API client
│   └── citation_graph.py  # Citation network analysis + gap detection
├── agents/
│   ├── __init__.py
│   ├── literature_reviewer.py   # Paper search + summarization
│   ├── hypothesis_generator.py  # Counterfactual hypothesis generation
│   ├── experiment_designer.py   # Experiment design + simulation
│   ├── paper_writer.py          # LaTeX paper generation
│   └── pipeline.py              # Pipeline orchestrator
├── memory/
│   ├── __init__.py
│   └── research_memory.py       # SQLite-backed storage
└── evaluation/
    ├── __init__.py
    └── quality_evaluator.py     # Quality metrics + scoring
```

## Testing

```bash
pytest --cov=deepresearch --cov-report=term-missing
```

Target: **85%+ coverage** across all modules.

## License

MIT
