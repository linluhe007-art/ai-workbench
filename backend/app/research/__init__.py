"""Research Module - Phase Beta-Search"""
from app.research.extractor import InformationExtractor, Document, get_extractor
from app.research.citation import Citation, CitationManager, get_citation_manager

__all__ = [
    "InformationExtractor", "Document", "get_extractor",
    "Citation", "CitationManager", "get_citation_manager",
]
