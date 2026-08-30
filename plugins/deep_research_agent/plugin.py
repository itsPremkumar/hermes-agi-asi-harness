"""deep_research_agent — re-export module."""
from . import logger, Evidence, ResearchPhase, DeepResearchReport, FreeSearchBackend, DuckDuckGoHTML

__all__ = ["DeepResearchReport", "DuckDuckGoHTML", "Evidence", "FreeSearchBackend", "ResearchPhase", "logger"]
