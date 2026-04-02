"""
Lead Scoring Module
Advanced scoring system for email lead quality assessment
"""

from dataclasses import dataclass, field
import logging
import math
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from core.config import ConfigManager
from core.database import DatabaseManager, Contact, ContactStatus

logger = logging.getLogger(__name__)


@dataclass
class PersonaMatch:
    persona_id: str
    match_score: float
    matched_criteria: List[str] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: Optional[str] = None


@dataclass
class ScoreComponent:
    name: str
    score: float
    weight: float
    description: str = ""
    details: dict = field(default_factory=dict)


@dataclass
class ScoreResult:
    contact_email: str
    overall_score: float
    confidence: float = 0.0
    domain_score: float = 0.0
    role_score: float = 0.0
    company_score: float = 0.0
    persona_matches: List[PersonaMatch] = field(default_factory=list)
    best_persona: Optional[str] = None
    score_components: List[ScoreComponent] = field(default_factory=list)
    calculation_time: float = 0.0
    scoring_version: str = "1.0"
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


# backward compat
ScoringResult = ScoreResult


class LeadScorer:
    """Advanced scoring system for email lead quality."""

    FREE_EMAIL_PROVIDERS = {
        'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'live.com',
        'aol.com', 'icloud.com', 'mail.com', 'protonmail.com', 'zoho.com',
        'ymail.com', 'msn.com', 'yandex.com', 'gmx.com'
    }

    ROLE_SCORES = {
        'cto': 1.0, 'ceo': 1.0, 'cfo': 0.9, 'coo': 0.9, 'president': 0.95,
        'vp': 0.85, 'vice president': 0.85, 'director': 0.8,
        'vp engineering': 1.0, 'vice president engineering': 1.0,
        'head of': 0.8, 'chief': 0.9,
        'manager': 0.6, 'lead': 0.65, 'senior': 0.55,
        'software engineer': 0.7, 'engineer': 0.6,
        'procurement': 0.75, 'purchasing': 0.7, 'buyer': 0.65,
        'tech lead': 0.8, 'tech': 0.5,
        'student': 0.1, 'intern': 0.15, 'janitor': 0.05,
        'assistant': 0.2, 'admin': 0.3,
    }

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.db_manager = DatabaseManager()
        self.rules_config = config_manager.load_rules()
        self.personas_config = config_manager.load_personas()
        self.scoring_weights = self.rules_config.get('processing_rules', {}).get('scoring_weights', {
            'persona_match': 0.4,
            'domain_quality': 0.25,
            'role_relevance': 0.20,
            'email_validity': 0.15
        })
        self.personas = self.personas_config.get('personas', {})
        # backward compat
        self.default_weights = self.scoring_weights

    def score_contact(self, contact: Contact) -> ScoreResult:
        """Score a single contact and return a ScoreResult."""
        start_time = time.perf_counter()

        persona_matches = self._score_persona_matches(contact)
        domain_comp = self._score_domain_quality(contact)
        role_comp = self._score_role_relevance(contact)
        validity_comp = self._score_email_validity(contact)

        # Build persona_match component
        best_pm = max(persona_matches, key=lambda m: m.match_score, default=None)
        persona_score = best_pm.match_score if best_pm else 0.0
        persona_comp = ScoreComponent(
            name="persona_match",
            score=persona_score,
            weight=self.scoring_weights.get('persona_match', 0.4),
            description="Persona alignment score",
        )

        components = [persona_comp, domain_comp, role_comp, validity_comp]
        overall_score = self._calculate_overall_score(components)
        confidence = self._calculate_confidence(contact, components)
        best_persona = best_pm.persona_id if best_pm and best_pm.match_score >= 0.2 else None

        calculation_time = time.perf_counter() - start_time
        return ScoreResult(
            contact_email=contact.email,
            overall_score=overall_score,
            confidence=confidence,
            domain_score=domain_comp.score,
            role_score=role_comp.score,
            company_score=persona_score,
            persona_matches=persona_matches,
            best_persona=best_persona,
            score_components=components,
            calculation_time=calculation_time,
        )

    def _score_persona_matches(self, contact: Contact) -> List[PersonaMatch]:
        """Score contact against all personas."""
        matches = []
        for persona_id, persona in self.personas.items():
            matched_criteria, match_score = self._match_persona_criteria(contact, persona)
            confidence = min(1.0, match_score * 1.1)
            reasoning = f"Matched {len(matched_criteria)} criteria" if matched_criteria else "No match"
            matches.append(PersonaMatch(
                persona_id=persona_id,
                match_score=match_score,
                matched_criteria=matched_criteria,
                confidence=confidence,
                reasoning=reasoning,
            ))
        return matches

    def _match_persona_criteria(self, contact: Contact, persona: dict):
        """Match contact against a single persona, return (matched_criteria, score)."""
        matched = []
        score = 0.0
        role = (contact.role or "").strip()
        email = (contact.email or "").lower()

        local_part = email.split('@')[0] if '@' in email else email

        # Role matching
        for target_role in persona.get('roles', []):
            if target_role.lower() in role.lower():
                matched.append(target_role)
                score += 0.6

        # Email pattern matching
        for pattern in persona.get('email_patterns', []):
            pat = pattern.replace('@', '').lower()
            if pat in local_part:
                matched.append(pattern)
                score += 0.35

        if local_part:
            normalized_role = role.lower().replace(' ', '').replace('-', '')
            normalized_local = local_part.lower().replace('.', '').replace('-', '')
            if normalized_role and normalized_local and normalized_role in normalized_local:
                matched.append(f"{local_part}@")
                score += 0.2
            elif any(token in normalized_local for token in ('cto', 'ceo', 'cfo', 'coo', 'vp', 'director', 'engineer', 'procurement', 'buyer')):
                matched.append(f"{local_part}@")
                score += 0.2

        # Negative signals — penalize
        for neg in persona.get('negative_signals', []):
            if neg.lower().replace('@', '') in email.split('@')[0]:
                score -= 0.25
                break

        score = max(0.0, min(1.0, score))
        return matched, score

    def _score_domain_quality(self, contact: Contact) -> ScoreComponent:
        """Score email domain quality."""
        domain = (contact.domain or contact.email.split('@')[-1] if contact.email else "").lower()
        is_free = domain in self.FREE_EMAIL_PROVIDERS
        domain_type = self._get_domain_type(domain)

        if is_free:
            score = 0.3
        elif domain_type == "educational":
            score = 0.6
        elif domain_type == "government":
            score = 0.7
        elif domain_type == "organization":
            score = 0.65
        else:
            score = 0.75

        return ScoreComponent(
            name="domain_quality",
            score=score,
            weight=self.scoring_weights.get('domain_quality', 0.25),
            description="Domain reputation score",
            details={"domain_type": domain_type, "is_free_provider": is_free, "domain": domain},
        )

    def _score_role_relevance(self, contact: Contact) -> ScoreComponent:
        """Score role relevance for B2B leads."""
        role = (contact.role or "").lower().strip()
        score = 0.25  # default for unknown role

        for key, val in self.ROLE_SCORES.items():
            if key in role:
                score = val
                break

        return ScoreComponent(
            name="role_relevance",
            score=score,
            weight=self.scoring_weights.get('role_relevance', 0.20),
            description="Role relevance for B2B leads",
            details={"role": role},
        )

    def _score_email_validity(self, contact: Contact) -> ScoreComponent:
        """Score email validity based on confidence and status."""
        confidence = contact.confidence_score or 0.5
        status = contact.status

        if status == ContactStatus.VALIDATED:
            score = min(1.0, confidence * 1.0 + 0.1)
        elif status == ContactStatus.BOUNCED:
            score = max(0.0, confidence * 0.2)
        elif status == ContactStatus.OPTED_OUT:
            score = 0.1
        elif status == ContactStatus.INVALID:
            score = 0.0
        elif status == ContactStatus.CONTACTED:
            score = min(1.0, confidence * 0.9)
        else:
            score = confidence * 0.6

        return ScoreComponent(
            name="email_validity",
            score=score,
            weight=self.scoring_weights.get('email_validity', 0.15),
            description="Email validity and confidence",
            details={"confidence": confidence, "status": str(status)},
        )

    def _calculate_overall_score(self, components: List[ScoreComponent]) -> float:
        """Calculate weighted overall score from components."""
        return sum(c.score * c.weight for c in components)

    def _calculate_confidence(self, contact: Contact, components: List[ScoreComponent]) -> float:
        """Calculate confidence in the scoring result."""
        base_confidence = 0.3

        # Data completeness bonus
        if contact.name:
            base_confidence += 0.15
        if contact.role:
            base_confidence += 0.15
        if contact.company:
            base_confidence += 0.1

        # Contact's own confidence score
        base_confidence += (contact.confidence_score or 0.0) * 0.2

        # Score consistency (higher scores = more confidence)
        avg_score = sum(c.score for c in components) / len(components) if components else 0
        base_confidence += avg_score * 0.1

        return max(0.0, min(1.0, base_confidence))

    def _is_business_domain(self, domain: str) -> bool:
        """Check if domain is a business domain (not free provider)."""
        return domain.lower() not in self.FREE_EMAIL_PROVIDERS

    def _get_domain_type(self, domain: str) -> str:
        """Classify domain type."""
        d = domain.lower()
        if d in self.FREE_EMAIL_PROVIDERS:
            return "free_provider"
        if d.endswith('.edu') or 'university' in d or 'college' in d:
            return "educational"
        if d.endswith('.gov'):
            return "government"
        if d.endswith('.org') or d.endswith('.ngo') or d.endswith('.charity'):
            return "organization"
        return "business"

    def score_contacts_batch(self, contacts: List[Contact]) -> List[ScoreResult]:
        """Score multiple contacts in batch."""
        return [self.score_contact(c) for c in contacts]

    def get_score_explanation(self, result: ScoreResult) -> dict:
        """Return a human-readable explanation of a score result."""
        component_info = [
            {"name": c.name, "score": c.score, "weight": c.weight, "weighted": c.score * c.weight}
            for c in result.score_components
        ]
        reasoning = (
            f"Overall score {result.overall_score:.2f} based on "
            + ", ".join(f"{c['name']}={c['score']:.2f}" for c in component_info)
        )
        if result.best_persona:
            reasoning += f". Best persona: {result.best_persona}"
        return {
            "overall_score": result.overall_score,
            "confidence": result.confidence,
            "best_persona": result.best_persona,
            "components": component_info,
            "reasoning": reasoning,
        }

    def update_scoring_weights(self, new_weights: Dict[str, float]) -> None:
        """Update scoring weights. Raises ValueError if they don't sum to 1.0."""
        total = sum(new_weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Scoring weights must sum to 1.0, got {total:.3f}")
        self.scoring_weights = dict(new_weights)
        self.default_weights = self.scoring_weights

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
        """Score all leads in the contacts table and persist results."""

        contacts = self.db_manager.get_all_contacts()

        total_leads = 0
        high_quality_leads = 0
        score_distribution = {'high': 0, 'medium': 0, 'low': 0}

        logger.info(f"Starting scoring of {len(contacts)} contacts")

        for contact in contacts:
            try:
                result = self.score_contact(contact)

                # Persist scored fields back to the contacts table
                contact.overall_score = result.overall_score
                contact.persona_match = result.best_persona
                self.db_manager.add_contact(contact)  # upsert

                score_pct = result.overall_score * 100
                total_leads += 1
                if score_pct >= min_score:
                    high_quality_leads += 1

                if score_pct >= 80:
                    score_distribution['high'] += 1
                elif score_pct >= 60:
                    score_distribution['medium'] += 1
                else:
                    score_distribution['low'] += 1

                if total_leads % 100 == 0:
                    logger.info(f"Scored {total_leads}/{len(contacts)} contacts")

            except Exception as e:
                logger.error(f"Error scoring contact {getattr(contact, 'email', 'unknown')}: {e}")
                total_leads += 1

        logger.info(f"Scoring completed. {high_quality_leads}/{total_leads} leads above threshold")

        return {
            'total_leads': total_leads,
            'high_quality_leads': high_quality_leads,
            'quality_rate': (high_quality_leads / total_leads * 100) if total_leads > 0 else 0,
            'score_distribution': score_distribution,
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