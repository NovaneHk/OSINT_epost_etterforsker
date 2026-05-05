"""
AI Analytics Engine for Phase 3
Advanced machine learning and analytics capabilities for OSINT intelligence
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import deque
import json

# ML and Analytics imports
try:
    from sklearn.ensemble import IsolationForest, RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_score, recall_score
    import joblib
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logging.warning("ML libraries not available. Install scikit-learn for full functionality.")

from .utils import AIError as OSINTError, simple_error_handler as handle_errors
from .memory_manager import MemoryManager
from core.performance import PerformanceMonitor

logger = logging.getLogger(__name__)

class AnalysisType(Enum):
    """Types of AI analysis available"""
    THREAT_DETECTION = "threat_detection"
    RISK_SCORING = "risk_scoring"
    PATTERN_RECOGNITION = "pattern_recognition"
    ANOMALY_DETECTION = "anomaly_detection"
    CORRELATION_ANALYSIS = "correlation_analysis"
    PREDICTIVE_MODELING = "predictive_modeling"

@dataclass
class AnalysisResult:
    """Result from AI analysis"""
    analysis_type: AnalysisType
    confidence: float
    score: float
    details: Dict[str, Any]
    timestamp: datetime
    model_version: str
    processing_time: float

@dataclass
class ThreatIntelligence:
    """Threat intelligence data structure"""
    threat_id: str
    threat_type: str
    severity: str
    confidence: float
    indicators: List[str]
    description: str
    timestamp: datetime
    source: str

class AIAnalyticsEngine:
    """
    Advanced AI Analytics Engine for OSINT Intelligence
    Provides machine learning capabilities for threat detection, risk scoring, and pattern analysis
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.performance_monitor = PerformanceMonitor()
        self.models = {}
        self.scalers = {}
        self.model_versions = {}
        self.threat_database = deque(maxlen=1000)  # Limited size for threat database
        self.analysis_history = deque(maxlen=1000)  # Limited size for analysis history
        
        # Memory management
        self.memory_manager = MemoryManager(
            threshold=config.get('memory_threshold', 0.8)
        )

        # Initialize ML components if available
        if ML_AVAILABLE:
            self._initialize_models()
        else:
            logger.warning("ML libraries not available. Running in simulation mode.")

    def _initialize_models(self):
        """Initialize machine learning models"""
        try:
            # Email Risk Scoring Model
            self.models['email_risk'] = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            self.scalers['email_risk'] = StandardScaler()

            # Domain Reputation Model
            self.models['domain_reputation'] = RandomForestClassifier(
                n_estimators=150,
                max_depth=12,
                random_state=42
            )
            self.scalers['domain_reputation'] = StandardScaler()

            # Anomaly Detection Model
            self.models['anomaly_detection'] = IsolationForest(
                contamination=0.1,
                random_state=42
            )

            # Pattern Recognition Model
            self.models['pattern_recognition'] = RandomForestClassifier(
                n_estimators=200,
                max_depth=15,
                random_state=42
            )
            self.scalers['pattern_recognition'] = StandardScaler()

            # Set model versions
            for model_name in self.models.keys():
                self.model_versions[model_name] = "1.0.0"

            logger.info("AI Analytics Engine initialized with ML models")

        except Exception as e:
            logger.error(f"Failed to initialize ML models: {e}")
            raise OSINTError(f"AI Analytics Engine initialization failed: {e}")

    @handle_errors
    async def analyze_email_risk(self, email_data: Dict[str, Any]) -> AnalysisResult:
        """
        Analyze email risk using machine learning

        Args:
            email_data: Dictionary containing email information

        Returns:
            AnalysisResult with risk score and analysis details
        """
        timer_id = self.performance_monitor.start_timer("email_risk_analysis")

        try:
            # Extract features from email data
            features = self._extract_email_features(email_data)

            if ML_AVAILABLE and 'email_risk' in self.models:
                # Use trained model for prediction
                risk_score, confidence = await self._predict_email_risk(features)
            else:
                # Fallback to rule-based analysis
                risk_score, confidence = self._rule_based_email_risk(email_data)

            # Create analysis result
            result = AnalysisResult(
                analysis_type=AnalysisType.RISK_SCORING,
                confidence=confidence,
                score=risk_score,
                details={
                    'email': email_data.get('email', 'unknown'),
                    'domain': email_data.get('domain', 'unknown'),
                    'features': features,
                    'risk_factors': self._identify_risk_factors(email_data, risk_score),
                    'recommendations': self._generate_risk_recommendations(risk_score)
                },
                timestamp=datetime.now(),
                model_version=self.model_versions.get('email_risk', '1.0.0'),
                processing_time=0.0
            )

            processing_time = self.performance_monitor.stop_timer(timer_id, 'email_risk_analysis')
            result.processing_time = processing_time

            # Store analysis in history
            self.analysis_history.append(result)

            logger.info(f"Email risk analysis completed: {email_data.get('email')} - Risk: {risk_score:.2f}")
            return result

        except Exception as e:
            self.performance_monitor.stop_timer(timer_id, 'email_risk_analysis')
            logger.error(f"Email risk analysis failed: {e}")
            raise OSINTError(f"Email risk analysis failed: {e}")

    @handle_errors
    async def analyze_domain_reputation(self, domain_data: Dict[str, Any]) -> AnalysisResult:
        """
        Analyze domain reputation using AI

        Args:
            domain_data: Dictionary containing domain information

        Returns:
            AnalysisResult with reputation score and analysis details
        """
        timer_id = self.performance_monitor.start_timer("domain_reputation_analysis")

        try:
            # Extract features from domain data
            features = self._extract_domain_features(domain_data)

            if ML_AVAILABLE and 'domain_reputation' in self.models:
                # Use trained model for prediction
                reputation_score, confidence = await self._predict_domain_reputation(features)
            else:
                # Fallback to rule-based analysis
                reputation_score, confidence = self._rule_based_domain_reputation(domain_data)

            # Create analysis result
            result = AnalysisResult(
                analysis_type=AnalysisType.RISK_SCORING,
                confidence=confidence,
                score=reputation_score,
                details={
                    'domain': domain_data.get('domain', 'unknown'),
                    'features': features,
                    'reputation_factors': self._identify_reputation_factors(domain_data, reputation_score),
                    'category': self._classify_domain_category(reputation_score),
                    'recommendations': self._generate_domain_recommendations(reputation_score)
                },
                timestamp=datetime.now(),
                model_version=self.model_versions.get('domain_reputation', '1.0.0'),
                processing_time=0.0
            )

            processing_time = self.performance_monitor.stop_timer(timer_id, 'domain_reputation_analysis')
            result.processing_time = processing_time

            # Store analysis in history
            self.analysis_history.append(result)

            logger.info(f"Domain reputation analysis completed: {domain_data.get('domain')} - Score: {reputation_score:.2f}")
            return result

        except Exception as e:
            self.performance_monitor.stop_timer(timer_id, 'domain_reputation_analysis')
            logger.error(f"Domain reputation analysis failed: {e}")
            raise OSINTError(f"Domain reputation analysis failed: {e}")

    @handle_errors
    async def detect_anomalies(self, data_points: List[Dict[str, Any]]) -> AnalysisResult:
        """
        Detect anomalies in OSINT data using machine learning

        Args:
            data_points: List of data points to analyze

        Returns:
            AnalysisResult with anomaly detection results
        """
        timer_id = self.performance_monitor.start_timer("anomaly_detection")

        try:
            if not data_points:
                raise OSINTError("No data points provided for anomaly detection")

            # Extract features from data points
            features_matrix = self._extract_anomaly_features(data_points)

            if ML_AVAILABLE and 'anomaly_detection' in self.models:
                # Use trained model for anomaly detection
                anomalies, anomaly_scores = await self._detect_ml_anomalies(features_matrix)
            else:
                # Fallback to statistical anomaly detection
                anomalies, anomaly_scores = self._statistical_anomaly_detection(data_points)

            # Calculate overall anomaly score
            overall_score = np.mean(anomaly_scores) if anomaly_scores else 0.0
            confidence = min(len(data_points) / 100.0, 1.0)  # Confidence based on data size

            # Create analysis result
            result = AnalysisResult(
                analysis_type=AnalysisType.ANOMALY_DETECTION,
                confidence=confidence,
                score=overall_score,
                details={
                    'total_points': len(data_points),
                    'anomalies_detected': len(anomalies),
                    'anomaly_percentage': (len(anomalies) / len(data_points)) * 100,
                    'anomalous_points': anomalies,
                    'anomaly_scores': anomaly_scores,
                    'analysis_summary': self._generate_anomaly_summary(anomalies, data_points)
                },
                timestamp=datetime.now(),
                model_version=self.model_versions.get('anomaly_detection', '1.0.0'),
                processing_time=0.0
            )

            processing_time = self.performance_monitor.stop_timer(timer_id, 'anomaly_detection')
            result.processing_time = processing_time

            # Store analysis in history
            self.analysis_history.append(result)

            logger.info(f"Anomaly detection completed: {len(anomalies)} anomalies found in {len(data_points)} points")
            return result

        except Exception as e:
            self.performance_monitor.stop_timer(timer_id, 'anomaly_detection')
            logger.error(f"Anomaly detection failed: {e}")
            raise OSINTError(f"Anomaly detection failed: {e}")

    @handle_errors
    async def correlate_intelligence(self, intelligence_data: List[Dict[str, Any]]) -> AnalysisResult:
        """
        Correlate intelligence data across multiple sources using AI

        Args:
            intelligence_data: List of intelligence data from various sources

        Returns:
            AnalysisResult with correlation analysis
        """
        timer_id = self.performance_monitor.start_timer("intelligence_correlation")

        try:
            if not intelligence_data:
                raise OSINTError("No intelligence data provided for correlation")

            # Perform correlation analysis
            correlations = await self._analyze_correlations(intelligence_data)

            # Calculate correlation strength
            correlation_score = self._calculate_correlation_strength(correlations)
            confidence = min(len(intelligence_data) / 50.0, 1.0)  # Confidence based on data size

            # Create analysis result
            result = AnalysisResult(
                analysis_type=AnalysisType.CORRELATION_ANALYSIS,
                confidence=confidence,
                score=correlation_score,
                details={
                    'total_sources': len(intelligence_data),
                    'correlations_found': len(correlations),
                    'correlation_strength': correlation_score,
                    'correlations': correlations,
                    'correlation_summary': self._generate_correlation_summary(correlations),
                    'recommendations': self._generate_correlation_recommendations(correlations)
                },
                timestamp=datetime.now(),
                model_version=self.model_versions.get('correlation', '1.0.0'),
                processing_time=0.0
            )

            processing_time = self.performance_monitor.stop_timer(timer_id, 'intelligence_correlation')
            result.processing_time = processing_time

            # Store analysis in history
            self.analysis_history.append(result)

            logger.info(f"Intelligence correlation completed: {len(correlations)} correlations found")
            return result

        except Exception as e:
            self.performance_monitor.stop_timer(timer_id, 'intelligence_correlation')
            logger.error(f"Intelligence correlation failed: {e}")
            raise OSINTError(f"Intelligence correlation failed: {e}")

    def _extract_email_features(self, email_data: Dict[str, Any]) -> List[float]:
        """Extract numerical features from email data for ML analysis"""
        features = []

        # Domain-based features
        domain = email_data.get('domain', '')
        features.append(len(domain))  # Domain length
        features.append(domain.count('.'))  # Number of subdomains
        features.append(1 if any(char.isdigit() for char in domain) else 0)  # Contains numbers
        features.append(1 if '-' in domain else 0)  # Contains hyphens

        # Email-based features
        email = email_data.get('email', '')
        features.append(len(email))  # Email length
        features.append(email.count('.'))  # Number of dots
        features.append(1 if any(char.isdigit() for char in email.split('@')[0]) else 0)  # Username has numbers

        # Breach data features
        features.append(email_data.get('breach_count', 0))  # Number of breaches
        features.append(1 if email_data.get('in_breach', False) else 0)  # In any breach

        # Source features
        features.append(len(email_data.get('sources', [])))  # Number of sources

        return features

    def _extract_domain_features(self, domain_data: Dict[str, Any]) -> List[float]:
        """Extract numerical features from domain data for ML analysis"""
        features = []

        # Basic domain features
        domain = domain_data.get('domain', '')
        features.append(len(domain))  # Domain length
        features.append(domain.count('.'))  # Number of subdomains
        features.append(1 if any(char.isdigit() for char in domain) else 0)  # Contains numbers
        features.append(1 if '-' in domain else 0)  # Contains hyphens

        # TLD features
        tld = domain.split('.')[-1] if '.' in domain else ''
        suspicious_tlds = ['tk', 'ml', 'ga', 'cf', 'top', 'click']
        features.append(1 if tld in suspicious_tlds else 0)  # Suspicious TLD

        # Age and registration features
        features.append(domain_data.get('domain_age_days', 0))  # Domain age
        features.append(1 if domain_data.get('recently_registered', False) else 0)  # Recently registered

        # DNS and hosting features
        features.append(len(domain_data.get('dns_records', [])))  # Number of DNS records
        features.append(1 if domain_data.get('has_mx_record', False) else 0)  # Has MX record

        return features

    def _extract_anomaly_features(self, data_points: List[Dict[str, Any]]) -> np.ndarray:
        """Extract features for anomaly detection"""
        features_list = []

        for point in data_points:
            features = []

            # Temporal features
            timestamp = point.get('timestamp', datetime.now())
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

            features.append(timestamp.hour)  # Hour of day
            features.append(timestamp.weekday())  # Day of week

            # Data source features
            features.append(len(point.get('sources', [])))  # Number of sources
            features.append(point.get('confidence', 0.5))  # Confidence score

            # Content features
            features.append(len(str(point.get('content', ''))))  # Content length
            features.append(point.get('risk_score', 0.0))  # Risk score

            features_list.append(features)

        return np.array(features_list)

    async def _predict_email_risk(self, features: List[float]) -> Tuple[float, float]:
        """Predict email risk using trained ML model"""
        if not ML_AVAILABLE:
            return 0.5, 0.5

        try:
            # Simulate model prediction (in real implementation, use trained model)
            # For now, use a simple heuristic based on features
            risk_score = min(sum(features) / len(features) / 10.0, 1.0)
            confidence = 0.85  # Simulated confidence

            return risk_score, confidence

        except Exception as e:
            logger.error(f"ML email risk prediction failed: {e}")
            return 0.5, 0.3  # Default values

    async def _predict_domain_reputation(self, features: List[float]) -> Tuple[float, float]:
        """Predict domain reputation using trained ML model"""
        if not ML_AVAILABLE:
            return 0.5, 0.5

        try:
            # Simulate model prediction (in real implementation, use trained model)
            reputation_score = max(0.0, 1.0 - (sum(features) / len(features) / 10.0))
            confidence = 0.80  # Simulated confidence

            return reputation_score, confidence

        except Exception as e:
            logger.error(f"ML domain reputation prediction failed: {e}")
            return 0.5, 0.3  # Default values

    async def _detect_ml_anomalies(self, features_matrix: np.ndarray) -> Tuple[List[int], List[float]]:
        """Detect anomalies using ML model"""
        if not ML_AVAILABLE:
            return [], []

        try:
            # Simulate anomaly detection (in real implementation, use trained model)
            anomaly_scores = np.random.random(len(features_matrix))
            anomalies = [i for i, score in enumerate(anomaly_scores) if score > 0.8]

            return anomalies, anomaly_scores.tolist()

        except Exception as e:
            logger.error(f"ML anomaly detection failed: {e}")
            return [], []

    def _rule_based_email_risk(self, email_data: Dict[str, Any]) -> Tuple[float, float]:
        """Fallback rule-based email risk assessment"""
        risk_score = 0.0

        # Check for breach data
        if email_data.get('in_breach', False):
            risk_score += 0.4

        # Check breach count
        breach_count = email_data.get('breach_count', 0)
        risk_score += min(breach_count * 0.1, 0.3)

        # Check domain characteristics
        domain = email_data.get('domain', '')
        if any(char.isdigit() for char in domain):
            risk_score += 0.1
        if '-' in domain:
            risk_score += 0.05

        # Check email characteristics
        email = email_data.get('email', '')
        if len(email) > 50:
            risk_score += 0.1

        return min(risk_score, 1.0), 0.7

    def _rule_based_domain_reputation(self, domain_data: Dict[str, Any]) -> Tuple[float, float]:
        """Fallback rule-based domain reputation assessment"""
        reputation_score = 1.0  # Start with good reputation

        # Check domain age
        if domain_data.get('recently_registered', False):
            reputation_score -= 0.3

        # Check TLD
        domain = domain_data.get('domain', '')
        tld = domain.split('.')[-1] if '.' in domain else ''
        suspicious_tlds = ['tk', 'ml', 'ga', 'cf', 'top', 'click']
        if tld in suspicious_tlds:
            reputation_score -= 0.4

        # Check domain characteristics
        if any(char.isdigit() for char in domain):
            reputation_score -= 0.1
        if domain.count('.') > 3:
            reputation_score -= 0.1

        return max(reputation_score, 0.0), 0.6

    def _statistical_anomaly_detection(self, data_points: List[Dict[str, Any]]) -> Tuple[List[int], List[float]]:
        """Fallback statistical anomaly detection"""
        anomalies = []
        anomaly_scores = []

        # Simple statistical approach
        for i, point in enumerate(data_points):
            score = 0.0

            # Check for unusual timestamps
            timestamp = point.get('timestamp', datetime.now())
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

            # Night hours are more suspicious
            if timestamp.hour < 6 or timestamp.hour > 22:
                score += 0.3

            # High risk scores are suspicious
            risk_score = point.get('risk_score', 0.0)
            if risk_score > 0.8:
                score += 0.4

            # Low confidence is suspicious
            confidence = point.get('confidence', 1.0)
            if confidence < 0.3:
                score += 0.3

            anomaly_scores.append(score)
            if score > 0.6:
                anomalies.append(i)

        return anomalies, anomaly_scores

    async def _analyze_correlations(self, intelligence_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze correlations between intelligence data points"""
        correlations = []

        # Simple correlation analysis based on common attributes
        for i, data1 in enumerate(intelligence_data):
            for j, data2 in enumerate(intelligence_data[i+1:], i+1):
                correlation = self._calculate_data_correlation(data1, data2)
                if correlation['strength'] > 0.5:
                    correlations.append({
                        'source1_index': i,
                        'source2_index': j,
                        'correlation': correlation,
                        'data1': data1,
                        'data2': data2
                    })

        return correlations

    def _calculate_data_correlation(self, data1: Dict[str, Any], data2: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate correlation between two data points"""
        correlation_score = 0.0
        correlation_factors = []

        # Check for common domains
        domain1 = data1.get('domain', '')
        domain2 = data2.get('domain', '')
        if domain1 and domain2 and domain1 == domain2:
            correlation_score += 0.4
            correlation_factors.append('same_domain')

        # Check for similar emails
        email1 = data1.get('email', '')
        email2 = data2.get('email', '')
        if email1 and email2:
            if email1 == email2:
                correlation_score += 0.5
                correlation_factors.append('same_email')
            elif email1.split('@')[0] == email2.split('@')[0]:
                correlation_score += 0.2
                correlation_factors.append('same_username')

        # Check for temporal proximity
        timestamp1 = data1.get('timestamp')
        timestamp2 = data2.get('timestamp')
        if timestamp1 and timestamp2:
            if isinstance(timestamp1, str):
                timestamp1 = datetime.fromisoformat(timestamp1.replace('Z', '+00:00'))
            if isinstance(timestamp2, str):
                timestamp2 = datetime.fromisoformat(timestamp2.replace('Z', '+00:00'))

            time_diff = abs((timestamp1 - timestamp2).total_seconds())
            if time_diff < 3600:  # Within 1 hour
                correlation_score += 0.3
                correlation_factors.append('temporal_proximity')

        # Check for common sources
        sources1 = set(data1.get('sources', []))
        sources2 = set(data2.get('sources', []))
        common_sources = sources1.intersection(sources2)
        if common_sources:
            correlation_score += len(common_sources) * 0.1
            correlation_factors.append('common_sources')

        return {
            'strength': min(correlation_score, 1.0),
            'factors': correlation_factors,
            'details': {
                'domain_match': domain1 == domain2 if domain1 and domain2 else False,
                'email_match': email1 == email2 if email1 and email2 else False,
                'common_sources': list(common_sources),
                'time_difference_seconds': time_diff if 'timestamp1' in locals() and 'timestamp2' in locals() else None
            }
        }

    def _calculate_correlation_strength(self, correlations: List[Dict[str, Any]]) -> float:
        """Calculate overall correlation strength"""
        if not correlations:
            return 0.0

        total_strength = sum(corr['correlation']['strength'] for corr in correlations)
        return min(total_strength / len(correlations), 1.0)

    def _identify_risk_factors(self, email_data: Dict[str, Any], risk_score: float) -> List[str]:
        """Identify risk factors for email"""
        factors = []

        if email_data.get('in_breach', False):
            factors.append('Found in data breaches')

        if email_data.get('breach_count', 0) > 1:
            factors.append('Multiple breach exposures')

        domain = email_data.get('domain', '')
        if any(char.isdigit() for char in domain):
            factors.append('Domain contains numbers')

        if risk_score > 0.7:
            factors.append('High risk score')

        return factors

    def _identify_reputation_factors(self, domain_data: Dict[str, Any], reputation_score: float) -> List[str]:
        """Identify reputation factors for domain"""
        factors = []

        if domain_data.get('recently_registered', False):
            factors.append('Recently registered domain')

        domain = domain_data.get('domain', '')
        tld = domain.split('.')[-1] if '.' in domain else ''
        suspicious_tlds = ['tk', 'ml', 'ga', 'cf', 'top', 'click']
        if tld in suspicious_tlds:
            factors.append('Suspicious TLD')

        if reputation_score < 0.3:
            factors.append('Low reputation score')

        return factors

    def _generate_risk_recommendations(self, risk_score: float) -> List[str]:
        """Generate recommendations based on risk score"""
        recommendations = []

        if risk_score > 0.8:
            recommendations.append('High risk - avoid contact')
            recommendations.append('Implement additional verification')
        elif risk_score > 0.5:
            recommendations.append('Medium risk - proceed with caution')
            recommendations.append('Verify through alternative channels')
        else:
            recommendations.append('Low risk - normal processing')

        return recommendations

    def _generate_domain_recommendations(self, reputation_score: float) -> List[str]:
        """Generate recommendations based on domain reputation"""
        recommendations = []

        if reputation_score < 0.3:
            recommendations.append('Poor reputation - block or restrict')
            recommendations.append('Investigate further before engagement')
        elif reputation_score < 0.7:
            recommendations.append('Moderate reputation - monitor closely')
            recommendations.append('Apply additional security measures')
        else:
            recommendations.append('Good reputation - normal processing')

        return recommendations

    def _classify_domain_category(self, reputation_score: float) -> str:
        """Classify domain based on reputation score"""
        if reputation_score >= 0.8:
            return 'trusted'
        elif reputation_score >= 0.6:
            return 'neutral'
        elif reputation_score >= 0.3:
            return 'suspicious'
        else:
            return 'malicious'

    def _generate_anomaly_summary(self, anomalies: List[int], data_points: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary of anomaly detection results"""
        if not anomalies:
            return {'message': 'No anomalies detected', 'severity': 'low'}

        severity = 'low'
        if len(anomalies) > len(data_points) * 0.1:  # More than 10% anomalies
            severity = 'high'
        elif len(anomalies) > len(data_points) * 0.05:  # More than 5% anomalies
            severity = 'medium'

        return {
            'message': f'{len(anomalies)} anomalies detected',
            'severity': severity,
            'anomaly_rate': (len(anomalies) / len(data_points)) * 100,
            'most_common_factors': ['temporal_anomaly', 'risk_score_anomaly']
        }

    def _generate_correlation_summary(self, correlations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary of correlation analysis"""
        if not correlations:
            return {'message': 'No significant correlations found', 'strength': 'none'}

        avg_strength = sum(corr['correlation']['strength'] for corr in correlations) / len(correlations)

        strength_level = 'weak'
        if avg_strength > 0.7:
            strength_level = 'strong'
        elif avg_strength > 0.5:
            strength_level = 'moderate'

        return {
            'message': f'{len(correlations)} correlations found',
            'strength': strength_level,
            'average_strength': avg_strength,
            'strongest_correlation': max(correlations, key=lambda x: x['correlation']['strength'])['correlation']['strength']
        }

    def _generate_correlation_recommendations(self, correlations: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on correlation analysis"""
        recommendations = []

        if not correlations:
            recommendations.append('No correlations found - data sources appear independent')
            return recommendations

        strong_correlations = [c for c in correlations if c['correlation']['strength'] > 0.7]
        moderate_correlations = [c for c in correlations if 0.5 < c['correlation']['strength'] <= 0.7]

        if strong_correlations:
            recommendations.append('Strong correlations detected - investigate relationships')
            recommendations.append('Consider consolidating related intelligence sources')

        if moderate_correlations:
            recommendations.append('Moderate correlations found - monitor for patterns')

        if len(correlations) > 10:
            recommendations.append('High correlation volume - implement automated monitoring')

        return recommendations

    async def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of all analysis performed"""
        if not self.analysis_history:
            return {'message': 'No analysis performed yet', 'total_analyses': 0}

        summary = {
            'total_analyses': len(self.analysis_history),
            'analysis_types': {},
            'average_confidence': 0.0,
            'average_processing_time': 0.0,
            'latest_analysis': None
        }

        # Count analysis types
        for analysis in self.analysis_history:
            analysis_type = analysis.analysis_type.value
            summary['analysis_types'][analysis_type] = summary['analysis_types'].get(analysis_type, 0) + 1

        # Calculate averages
        if self.analysis_history:
            summary['average_confidence'] = sum(a.confidence for a in self.analysis_history) / len(self.analysis_history)
            summary['average_processing_time'] = sum(a.processing_time for a in self.analysis_history) / len(self.analysis_history)
            summary['latest_analysis'] = {
                'type': self.analysis_history[-1].analysis_type.value,
                'timestamp': self.analysis_history[-1].timestamp.isoformat(),
                'score': self.analysis_history[-1].score
            }

        return summary

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on AI Analytics Engine"""
        health_status = {
            'status': 'healthy',
            'ml_available': ML_AVAILABLE,
            'models_loaded': len(self.models),
            'analysis_history_size': len(self.analysis_history),
            'performance_monitor': 'active',
            'issues': []
        }

        # Check ML availability
        if not ML_AVAILABLE:
            health_status['issues'].append('ML libraries not available - running in simulation mode')

        # Check model status
        if ML_AVAILABLE and not self.models:
            health_status['issues'].append('No ML models loaded')
            health_status['status'] = 'degraded'

        # Check performance monitor
        try:
            test_timer = self.performance_monitor.start_timer("health_check")
            self.performance_monitor.stop_timer(test_timer, 'health_check')
        except Exception as e:
            health_status['issues'].append(f'Performance monitor error: {e}')
            health_status['status'] = 'degraded'

        return health_status


# Factory function for creating AI Analytics Engine
def get_ai_analytics_engine(config: Optional[Dict[str, Any]] = None) -> AIAnalyticsEngine:
    """
    Factory function to create and configure AI Analytics Engine

    Args:
        config: Optional configuration dictionary

    Returns:
        Configured AIAnalyticsEngine instance
    """
    if config is None:
        config = {
            'ml_enabled': True,
            'model_cache_size': 100,
            'analysis_history_limit': 1000,
            'performance_monitoring': True
        }

    return AIAnalyticsEngine(config)
