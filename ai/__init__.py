"""
AI Module for Phase 3
Advanced Analytics and Natural Language Processing for OSINT Intelligence
"""

from .analytics_engine import AIAnalyticsEngine, get_ai_analytics_engine, AnalysisType, AnalysisResult
from .nlp_processor import NLPProcessor, get_nlp_processor, EntityType, SentimentType, ExtractedEntity, SentimentResult, TextSummary

__all__ = [
    'AIAnalyticsEngine',
    'get_ai_analytics_engine',
    'AnalysisType',
    'AnalysisResult',
    'NLPProcessor',
    'get_nlp_processor',
    'EntityType',
    'SentimentType',
    'ExtractedEntity',
    'SentimentResult',
    'TextSummary'
]
