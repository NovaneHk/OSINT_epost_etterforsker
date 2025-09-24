"""
Natural Language Processing Module for Phase 3
Advanced text analysis and entity extraction for OSINT intelligence
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json

# NLP imports
try:
    import spacy
    from spacy import displacy
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False
    logging.warning("spaCy not available. Install spacy for full NLP functionality.")

from .utils import AIError as OSINTError, simple_error_handler as handle_errors
from core.performance import PerformanceMonitor

logger = logging.getLogger(__name__)

class EntityType(Enum):
    """Types of entities that can be extracted"""
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    IP_ADDRESS = "ip_address"
    DOMAIN = "domain"
    DATE = "date"
    MONEY = "money"

class SentimentType(Enum):
    """Sentiment analysis types"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    THREAT = "threat"
    URGENT = "urgent"

@dataclass
class ExtractedEntity:
    """Extracted entity from text"""
    text: str
    entity_type: EntityType
    confidence: float
    start_pos: int
    end_pos: int
    context: str
    metadata: Dict[str, Any]

@dataclass
class SentimentResult:
    """Sentiment analysis result"""
    sentiment: SentimentType
    confidence: float
    score: float  # -1 to 1 scale
    details: Dict[str, Any]

@dataclass
class TextSummary:
    """Text summarization result"""
    summary: str
    key_points: List[str]
    entities: List[ExtractedEntity]
    sentiment: SentimentResult
    word_count: int
    compression_ratio: float

class NLPProcessor:
    """
    Advanced Natural Language Processing for OSINT Intelligence
    Provides entity extraction, sentiment analysis, and text summarization
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.performance_monitor = PerformanceMonitor()
        self.nlp_models = {}
        self.entity_patterns = {}
        self.sentiment_keywords = {}

        # Initialize NLP components
        self._initialize_nlp()
        self._load_patterns()
        self._load_sentiment_keywords()

    def _initialize_nlp(self):
        """Initialize NLP models and components"""
        try:
            if NLP_AVAILABLE:
                # Try to load English model
                try:
                    self.nlp_models['en'] = spacy.load("en_core_web_sm")
                    logger.info("Loaded English NLP model")
                except OSError:
                    logger.warning("English NLP model not found. Using basic processing.")
                    self.nlp_models['en'] = None

                # Try to load other language models if available
                for lang in ['nb', 'de', 'fr']:  # Norwegian, German, French
                    try:
                        model_name = f"{lang}_core_news_sm"
                        self.nlp_models[lang] = spacy.load(model_name)
                        logger.info(f"Loaded {lang} NLP model")
                    except OSError:
                        self.nlp_models[lang] = None
            else:
                logger.warning("spaCy not available. Using regex-based processing.")

        except Exception as e:
            logger.error(f"Failed to initialize NLP models: {e}")

    def _load_patterns(self):
        """Load regex patterns for entity extraction"""
        self.entity_patterns = {
            EntityType.EMAIL: r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            EntityType.PHONE: r'(\+\d{1,3}[-.\s]?)?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
            EntityType.URL: r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?',
            EntityType.IP_ADDRESS: r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            EntityType.DOMAIN: r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b',
            EntityType.DATE: r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',
            EntityType.MONEY: r'\$\d+(?:,\d{3})*(?:\.\d{2})?|\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|EUR|NOK|GBP)',
        }

    def _load_sentiment_keywords(self):
        """Load sentiment analysis keywords"""
        self.sentiment_keywords = {
            SentimentType.THREAT: [
                'threat', 'attack', 'malicious', 'suspicious', 'dangerous', 'harmful',
                'breach', 'hack', 'exploit', 'vulnerability', 'compromise', 'malware',
                'phishing', 'scam', 'fraud', 'criminal', 'illegal', 'unauthorized'
            ],
            SentimentType.URGENT: [
                'urgent', 'immediate', 'critical', 'emergency', 'asap', 'priority',
                'deadline', 'time-sensitive', 'quickly', 'fast', 'now', 'today'
            ],
            SentimentType.POSITIVE: [
                'good', 'excellent', 'great', 'positive', 'success', 'achievement',
                'beneficial', 'advantage', 'opportunity', 'improvement', 'effective'
            ],
            SentimentType.NEGATIVE: [
                'bad', 'terrible', 'negative', 'failure', 'problem', 'issue',
                'concern', 'risk', 'disadvantage', 'loss', 'decline', 'poor'
            ]
        }

    @handle_errors
    async def extract_entities(self, text: str, language: str = 'en') -> List[ExtractedEntity]:
        """
        Extract entities from text using NLP and regex patterns

        Args:
            text: Text to analyze
            language: Language code (en, nb, de, fr)

        Returns:
            List of extracted entities
        """
        timer_id = self.performance_monitor.start_timer("entity_extraction")

        try:
            entities = []

            # Use spaCy model if available
            if NLP_AVAILABLE and language in self.nlp_models and self.nlp_models[language]:
                spacy_entities = await self._extract_spacy_entities(text, language)
                entities.extend(spacy_entities)

            # Use regex patterns for specific entity types
            regex_entities = await self._extract_regex_entities(text)
            entities.extend(regex_entities)

            # Remove duplicates and merge overlapping entities
            entities = self._deduplicate_entities(entities)

            processing_time = self.performance_monitor.stop_timer(timer_id, 'entity_extraction')
            logger.info(f"Entity extraction completed: {len(entities)} entities found in {processing_time:.2f}ms")

            return entities

        except Exception as e:
            self.performance_monitor.stop_timer(timer_id, 'entity_extraction')
            logger.error(f"Entity extraction failed: {e}")
            raise OSINTError(f"Entity extraction failed: {e}")

    @handle_errors
    async def analyze_sentiment(self, text: str, language: str = 'en') -> SentimentResult:
        """
        Analyze sentiment of text

        Args:
            text: Text to analyze
            language: Language code

        Returns:
            Sentiment analysis result
        """
        timer_id = self.performance_monitor.start_timer("sentiment_analysis")

        try:
            # Use keyword-based sentiment analysis
            sentiment_scores = self._calculate_sentiment_scores(text)

            # Determine overall sentiment
            sentiment, confidence, score = self._determine_sentiment(sentiment_scores)

            # Create sentiment result
            result = SentimentResult(
                sentiment=sentiment,
                confidence=confidence,
                score=score,
                details={
                    'keyword_scores': sentiment_scores,
                    'text_length': len(text),
                    'language': language,
                    'analysis_method': 'keyword_based'
                }
            )

            processing_time = self.performance_monitor.stop_timer(timer_id, 'sentiment_analysis')
            logger.info(f"Sentiment analysis completed: {sentiment.value} ({confidence:.2f}) in {processing_time:.2f}ms")

            return result

        except Exception as e:
            self.performance_monitor.stop_timer(timer_id, 'sentiment_analysis')
            logger.error(f"Sentiment analysis failed: {e}")
            raise OSINTError(f"Sentiment analysis failed: {e}")

    @handle_errors
    async def summarize_text(self, text: str, max_sentences: int = 3, language: str = 'en') -> TextSummary:
        """
        Summarize text and extract key information

        Args:
            text: Text to summarize
            max_sentences: Maximum sentences in summary
            language: Language code

        Returns:
            Text summary with key information
        """
        timer_id = self.performance_monitor.start_timer("text_summarization")

        try:
            # Extract entities
            entities = await self.extract_entities(text, language)

            # Analyze sentiment
            sentiment = await self.analyze_sentiment(text, language)

            # Generate summary
            summary = self._generate_extractive_summary(text, max_sentences)

            # Extract key points
            key_points = self._extract_key_points(text, entities)

            # Calculate metrics
            word_count = len(text.split())
            summary_word_count = len(summary.split())
            compression_ratio = summary_word_count / word_count if word_count > 0 else 0

            # Create text summary
            result = TextSummary(
                summary=summary,
                key_points=key_points,
                entities=entities,
                sentiment=sentiment,
                word_count=word_count,
                compression_ratio=compression_ratio
            )

            processing_time = self.performance_monitor.stop_timer(timer_id, 'text_summarization')
            logger.info(f"Text summarization completed in {processing_time:.2f}ms")

            return result

        except Exception as e:
            self.performance_monitor.stop_timer(timer_id, 'text_summarization')
            logger.error(f"Text summarization failed: {e}")
            raise OSINTError(f"Text summarization failed: {e}")

    async def _extract_spacy_entities(self, text: str, language: str) -> List[ExtractedEntity]:
        """Extract entities using spaCy NLP model"""
        entities = []

        try:
            nlp = self.nlp_models[language]
            doc = nlp(text)

            for ent in doc.ents:
                # Map spaCy entity types to our entity types
                entity_type = self._map_spacy_entity_type(ent.label_)
                if entity_type:
                    # Get context around the entity
                    context = self._get_entity_context(text, ent.start_char, ent.end_char)

                    entity = ExtractedEntity(
                        text=ent.text,
                        entity_type=entity_type,
                        confidence=0.8,  # spaCy confidence (simplified)
                        start_pos=ent.start_char,
                        end_pos=ent.end_char,
                        context=context,
                        metadata={
                            'spacy_label': ent.label_,
                            'spacy_description': spacy.explain(ent.label_),
                            'extraction_method': 'spacy'
                        }
                    )
                    entities.append(entity)

        except Exception as e:
            logger.error(f"spaCy entity extraction failed: {e}")

        return entities

    async def _extract_regex_entities(self, text: str) -> List[ExtractedEntity]:
        """Extract entities using regex patterns"""
        entities = []

        for entity_type, pattern in self.entity_patterns.items():
            try:
                matches = re.finditer(pattern, text, re.IGNORECASE)

                for match in matches:
                    # Get context around the entity
                    context = self._get_entity_context(text, match.start(), match.end())

                    entity = ExtractedEntity(
                        text=match.group(),
                        entity_type=entity_type,
                        confidence=0.9,  # High confidence for regex matches
                        start_pos=match.start(),
                        end_pos=match.end(),
                        context=context,
                        metadata={
                            'pattern': pattern,
                            'extraction_method': 'regex'
                        }
                    )
                    entities.append(entity)

            except Exception as e:
                logger.error(f"Regex extraction failed for {entity_type}: {e}")

        return entities

    def _map_spacy_entity_type(self, spacy_label: str) -> Optional[EntityType]:
        """Map spaCy entity labels to our entity types"""
        mapping = {
            'PERSON': EntityType.PERSON,
            'ORG': EntityType.ORGANIZATION,
            'GPE': EntityType.LOCATION,  # Geopolitical entity
            'LOC': EntityType.LOCATION,
            'DATE': EntityType.DATE,
            'MONEY': EntityType.MONEY,
        }
        return mapping.get(spacy_label)

    def _get_entity_context(self, text: str, start: int, end: int, context_size: int = 50) -> str:
        """Get context around an entity"""
        context_start = max(0, start - context_size)
        context_end = min(len(text), end + context_size)

        context = text[context_start:context_end]

        # Add ellipsis if context is truncated
        if context_start > 0:
            context = "..." + context
        if context_end < len(text):
            context = context + "..."

        return context

    def _deduplicate_entities(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """Remove duplicate and overlapping entities"""
        if not entities:
            return entities

        # Sort by start position
        entities.sort(key=lambda x: x.start_pos)

        deduplicated = []
        for entity in entities:
            # Check for overlap with existing entities
            overlaps = False
            for existing in deduplicated:
                if (entity.start_pos < existing.end_pos and
                    entity.end_pos > existing.start_pos):
                    # Entities overlap - keep the one with higher confidence
                    if entity.confidence > existing.confidence:
                        deduplicated.remove(existing)
                        deduplicated.append(entity)
                    overlaps = True
                    break

            if not overlaps:
                deduplicated.append(entity)

        return deduplicated

    def _calculate_sentiment_scores(self, text: str) -> Dict[str, float]:
        """Calculate sentiment scores based on keywords"""
        text_lower = text.lower()
        scores = {}

        for sentiment_type, keywords in self.sentiment_keywords.items():
            score = 0
            for keyword in keywords:
                # Count occurrences and weight by keyword importance
                count = text_lower.count(keyword.lower())
                score += count * (1.0 if len(keyword) > 5 else 0.5)  # Longer keywords get more weight

            # Normalize by text length
            scores[sentiment_type.value] = score / len(text.split()) if text.split() else 0

        return scores

    def _determine_sentiment(self, sentiment_scores: Dict[str, float]) -> Tuple[SentimentType, float, float]:
        """Determine overall sentiment from scores"""
        # Check for threat indicators first (highest priority)
        if sentiment_scores.get('threat', 0) > 0.1:
            return SentimentType.THREAT, 0.8, -0.8

        # Check for urgency
        if sentiment_scores.get('urgent', 0) > 0.1:
            return SentimentType.URGENT, 0.7, 0.0

        # Compare positive vs negative
        positive_score = sentiment_scores.get('positive', 0)
        negative_score = sentiment_scores.get('negative', 0)

        if positive_score > negative_score and positive_score > 0.05:
            confidence = min(positive_score * 10, 1.0)
            return SentimentType.POSITIVE, confidence, positive_score - negative_score
        elif negative_score > positive_score and negative_score > 0.05:
            confidence = min(negative_score * 10, 1.0)
            return SentimentType.NEGATIVE, confidence, -(negative_score - positive_score)
        else:
            return SentimentType.NEUTRAL, 0.6, 0.0

    def _generate_extractive_summary(self, text: str, max_sentences: int) -> str:
        """Generate extractive summary by selecting key sentences"""
        sentences = self._split_into_sentences(text)

        if len(sentences) <= max_sentences:
            return text

        # Score sentences based on various factors
        sentence_scores = []
        for i, sentence in enumerate(sentences):
            score = self._score_sentence(sentence, text)
            sentence_scores.append((score, i, sentence))

        # Sort by score and select top sentences
        sentence_scores.sort(reverse=True)
        selected_sentences = sentence_scores[:max_sentences]

        # Sort selected sentences by original order
        selected_sentences.sort(key=lambda x: x[1])

        # Combine into summary
        summary = ' '.join([sentence for _, _, sentence in selected_sentences])
        return summary

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting (can be improved with spaCy)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences

    def _score_sentence(self, sentence: str, full_text: str) -> float:
        """Score a sentence for importance in summary"""
        score = 0.0

        # Length factor (prefer medium-length sentences)
        words = sentence.split()
        if 10 <= len(words) <= 30:
            score += 0.3

        # Position factor (first and last sentences are often important)
        sentences = self._split_into_sentences(full_text)
        sentence_index = sentences.index(sentence) if sentence in sentences else -1
        if sentence_index == 0 or sentence_index == len(sentences) - 1:
            score += 0.2

        # Keyword density
        important_words = ['important', 'significant', 'key', 'main', 'primary', 'critical']
        for word in important_words:
            if word.lower() in sentence.lower():
                score += 0.1

        # Entity presence (sentences with entities are often important)
        for pattern in self.entity_patterns.values():
            if re.search(pattern, sentence, re.IGNORECASE):
                score += 0.15

        return score

    def _extract_key_points(self, text: str, entities: List[ExtractedEntity]) -> List[str]:
        """Extract key points from text"""
        key_points = []

        # Extract sentences containing entities
        sentences = self._split_into_sentences(text)
        for sentence in sentences:
            for entity in entities:
                if entity.text.lower() in sentence.lower():
                    if sentence not in key_points:
                        key_points.append(sentence)
                    break

        # Extract sentences with high importance keywords
        importance_keywords = [
            'important', 'significant', 'key', 'main', 'critical', 'essential',
            'note', 'warning', 'alert', 'attention', 'notice'
        ]

        for sentence in sentences:
            for keyword in importance_keywords:
                if keyword.lower() in sentence.lower():
                    if sentence not in key_points:
                        key_points.append(sentence)
                    break

        # Limit to top key points
        return key_points[:5]

    async def process_intelligence_text(self, text: str, language: str = 'en') -> Dict[str, Any]:
        """
        Process intelligence text with full NLP analysis

        Args:
            text: Intelligence text to process
            language: Language code

        Returns:
            Complete NLP analysis results
        """
        timer_id = self.performance_monitor.start_timer("intelligence_text_processing")

        try:
            # Perform all NLP analyses
            entities = await self.extract_entities(text, language)
            sentiment = await self.analyze_sentiment(text, language)
            summary = await self.summarize_text(text, language=language)

            # Compile results
            results = {
                'text_length': len(text),
                'word_count': len(text.split()),
                'language': language,
                'entities': [
                    {
                        'text': e.text,
                        'type': e.entity_type.value,
                        'confidence': e.confidence,
                        'context': e.context,
                        'metadata': e.metadata
                    } for e in entities
                ],
                'sentiment': {
                    'type': sentiment.sentiment.value,
                    'confidence': sentiment.confidence,
                    'score': sentiment.score,
                    'details': sentiment.details
                },
                'summary': {
                    'text': summary.summary,
                    'key_points': summary.key_points,
                    'compression_ratio': summary.compression_ratio
                },
                'analysis_metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'nlp_available': NLP_AVAILABLE,
                    'models_used': list(self.nlp_models.keys()),
                    'processing_time': 0.0
                }
            }

            processing_time = self.performance_monitor.stop_timer(timer_id, 'intelligence_text_processing')
            results['analysis_metadata']['processing_time'] = processing_time

            logger.info(f"Intelligence text processing completed in {processing_time:.2f}ms")
            return results

        except Exception as e:
            self.performance_monitor.stop_timer(timer_id, 'intelligence_text_processing')
            logger.error(f"Intelligence text processing failed: {e}")
            raise OSINTError(f"Intelligence text processing failed: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on NLP processor"""
        health_status = {
            'status': 'healthy',
            'nlp_available': NLP_AVAILABLE,
            'models_loaded': len([m for m in self.nlp_models.values() if m is not None]),
            'total_models': len(self.nlp_models),
            'patterns_loaded': len(self.entity_patterns),
            'sentiment_keywords': len(self.sentiment_keywords),
            'issues': []
        }

        # Check NLP availability
        if not NLP_AVAILABLE:
            health_status['issues'].append('spaCy not available - using regex-based processing')

        # Check model availability
        if NLP_AVAILABLE:
            missing_models = [lang for lang, model in self.nlp_models.items() if model is None]
            if missing_models:
                health_status['issues'].append(f'Missing NLP models: {missing_models}')

        # Test basic functionality
        try:
            test_text = "This is a test email: test@example.com"
            entities = await self.extract_entities(test_text)
            if not entities:
                health_status['issues'].append('Entity extraction test failed')
                health_status['status'] = 'degraded'
        except Exception as e:
            health_status['issues'].append(f'NLP functionality test failed: {e}')
            health_status['status'] = 'degraded'

        return health_status


# Factory function for creating NLP Processor
def get_nlp_processor(config: Optional[Dict[str, Any]] = None) -> NLPProcessor:
    """
    Factory function to create and configure NLP Processor

    Args:
        config: Optional configuration dictionary

    Returns:
        Configured NLPProcessor instance
    """
    if config is None:
        config = {
            'languages': ['en', 'nb'],
            'entity_extraction': True,
            'sentiment_analysis': True,
            'text_summarization': True,
            'context_size': 50
        }

    return NLPProcessor(config)
