class ScoreResult:
    """Lightweight container for scoring results used in tests.

    Accepts arbitrary keyword arguments and sets them as attributes so tests
    can access fields like overall_score, confidence, best_persona, etc.
    """
    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class ScoreComponent:
    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class PersonaMatch:
    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
"""
Lead Scoring Module
Advanced scoring system for email lead quality assessment
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import math

# Placeholder kept for backward compatibility
class ScoringResult:
    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

from core.config import ConfigManager
from core.database import DatabaseManager

logger = logging.getLogger(__name__)

class LeadScorer:
    """Advanced scoring system for email lead quality."""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.db_manager = DatabaseManager()
        self.rules_config = config_manager.load_rules()
        self.personas_config = config_manager.load_personas()
        self.default_weights = self._get_default_weights()

    def _get_default_weights(self) -> Dict[str, float]:
        """Get default scoring weights from configuration."""

        return self.rules_config.get('processing_rules', {}).get('scoring_weights', {
            'persona_match': 0.35,
            'sector_relevance': 0.25,
            'geographic_preference': 0.20,
            'source_credibility': 0.15,
            'data_freshness': 0.05
        })

    def score_all_leads(self, min_score: int = 70, weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Score all leads in the database."""

        if weights is None:
            weights = self.default_weights

        # Validate weights sum to 1.0
        total_weight = sum(weights.values())
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"Weights sum to {total_weight}, normalizing to 1.0")
            weights = {k: v / total_weight for k, v in weights.items()}

        # Get all emails with company information
        emails = self.db_manager.get_emails(min_score=0)
        companies = {c['id']: c for c in self.db_manager.get_companies()}

        total_leads = 0
        high_quality_leads = 0
        score_distribution = {'high': 0, 'medium': 0, 'low': 0}

        logger.info(f"Starting scoring of {len(emails)} leads")

        for email_record in emails:
            try:
                # Get associated company data
                company_id = email_record.get('company_id')
                company_data = companies.get(company_id, {}) if company_id else {}

                # Calculate comprehensive score
                score = self.calculate_lead_score(email_record, company_data, weights)

                # Update database with score
                self.db_manager.update_email_score(email_record['id'], score)

                # Update statistics
                total_leads += 1
                if score >= min_score:
                    high_quality_leads += 1

                # Categorize score
                if score >= 80:
                    score_distribution['high'] += 1
                elif score >= 60:
                    score_distribution['medium'] += 1
                else:
                    score_distribution['low'] += 1

                if total_leads % 100 == 0:
                    logger.info(f"Scored {total_leads}/{len(emails)} leads")

            except Exception as e:
                logger.error(f"Error scoring lead {email_record.get('email', 'unknown')}: {e}")
                total_leads += 1

        logger.info(f"Scoring completed. {high_quality_leads}/{total_leads} leads above threshold")

        return {
            'total_leads': total_leads,
            'high_quality_leads': high_quality_leads,
            'quality_rate': (high_quality_leads / total_leads * 100) if total_leads > 0 else 0,
            'score_distribution': score_distribution,
            'weights_used': weights
        }

    def calculate_lead_score(self, email_data: Dict[str, Any], company_data: Dict[str, Any],
                           weights: Dict[str, float]) -> int:
        """Calculate comprehensive lead score (0-100)."""

        scores = {}

        # 1. Persona Match Score
        scores['persona_match'] = self._calculate_persona_score(email_data, company_data)

        # 2. Sector Relevance Score
        scores['sector_relevance'] = self._calculate_sector_score(company_data)

        # 3. Geographic Preference Score
        scores['geographic_preference'] = self._calculate_geographic_score(company_data)

        # 4. Source Credibility Score
        scores['source_credibility'] = self._calculate_source_credibility_score(email_data, company_data)

        # 5. Data Freshness Score
        scores['data_freshness'] = self._calculate_freshness_score(email_data)

        # Calculate weighted final score
        weighted_score = sum(
            scores[factor] * weights.get(factor, 0)
            for factor in scores
        )

        # Apply validation penalty
        validation_penalty = self._calculate_validation_penalty(email_data)
        final_score = weighted_score * (1 - validation_penalty)

        return round(max(0, min(100, final_score * 100)))

    def _calculate_persona_score(self, email_data: Dict[str, Any], company_data: Dict[str, Any]) -> float:
        """Score based on persona matching."""

        email = email_data.get('email', '')
        role = email_data.get('role', '')
        confidence = email_data.get('confidence', 0.0)

        if not email or not role:
            return 0.0

        # Get all personas for scoring
        personas = self.personas_config.get('personas', {})
        max_score = 0.0

        for persona_name, persona_config in personas.items():
            persona_score = 0.0

            # Check role matching
            target_roles = persona_config.get('roles', [])
            if any(target_role.lower() in role.lower() for target_role in target_roles):
                persona_score += 0.4

            # Check email pattern matching
            email_patterns = persona_config.get('email_patterns', [])
            local_part = email.split('@')[0].lower()
            if any(pattern.replace('@', '') in local_part for pattern in email_patterns):
                persona_score += 0.3

            # Check negative signals
            negative_signals = persona_config.get('negative_signals', [])
            if any(signal.lower() in role.lower() for signal in negative_signals):
                persona_score -= 0.3

            # Apply persona priority weight
            priority_weight = 1.0
            if persona_config.get('priority_level') == 'high':
                priority_weight = 1.2
            elif persona_config.get('priority_level') == 'low':
                priority_weight = 0.8

            persona_score *= priority_weight

            max_score = max(max_score, persona_score)

        # Factor in extraction confidence
        final_score = max_score * confidence

        return max(0.0, min(1.0, final_score))

    def _calculate_sector_score(self, company_data: Dict[str, Any]) -> float:
        """Score based on sector matching."""

        industry = company_data.get('industry', '').lower()
        technologies = company_data.get('technologies', [])

        if not industry and not technologies:
            return 0.5  # Neutral score for unknown sector

        # Get sector definitions from rules
        sector_definitions = self.rules_config.get('sector_definitions', {})
        max_score = 0.0

        for sector_name, sector_config in sector_definitions.items():
            sector_score = 0.0

            # Check industry keywords
            keywords = sector_config.get('keywords', [])
            keyword_matches = sum(1 for keyword in keywords if keyword.lower() in industry)
            if keyword_matches > 0:
                sector_score += min(0.5, keyword_matches * 0.2)

            # Check negative keywords
            negative_keywords = sector_config.get('negative_keywords', [])
            negative_matches = sum(1 for keyword in negative_keywords if keyword.lower() in industry)
            sector_score -= negative_matches * 0.2

            # Check technology signals
            tech_signals = sector_config.get('technology_signals', [])
            if technologies:
                tech_matches = sum(1 for tech in technologies if any(signal.lower() in tech.lower() for signal in tech_signals))
                sector_score += min(0.3, tech_matches * 0.1)

            # Apply sector multiplier
            multiplier = sector_config.get('scoring_multiplier', 1.0)
            sector_score *= multiplier

            max_score = max(max_score, sector_score)

        return max(0.0, min(1.0, max_score))

    def _calculate_geographic_score(self, company_data: Dict[str, Any]) -> float:
        """Score based on geographic preferences."""

        country = company_data.get('country', '').upper()
        domain = company_data.get('domain', '').lower()

        if not country and not domain:
            return 0.5  # Neutral score for unknown geography

        # Get geographic targeting from rules
        geographic_targeting = self.rules_config.get('geographic_targeting', {})
        max_score = 0.0

        for region_name, region_config in geographic_targeting.items():
            region_score = 0.0

            # Check country match
            target_countries = region_config.get('countries', [])
            if country in target_countries:
                region_score += 0.6

            # Check TLD preferences
            tld_preferences = region_config.get('tld_preferences', [])
            if any(domain.endswith(tld) for tld in tld_preferences):
                region_score += 0.4

            # Apply scoring boost
            scoring_boost = region_config.get('scoring_boost', 0) / 100
            region_score += scoring_boost

            max_score = max(max_score, region_score)

        return max(0.0, min(1.0, max_score))

    def _calculate_source_credibility_score(self, email_data: Dict[str, Any], company_data: Dict[str, Any]) -> float:
        """Score based on source credibility."""

        source_type = email_data.get('source_type', company_data.get('source_type', 'unknown'))
        credibility_score = company_data.get('credibility_score', 50)

        # Base credibility from source
        base_score = credibility_score / 100

        # Source type multipliers
        source_multipliers = {
            'directory': 1.0,
            'event': 1.1,  # Events often have higher quality
            'company_site': 1.2,  # Direct from company is most credible
            'unknown': 0.7
        }

        multiplier = source_multipliers.get(source_type, 0.8)
        final_score = base_score * multiplier

        return max(0.0, min(1.0, final_score))

    def _calculate_freshness_score(self, email_data: Dict[str, Any]) -> float:
        """Score based on data freshness."""

        extracted_at = email_data.get('extracted_at')
        if not extracted_at:
            return 0.5  # Neutral score for unknown date

        try:
            # Parse the timestamp
            if isinstance(extracted_at, str):
                extracted_date = datetime.fromisoformat(extracted_at.replace('Z', '+00:00'))
            else:
                extracted_date = extracted_at

            # Calculate age in days
            age_days = (datetime.now() - extracted_date.replace(tzinfo=None)).days

            # Freshness scoring curve (exponential decay)
            if age_days <= 7:
                return 1.0  # Perfect score for data less than a week old
            elif age_days <= 30:
                return 0.8  # Good score for data less than a month old
            elif age_days <= 90:
                return 0.6  # Acceptable score for data less than 3 months old
            elif age_days <= 180:
                return 0.4  # Lower score for data less than 6 months old
            else:
                return 0.2  # Minimal score for older data

        except Exception as e:
            logger.warning(f"Error parsing date {extracted_at}: {e}")
            return 0.5

    def _calculate_validation_penalty(self, email_data: Dict[str, Any]) -> float:
        """Calculate penalty based on validation results."""

        validation_status = email_data.get('validation_status', 'unknown')
        risk_score = email_data.get('risk_score', 0)
        mx_valid = email_data.get('mx_valid', False)

        penalty = 0.0

        # Status-based penalties
        if validation_status == 'invalid':
            penalty += 0.8  # Heavy penalty for invalid emails
        elif validation_status == 'risky':
            penalty += 0.4  # Moderate penalty for risky emails
        elif validation_status == 'unknown':
            penalty += 0.2  # Light penalty for unknown status

        # Risk score penalty
        penalty += (risk_score / 100) * 0.3

        # MX validation penalty
        if not mx_valid:
            penalty += 0.3

        return min(1.0, penalty)  # Cap penalty at 100%

    def get_scoring_insights(self, min_score: int = 70) -> Dict[str, Any]:
        """Get insights about scoring performance and recommendations."""

        emails = self.db_manager.get_emails(min_score=0)
        high_quality_emails = [e for e in emails if e.get('final_score', 0) >= min_score]

        insights = {
            'total_leads': len(emails),
            'high_quality_leads': len(high_quality_emails),
            'quality_rate': (len(high_quality_emails) / len(emails) * 100) if emails else 0
        }

        if high_quality_emails:
            # Analyze top performing characteristics
            top_roles = {}
            top_sources = {}
            top_domains = {}

            for email in high_quality_emails:
                role = email.get('role', 'unknown')
                source_type = email.get('source_type', 'unknown')
                domain = email.get('domain', 'unknown')

                top_roles[role] = top_roles.get(role, 0) + 1
                top_sources[source_type] = top_sources.get(source_type, 0) + 1
                top_domains[domain] = top_domains.get(domain, 0) + 1

            insights.update({
                'top_roles': sorted(top_roles.items(), key=lambda x: x[1], reverse=True)[:5],
                'top_sources': sorted(top_sources.items(), key=lambda x: x[1], reverse=True)[:5],
                'top_domains': sorted(top_domains.items(), key=lambda x: x[1], reverse=True)[:5]
            })

        # Generate recommendations
        recommendations = self._generate_recommendations(emails, high_quality_emails)
        insights['recommendations'] = recommendations

        return insights

    def _generate_recommendations(self, all_emails: List[Dict], high_quality_emails: List[Dict]) -> List[str]:
        """Generate recommendations for improving lead quality."""

        recommendations = []

        if not all_emails:
            return ["No leads available for analysis"]

        total_count = len(all_emails)
        high_quality_count = len(high_quality_emails)
        quality_rate = (high_quality_count / total_count * 100) if total_count > 0 else 0

        # Quality rate recommendations
        if quality_rate < 30:
            recommendations.append("Low quality rate detected. Consider refining source selection and targeting criteria.")
        elif quality_rate < 50:
            recommendations.append("Moderate quality rate. Focus on higher-credibility sources and better persona matching.")

        # Validation recommendations
        invalid_count = sum(1 for e in all_emails if e.get('validation_status') == 'invalid')
        if invalid_count > total_count * 0.2:
            recommendations.append("High invalid email rate. Improve email extraction patterns and validation processes.")

        # Source diversity recommendations
        source_types = set(e.get('source_type', 'unknown') for e in all_emails)
        if len(source_types) < 3:
            recommendations.append("Limited source diversity. Consider adding more source types for better coverage.")

        # Freshness recommendations
        old_data_count = sum(1 for e in all_emails if self._is_old_data(e.get('extracted_at')))
        if old_data_count > total_count * 0.3:
            recommendations.append("Significant amount of old data. Implement regular data refresh cycles.")

        if not recommendations:
            recommendations.append("Lead quality looks good. Continue monitoring and optimizing based on performance metrics.")

        return recommendations

    def _is_old_data(self, extracted_at) -> bool:
        """Check if data is considered old (>90 days)."""

        if not extracted_at:
            return True

        try:
            if isinstance(extracted_at, str):
                extracted_date = datetime.fromisoformat(extracted_at.replace('Z', '+00:00'))
            else:
                extracted_date = extracted_at

            age_days = (datetime.now() - extracted_date.replace(tzinfo=None)).days
            return age_days > 90

        except:
            return True