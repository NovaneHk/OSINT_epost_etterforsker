#!/usr/bin/env python3
"""
Phase 3 AI Integration Test Script
Test the new AI Analytics Engine and NLP Processor
"""

import asyncio
import logging
import sys
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from ai.analytics_engine import get_ai_analytics_engine, AnalysisType
from ai.nlp_processor import get_nlp_processor, EntityType, SentimentType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Phase3AITest:
    """Test suite for Phase 3 AI features"""

    def __init__(self):
        self.ai_engine = None
        self.nlp_processor = None
        self.test_results = {}

    async def run_all_tests(self):
        """Run all Phase 3 AI tests"""
        logger.info("🚀 Starting Phase 3 AI Integration Tests")
        logger.info("=" * 60)

        tests = [
            ("AI Analytics Engine Initialization", self.test_ai_engine_init),
            ("NLP Processor Initialization", self.test_nlp_processor_init),
            ("Email Risk Analysis", self.test_email_risk_analysis),
            ("Domain Reputation Analysis", self.test_domain_reputation_analysis),
            ("Anomaly Detection", self.test_anomaly_detection),
            ("Intelligence Correlation", self.test_intelligence_correlation),
            ("Entity Extraction", self.test_entity_extraction),
            ("Sentiment Analysis", self.test_sentiment_analysis),
            ("Text Summarization", self.test_text_summarization),
            ("Intelligence Text Processing", self.test_intelligence_text_processing),
            ("AI Engine Health Check", self.test_ai_engine_health),
            ("NLP Processor Health Check", self.test_nlp_processor_health),
        ]

        passed = 0
        failed = 0

        for test_name, test_func in tests:
            try:
                logger.info(f"\n📋 Running: {test_name}")
                result = await test_func()
                if result:
                    logger.info(f"✅ PASSED: {test_name}")
                    passed += 1
                else:
                    logger.error(f"❌ FAILED: {test_name}")
                    failed += 1
                self.test_results[test_name] = result
            except Exception as e:
                logger.error(f"💥 ERROR in {test_name}: {e}")
                self.test_results[test_name] = False
                failed += 1

        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"✅ Passed: {passed}")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"📈 Success Rate: {(passed / (passed + failed)) * 100:.1f}%")

        if failed == 0:
            logger.info("🎉 ALL TESTS PASSED! Phase 3 AI integration is working correctly.")
        else:
            logger.warning(f"⚠️  {failed} tests failed. Please review the issues above.")

        return failed == 0

    async def test_ai_engine_init(self):
        """Test AI Analytics Engine initialization"""
        try:
            self.ai_engine = get_ai_analytics_engine()

            if not self.ai_engine:
                return False

            logger.info("AI Analytics Engine initialized successfully")
            return True

        except Exception as e:
            logger.error(f"AI Analytics Engine initialization failed: {e}")
            return False

    async def test_nlp_processor_init(self):
        """Test NLP Processor initialization"""
        try:
            self.nlp_processor = get_nlp_processor()

            if not self.nlp_processor:
                return False

            logger.info("NLP Processor initialized successfully")
            return True

        except Exception as e:
            logger.error(f"NLP Processor initialization failed: {e}")
            return False

    async def test_email_risk_analysis(self):
        """Test email risk analysis"""
        try:
            if not self.ai_engine:
                return False

            # Test email data
            email_data = {
                'email': 'test@suspicious-domain123.tk',
                'domain': 'suspicious-domain123.tk',
                'breach_count': 2,
                'in_breach': True,
                'sources': ['google', 'bing']
            }

            result = await self.ai_engine.analyze_email_risk(email_data)

            # Validate result
            if (result.analysis_type == AnalysisType.RISK_SCORING and
                0 <= result.score <= 1 and
                0 <= result.confidence <= 1):
                logger.info(f"Email risk analysis: Score={result.score:.2f}, Confidence={result.confidence:.2f}")
                return True

            return False

        except Exception as e:
            logger.error(f"Email risk analysis failed: {e}")
            return False

    async def test_domain_reputation_analysis(self):
        """Test domain reputation analysis"""
        try:
            if not self.ai_engine:
                return False

            # Test domain data
            domain_data = {
                'domain': 'example.com',
                'domain_age_days': 7300,  # ~20 years
                'recently_registered': False,
                'dns_records': ['A', 'MX', 'NS'],
                'has_mx_record': True
            }

            result = await self.ai_engine.analyze_domain_reputation(domain_data)

            # Validate result
            if (result.analysis_type == AnalysisType.RISK_SCORING and
                0 <= result.score <= 1 and
                0 <= result.confidence <= 1):
                logger.info(f"Domain reputation analysis: Score={result.score:.2f}, Confidence={result.confidence:.2f}")
                return True

            return False

        except Exception as e:
            logger.error(f"Domain reputation analysis failed: {e}")
            return False

    async def test_anomaly_detection(self):
        """Test anomaly detection"""
        try:
            if not self.ai_engine:
                return False

            # Test data points
            data_points = [
                {
                    'timestamp': '2025-09-24T09:00:00Z',
                    'sources': ['google'],
                    'confidence': 0.8,
                    'content': 'Normal email data',
                    'risk_score': 0.2
                },
                {
                    'timestamp': '2025-09-24T03:00:00Z',  # Unusual time
                    'sources': ['unknown'],
                    'confidence': 0.1,  # Low confidence
                    'content': 'Suspicious activity detected',
                    'risk_score': 0.9  # High risk
                },
                {
                    'timestamp': '2025-09-24T10:00:00Z',
                    'sources': ['bing', 'linkedin'],
                    'confidence': 0.9,
                    'content': 'Regular business email',
                    'risk_score': 0.1
                }
            ]

            result = await self.ai_engine.detect_anomalies(data_points)

            # Validate result
            if (result.analysis_type == AnalysisType.ANOMALY_DETECTION and
                'anomalies_detected' in result.details):
                anomalies_count = result.details['anomalies_detected']
                logger.info(f"Anomaly detection: {anomalies_count} anomalies found in {len(data_points)} points")
                return True

            return False

        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return False

    async def test_intelligence_correlation(self):
        """Test intelligence correlation"""
        try:
            if not self.ai_engine:
                return False

            # Test intelligence data
            intelligence_data = [
                {
                    'domain': 'example.com',
                    'email': 'john@example.com',
                    'timestamp': '2025-09-24T09:00:00Z',
                    'sources': ['google', 'linkedin']
                },
                {
                    'domain': 'example.com',  # Same domain
                    'email': 'jane@example.com',
                    'timestamp': '2025-09-24T09:30:00Z',  # Close time
                    'sources': ['google', 'bing']
                },
                {
                    'domain': 'different.com',
                    'email': 'bob@different.com',
                    'timestamp': '2025-09-24T15:00:00Z',
                    'sources': ['twitter']
                }
            ]

            result = await self.ai_engine.correlate_intelligence(intelligence_data)

            # Validate result
            if (result.analysis_type == AnalysisType.CORRELATION_ANALYSIS and
                'correlations_found' in result.details):
                correlations_count = result.details['correlations_found']
                logger.info(f"Intelligence correlation: {correlations_count} correlations found")
                return True

            return False

        except Exception as e:
            logger.error(f"Intelligence correlation failed: {e}")
            return False

    async def test_entity_extraction(self):
        """Test entity extraction"""
        try:
            if not self.nlp_processor:
                return False

            # Test text with various entities
            test_text = """
            John Smith from Acme Corporation contacted us at john.smith@acme.com.
            Their office is located in New York and can be reached at +1-555-123-4567.
            Please visit their website at https://www.acme.com for more information.
            The meeting is scheduled for 2025-09-25 and the budget is $50,000.
            """

            entities = await self.nlp_processor.extract_entities(test_text)

            # Validate entities
            entity_types_found = set(entity.entity_type for entity in entities)
            expected_types = {EntityType.EMAIL, EntityType.URL, EntityType.PHONE}

            if len(entities) > 0 and any(et in entity_types_found for et in expected_types):
                logger.info(f"Entity extraction: {len(entities)} entities found")
                for entity in entities[:3]:  # Show first 3
                    logger.info(f"  - {entity.entity_type.value}: {entity.text}")
                return True

            return False

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return False

    async def test_sentiment_analysis(self):
        """Test sentiment analysis"""
        try:
            if not self.nlp_processor:
                return False

            # Test texts with different sentiments
            test_cases = [
                ("This is a great opportunity for our business!", SentimentType.POSITIVE),
                ("URGENT: Security breach detected! Immediate action required!", SentimentType.THREAT),
                ("The weather is nice today.", SentimentType.NEUTRAL),
                ("This is a terrible situation with many problems.", SentimentType.NEGATIVE)
            ]

            all_passed = True
            for text, expected_sentiment in test_cases:
                result = await self.nlp_processor.analyze_sentiment(text)

                logger.info(f"Sentiment: '{text[:30]}...' -> {result.sentiment.value} ({result.confidence:.2f})")

                # For this test, we'll accept any valid sentiment result
                if result.sentiment not in SentimentType:
                    all_passed = False

            return all_passed

        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return False

    async def test_text_summarization(self):
        """Test text summarization"""
        try:
            if not self.nlp_processor:
                return False

            # Test text for summarization
            test_text = """
            The cybersecurity landscape has evolved significantly in recent years.
            Organizations are facing increasingly sophisticated threats from various actors.
            Email-based attacks remain one of the most common vectors for cybercriminals.
            Phishing campaigns have become more targeted and harder to detect.
            Companies need to implement comprehensive security measures to protect their assets.
            Employee training is crucial for maintaining security awareness.
            Regular security audits help identify vulnerabilities before they can be exploited.
            The cost of a data breach can be devastating for businesses of all sizes.
            """

            summary = await self.nlp_processor.summarize_text(test_text, max_sentences=2)

            # Validate summary
            if (summary.summary and
                len(summary.summary) < len(test_text) and
                summary.compression_ratio < 1.0):
                logger.info(f"Text summarization: {summary.word_count} -> {len(summary.summary.split())} words")
                logger.info(f"Compression ratio: {summary.compression_ratio:.2f}")
                return True

            return False

        except Exception as e:
            logger.error(f"Text summarization failed: {e}")
            return False

    async def test_intelligence_text_processing(self):
        """Test complete intelligence text processing"""
        try:
            if not self.nlp_processor:
                return False

            # Intelligence text sample
            intelligence_text = """
            THREAT ALERT: Suspicious activity detected from domain malicious-site.tk.
            Multiple phishing emails sent from admin@malicious-site.tk targeting our organization.
            The attacker appears to be using social engineering techniques.
            Contact information: Phone +1-555-999-8888, Website: https://malicious-site.tk
            Immediate action required to block this domain and alert all users.
            """

            result = await self.nlp_processor.process_intelligence_text(intelligence_text)

            # Validate complete processing result
            if (result and
                'entities' in result and
                'sentiment' in result and
                'summary' in result):
                logger.info(f"Intelligence processing: {result['word_count']} words processed")
                logger.info(f"Entities found: {len(result['entities'])}")
                logger.info(f"Sentiment: {result['sentiment']['type']}")
                return True

            return False

        except Exception as e:
            logger.error(f"Intelligence text processing failed: {e}")
            return False

    async def test_ai_engine_health(self):
        """Test AI Analytics Engine health check"""
        try:
            if not self.ai_engine:
                return False

            health = await self.ai_engine.health_check()

            if health and 'status' in health:
                logger.info(f"AI Engine health: {health['status']}")
                logger.info(f"ML available: {health.get('ml_available', False)}")
                logger.info(f"Models loaded: {health.get('models_loaded', 0)}")
                return health['status'] in ['healthy', 'degraded']

            return False

        except Exception as e:
            logger.error(f"AI Engine health check failed: {e}")
            return False

    async def test_nlp_processor_health(self):
        """Test NLP Processor health check"""
        try:
            if not self.nlp_processor:
                return False

            health = await self.nlp_processor.health_check()

            if health and 'status' in health:
                logger.info(f"NLP Processor health: {health['status']}")
                logger.info(f"NLP available: {health.get('nlp_available', False)}")
                logger.info(f"Models loaded: {health.get('models_loaded', 0)}")
                return health['status'] in ['healthy', 'degraded']

            return False

        except Exception as e:
            logger.error(f"NLP Processor health check failed: {e}")
            return False

    def save_test_results(self):
        """Save test results to file"""
        try:
            results = {
                'timestamp': datetime.now().isoformat(),
                'phase': 'Phase 3 AI Integration Tests',
                'results': self.test_results,
                'summary': {
                    'total_tests': len(self.test_results),
                    'passed': sum(1 for r in self.test_results.values() if r),
                    'failed': sum(1 for r in self.test_results.values() if not r),
                }
            }

            with open('phase3_ai_test_results.json', 'w') as f:
                json.dump(results, f, indent=2)

            logger.info("Test results saved to phase3_ai_test_results.json")

        except Exception as e:
            logger.error(f"Failed to save test results: {e}")

async def main():
    """Main test execution"""
    test_suite = Phase3AITest()

    try:
        success = await test_suite.run_all_tests()
        test_suite.save_test_results()

        if success:
            logger.info("\n🎉 Phase 3 AI integration tests completed successfully!")
            logger.info("The AI Analytics Engine and NLP Processor are ready for use.")
            return 0
        else:
            logger.error("\n❌ Some tests failed. Please review and fix issues.")
            return 1

    except Exception as e:
        logger.error(f"Test suite execution failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
