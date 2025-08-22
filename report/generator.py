"""
Report Generation Module
Generate comprehensive reports and summaries
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from jinja2 import Template
import json

from core.config import ConfigManager
from core.database import DatabaseManager

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generate comprehensive reports and summaries."""

    def __init__(self, config_manager: ConfigManager, db_manager: DatabaseManager):
        self.config_manager = config_manager
        self.db_manager = db_manager

    def generate_summary_report(self, include_stats: bool = True,
                               include_recommendations: bool = True) -> str:
        """Generate a comprehensive summary report."""

        # Collect all statistics
        stats = self._collect_comprehensive_stats()

        # Generate recommendations
        recommendations = []
        if include_recommendations:
            recommendations = self._generate_recommendations(stats)

        # Create report template
        report_template = self._get_report_template()

        # Render report
        template = Template(report_template)
        report_content = template.render(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            stats=stats,
            recommendations=recommendations,
            include_stats=include_stats,
            include_recommendations=include_recommendations
        )

        return report_content

    def _collect_comprehensive_stats(self) -> Dict[str, Any]:
        """Collect comprehensive statistics from all modules."""

        stats = {}

        # Database statistics
        db_stats = self.db_manager.get_statistics()
        stats['database'] = db_stats

        # Email statistics
        emails = self.db_manager.get_emails(min_score=0)
        stats['emails'] = self._analyze_email_stats(emails)

        # Company statistics
        companies = self.db_manager.get_companies()
        stats['companies'] = self._analyze_company_stats(companies)

        # Performance statistics
        stats['performance'] = self._calculate_performance_stats(emails, companies)

        # Quality statistics
        stats['quality'] = self._calculate_quality_stats(emails)

        return stats

    def _analyze_email_stats(self, emails: list) -> Dict[str, Any]:
        """Analyze email statistics."""

        if not emails:
            return {'total': 0}

        total_emails = len(emails)

        # Score distribution
        high_score = sum(1 for e in emails if e.get('final_score', 0) >= 80)
        medium_score = sum(1 for e in emails if 60 <= e.get('final_score', 0) < 80)
        low_score = sum(1 for e in emails if e.get('final_score', 0) < 60)

        # Validation status
        valid_emails = sum(1 for e in emails if e.get('validation_status') == 'valid')
        invalid_emails = sum(1 for e in emails if e.get('validation_status') == 'invalid')
        risky_emails = sum(1 for e in emails if e.get('validation_status') == 'risky')

        # Role distribution
        role_counts = {}
        for email in emails:
            role = email.get('role', 'unknown')
            role_counts[role] = role_counts.get(role, 0) + 1

        # Source distribution
        source_counts = {}
        for email in emails:
            source = email.get('source_type', 'unknown')
            source_counts[source] = source_counts.get(source, 0) + 1

        return {
            'total': total_emails,
            'score_distribution': {
                'high': high_score,
                'medium': medium_score,
                'low': low_score
            },
            'validation_status': {
                'valid': valid_emails,
                'invalid': invalid_emails,
                'risky': risky_emails,
                'validation_rate': round((valid_emails / total_emails * 100), 1) if total_emails > 0 else 0
            },
            'top_roles': sorted(role_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            'source_distribution': dict(sorted(source_counts.items(), key=lambda x: x[1], reverse=True))
        }

    def _analyze_company_stats(self, companies: list) -> Dict[str, Any]:
        """Analyze company statistics."""

        if not companies:
            return {'total': 0}

        total_companies = len(companies)

        # Industry distribution
        industry_counts = {}
        for company in companies:
            industry = company.get('industry', 'unknown')
            industry_counts[industry] = industry_counts.get(industry, 0) + 1

        # Country distribution
        country_counts = {}
        for company in companies:
            country = company.get('country', 'unknown')
            country_counts[country] = country_counts.get(country, 0) + 1

        # Source credibility
        credibility_scores = [c.get('credibility_score', 50) for c in companies]
        avg_credibility = sum(credibility_scores) / len(credibility_scores) if credibility_scores else 0

        return {
            'total': total_companies,
            'industry_distribution': dict(sorted(industry_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            'country_distribution': dict(sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            'average_credibility': round(avg_credibility, 1)
        }

    def _calculate_performance_stats(self, emails: list, companies: list) -> Dict[str, Any]:
        """Calculate performance statistics."""

        # Calculate processing rates
        total_companies = len(companies)
        total_emails = len(emails)

        # Email extraction rate
        extraction_rate = (total_emails / total_companies) if total_companies > 0 else 0

        # Data freshness
        recent_emails = 0
        if emails:
            cutoff_date = datetime.now() - timedelta(days=7)
            for email in emails:
                extracted_at = email.get('extracted_at')
                if extracted_at:
                    try:
                        email_date = datetime.fromisoformat(extracted_at.replace('Z', '+00:00'))
                        if email_date.replace(tzinfo=None) > cutoff_date:
                            recent_emails += 1
                    except:
                        pass

        freshness_rate = (recent_emails / total_emails * 100) if total_emails > 0 else 0

        return {
            'email_extraction_rate': round(extraction_rate, 2),
            'data_freshness_rate': round(freshness_rate, 1),
            'recent_emails_count': recent_emails,
            'processing_efficiency': 'High' if extraction_rate > 2 else 'Medium' if extraction_rate > 1 else 'Low'
        }

    def _calculate_quality_stats(self, emails: list) -> Dict[str, Any]:
        """Calculate quality statistics."""

        if not emails:
            return {'overall_quality': 'No data'}

        total_emails = len(emails)

        # Quality indicators
        high_confidence = sum(1 for e in emails if e.get('confidence', 0) >= 0.8)
        high_score = sum(1 for e in emails if e.get('final_score', 0) >= 80)
        validated = sum(1 for e in emails if e.get('validation_status') == 'valid')
        low_risk = sum(1 for e in emails if e.get('risk_score', 100) < 30)

        # Calculate overall quality score
        quality_factors = [
            high_confidence / total_emails,
            high_score / total_emails,
            validated / total_emails,
            low_risk / total_emails
        ]

        overall_quality_score = sum(quality_factors) / len(quality_factors) * 100

        # Determine quality level
        if overall_quality_score >= 80:
            quality_level = 'Excellent'
        elif overall_quality_score >= 60:
            quality_level = 'Good'
        elif overall_quality_score >= 40:
            quality_level = 'Fair'
        else:
            quality_level = 'Poor'

        return {
            'overall_quality_score': round(overall_quality_score, 1),
            'overall_quality': quality_level,
            'high_confidence_rate': round((high_confidence / total_emails * 100), 1),
            'high_score_rate': round((high_score / total_emails * 100), 1),
            'validation_rate': round((validated / total_emails * 100), 1),
            'low_risk_rate': round((low_risk / total_emails * 100), 1)
        }

    def _generate_recommendations(self, stats: Dict[str, Any]) -> list:
        """Generate actionable recommendations based on statistics."""

        recommendations = []

        # Email quality recommendations
        email_stats = stats.get('emails', {})
        validation_rate = email_stats.get('validation_status', {}).get('validation_rate', 0)

        if validation_rate < 70:
            recommendations.append({
                'category': 'Data Quality',
                'priority': 'High',
                'issue': 'Low email validation rate',
                'recommendation': 'Improve email extraction patterns and implement stricter validation rules',
                'impact': 'Better deliverability and reduced bounce rates'
            })

        # Score distribution recommendations
        score_dist = email_stats.get('score_distribution', {})
        high_score_count = score_dist.get('high', 0)
        total_emails = email_stats.get('total', 1)

        if high_score_count / total_emails < 0.3:
            recommendations.append({
                'category': 'Lead Quality',
                'priority': 'Medium',
                'issue': 'Low percentage of high-scoring leads',
                'recommendation': 'Refine targeting criteria and focus on higher-credibility sources',
                'impact': 'Improved conversion rates and ROI'
            })

        # Source diversity recommendations
        source_dist = email_stats.get('source_distribution', {})
        if len(source_dist) < 3:
            recommendations.append({
                'category': 'Source Diversity',
                'priority': 'Medium',
                'issue': 'Limited source diversity',
                'recommendation': 'Add more source types to reduce dependency and improve coverage',
                'impact': 'More comprehensive lead generation and reduced risk'
            })

        # Performance recommendations
        performance_stats = stats.get('performance', {})
        extraction_rate = performance_stats.get('email_extraction_rate', 0)

        if extraction_rate < 1.5:
            recommendations.append({
                'category': 'Performance',
                'priority': 'Low',
                'issue': 'Low email extraction rate',
                'recommendation': 'Optimize email extraction patterns and target more email-rich sources',
                'impact': 'Increased lead volume and better ROI'
            })

        # Data freshness recommendations
        freshness_rate = performance_stats.get('data_freshness_rate', 0)
        if freshness_rate < 50:
            recommendations.append({
                'category': 'Data Freshness',
                'priority': 'Medium',
                'issue': 'Significant amount of old data',
                'recommendation': 'Implement regular data refresh cycles and prioritize recent sources',
                'impact': 'More relevant leads and better engagement rates'
            })

        # If no issues found
        if not recommendations:
            recommendations.append({
                'category': 'Overall',
                'priority': 'Info',
                'issue': 'No major issues detected',
                'recommendation': 'Continue monitoring performance and consider expanding to new markets or personas',
                'impact': 'Sustained growth and optimization'
            })

        return recommendations

    def _get_report_template(self) -> str:
        """Get the report template."""

        return """
# OSINT B2B Email List Generation Report

**Generated:** {{ timestamp }}

---

## Executive Summary

{% if stats.emails.total > 0 %}
This report summarizes the performance of the OSINT B2B email list generation system. A total of **{{ stats.emails.total }}** email leads were processed from **{{ stats.companies.total }}** companies, achieving an overall quality score of **{{ stats.quality.overall_quality_score }}%** ({{ stats.quality.overall_quality }}).
{% else %}
No email data available for analysis.
{% endif %}

---

{% if include_stats %}
## Detailed Statistics

### Email Lead Statistics
- **Total Emails:** {{ stats.emails.total }}
- **Validation Rate:** {{ stats.emails.validation_status.validation_rate }}%
- **High Score Leads (80+):** {{ stats.emails.score_distribution.high }}
- **Medium Score Leads (60-79):** {{ stats.emails.score_distribution.medium }}
- **Low Score Leads (<60):** {{ stats.emails.score_distribution.low }}

### Validation Breakdown
- **Valid:** {{ stats.emails.validation_status.valid }}
- **Invalid:** {{ stats.emails.validation_status.invalid }}
- **Risky:** {{ stats.emails.validation_status.risky }}

### Top Roles Identified
{% for role, count in stats.emails.top_roles %}
- **{{ role }}:** {{ count }} leads
{% endfor %}

### Source Distribution
{% for source, count in stats.emails.source_distribution.items() %}
- **{{ source }}:** {{ count }} leads
{% endfor %}

### Company Statistics
- **Total Companies:** {{ stats.companies.total }}
- **Average Source Credibility:** {{ stats.companies.average_credibility }}

### Top Industries
{% for industry, count in stats.companies.industry_distribution.items() %}
- **{{ industry }}:** {{ count }} companies
{% endfor %}

### Geographic Distribution
{% for country, count in stats.companies.country_distribution.items() %}
- **{{ country }}:** {{ count }} companies
{% endfor %}

### Performance Metrics
- **Email Extraction Rate:** {{ stats.performance.email_extraction_rate }} emails per company
- **Data Freshness Rate:** {{ stats.performance.data_freshness_rate }}% (last 7 days)
- **Processing Efficiency:** {{ stats.performance.processing_efficiency }}

### Quality Metrics
- **Overall Quality Score:** {{ stats.quality.overall_quality_score }}%
- **High Confidence Rate:** {{ stats.quality.high_confidence_rate }}%
- **High Score Rate:** {{ stats.quality.high_score_rate }}%
- **Low Risk Rate:** {{ stats.quality.low_risk_rate }}%

---
{% endif %}

{% if include_recommendations %}
## Recommendations

{% for rec in recommendations %}
### {{ rec.category }} - {{ rec.priority }} Priority

**Issue:** {{ rec.issue }}

**Recommendation:** {{ rec.recommendation }}

**Expected Impact:** {{ rec.impact }}

---
{% endfor %}
{% endif %}

## Compliance Notes

- All data collection follows GDPR Article 6(1)(f) legitimate interest provisions
- Business email addresses only - no personal email collection
- Comprehensive audit trail maintained for all processing activities
- Automatic opt-out mechanisms available
- Data retention limited to 90 days maximum

## Next Steps

1. **Review Recommendations:** Implement high-priority recommendations first
2. **Monitor Performance:** Continue tracking key metrics weekly
3. **Quality Assurance:** Regular validation of email extraction patterns
4. **Compliance Review:** Monthly compliance audit and documentation update
5. **Optimization:** Continuous improvement based on performance data

---

*Report generated by OSINT B2B Email List Generation System*
*For questions or support, contact: support@yourcompany.com*
"""

    def export_json_report(self, output_path: str) -> Dict[str, Any]:
        """Export comprehensive statistics as JSON."""

        stats = self._collect_comprehensive_stats()
        recommendations = self._generate_recommendations(stats)

        report_data = {
            'generated_at': datetime.now().isoformat(),
            'statistics': stats,
            'recommendations': recommendations,
            'summary': {
                'total_emails': stats.get('emails', {}).get('total', 0),
                'total_companies': stats.get('companies', {}).get('total', 0),
                'overall_quality': stats.get('quality', {}).get('overall_quality', 'Unknown'),
                'validation_rate': stats.get('emails', {}).get('validation_status', {}).get('validation_rate', 0)
            }
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        return {
            'file_path': output_path,
            'record_count': len(report_data),
            'format': 'json'
        }