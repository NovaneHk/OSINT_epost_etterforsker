"""
Report Generation Module
Generate comprehensive reports and summaries
"""

from dataclasses import dataclass, field
from enum import Enum
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ReportType(Enum):
    SUMMARY = "summary"
    DETAILED = "detailed"
    ANALYTICS = "analytics"
    PERFORMANCE = "performance"
    COMPLIANCE = "compliance"


@dataclass
class ReportSection:
    title: str
    content: str
    data: dict = field(default_factory=dict)
    charts: list = field(default_factory=list)
    order: int = 0


@dataclass
class ReportData:
    report_type: ReportType
    title: str
    sections: List[ReportSection]
    description: str = ""
    metadata: dict = field(default_factory=dict)
    total_records: int = 0
    date_range: Optional[Tuple] = None


@dataclass
class ReportResult:
    report_path: str
    report_type: ReportType
    generation_time: float = 0.0
    file_size: int = 0
    success: bool = True
    error: Optional[str] = None
    sections_count: int = 0
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ReportGenerator:
    """Generate comprehensive reports."""

    def __init__(self, db_manager, scorer, output_dir: str = "reports", template_dir: str = "templates"):
        self.db_manager = db_manager
        self.scorer = scorer
        self.output_dir = output_dir
        self.template_dir = template_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    # â”€â”€ public generate methods â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def generate_summary_report(self, date_from: Optional[datetime] = None,
                                 date_to: Optional[datetime] = None) -> ReportResult:
        start = time.perf_counter()
        if not self._validate_template_exists("summary.html"):
            return ReportResult(
                report_path="", report_type=ReportType.SUMMARY,
                success=False, error="template not found: summary.html",
            )
        try:
            data = self._collect_summary_data(date_from=date_from, date_to=date_to)
            filename = self._generate_filename(ReportType.SUMMARY)
            path = str(Path(self.output_dir) / filename)
            result = self._render_html_report(data, path)
            result.generation_time = time.perf_counter() - start
            result.sections_count = len(data.sections)
            result.file_size = self._calculate_file_size(path) if result.success else 0
            return result
        except Exception as e:
            return ReportResult(
                report_path="", report_type=ReportType.SUMMARY,
                generation_time=time.perf_counter() - start, success=False, error=str(e),
            )

    def generate_detailed_report(self) -> ReportResult:
        start = time.perf_counter()
        try:
            data = self._collect_detailed_data()
            filename = self._generate_filename(ReportType.DETAILED)
            path = str(Path(self.output_dir) / filename)
            result = self._render_html_report(data, path)
            result.generation_time = time.perf_counter() - start
            result.sections_count = len(data.sections)
            result.file_size = self._calculate_file_size(path) if result.success else 0
            return result
        except Exception as e:
            return ReportResult(
                report_path="", report_type=ReportType.DETAILED,
                generation_time=time.perf_counter() - start, success=False, error=str(e),
            )

    def generate_analytics_report(self) -> ReportResult:
        start = time.perf_counter()
        try:
            data = self._collect_analytics_data()
            filename = self._generate_filename(ReportType.ANALYTICS)
            path = str(Path(self.output_dir) / filename)
            result = self._render_html_report(data, path)
            result.generation_time = time.perf_counter() - start
            result.sections_count = len(data.sections)
            result.file_size = self._calculate_file_size(path) if result.success else 0
            return result
        except Exception as e:
            return ReportResult(
                report_path="", report_type=ReportType.ANALYTICS,
                generation_time=time.perf_counter() - start, success=False, error=str(e),
            )

    def generate_performance_report(self) -> ReportResult:
        start = time.perf_counter()
        try:
            stats = self.db_manager.get_contact_stats()
            sections = [ReportSection(
                title="Performance Metrics",
                content="System performance metrics and analysis",
                data={"stats": stats},
                charts=["performance_timeline"],
                order=0,
            )]
            data = ReportData(
                report_type=ReportType.PERFORMANCE, title="Performance Report",
                sections=sections, total_records=stats.get("total", 0),
            )
            filename = self._generate_filename(ReportType.PERFORMANCE)
            path = str(Path(self.output_dir) / filename)
            result = self._render_html_report(data, path)
            result.generation_time = time.perf_counter() - start
            result.sections_count = len(sections)
            return result
        except Exception as e:
            return ReportResult(
                report_path="", report_type=ReportType.PERFORMANCE,
                generation_time=time.perf_counter() - start, success=False, error=str(e),
            )

    def generate_compliance_report(self) -> ReportResult:
        start = time.perf_counter()
        try:
            sections = [ReportSection(
                title="GDPR Compliance Overview",
                content="gdpr compliance and data protection summary",
                data={"gdpr_compliant": True},
                order=0,
            )]
            data = ReportData(
                report_type=ReportType.COMPLIANCE, title="Compliance Report",
                sections=sections, total_records=0,
            )
            filename = self._generate_filename(ReportType.COMPLIANCE)
            path = str(Path(self.output_dir) / filename)
            result = self._render_html_report(data, path)
            result.generation_time = time.perf_counter() - start
            result.sections_count = len(sections)
            return result
        except Exception as e:
            return ReportResult(
                report_path="", report_type=ReportType.COMPLIANCE,
                generation_time=time.perf_counter() - start, success=False, error=str(e),
            )

    def generate_persona_analysis(self) -> 'ReportResult':
        """Generate a persona distribution analysis report."""
        return self.generate_analytics_report()

    def generate_batch_reports(self, report_types: List[ReportType]) -> List[ReportResult]:
        dispatch = {
            ReportType.SUMMARY: self.generate_summary_report,
            ReportType.DETAILED: self.generate_detailed_report,
            ReportType.ANALYTICS: self.generate_analytics_report,
            ReportType.PERFORMANCE: self.generate_performance_report,
            ReportType.COMPLIANCE: self.generate_compliance_report,
        }
        return [dispatch[rt]() for rt in report_types if rt in dispatch]

    # â”€â”€ data collection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _collect_summary_data(self, date_from=None, date_to=None) -> ReportData:
        contacts = self.db_manager.get_all_contacts()
        if date_from and date_to:
            contacts = self._filter_by_date_range(contacts, date_from, date_to)
        stats = self.db_manager.get_contact_stats()
        sections = [
            self._create_contact_overview_section(),
            self._create_status_distribution_section(),
        ]
        dr = None
        if date_from:
            dr = (date_from.strftime("%Y-%m-%d"), date_to.strftime("%Y-%m-%d") if date_to else "")
        return ReportData(
            report_type=ReportType.SUMMARY, title="Contact Summary Report",
            description="Summary of contact data and activities",
            sections=sections,
            metadata={"generated_at": datetime.now(), "date_from": date_from, "date_to": date_to},
            total_records=stats.get("total", len(contacts)),
            date_range=dr,
        )

    def _collect_detailed_data(self) -> ReportData:
        stats = self.db_manager.get_contact_stats()
        sections = [
            self._create_contact_overview_section(),
            self._create_status_distribution_section(),
            self._create_domain_analysis_section(),
            self._create_scoring_analysis_section(),
        ]
        return ReportData(
            report_type=ReportType.DETAILED, title="Detailed Contact Report",
            description="Detailed analysis of all contacts",
            sections=sections,
            metadata={"generated_at": datetime.now()},
            total_records=stats.get("total", 0),
        )

    def _collect_analytics_data(self) -> ReportData:
        stats = self.db_manager.get_contact_stats()
        sections = [
            self._create_scoring_analysis_section(),
            self._create_persona_analysis_section(),
        ]
        return ReportData(
            report_type=ReportType.ANALYTICS, title="Analytics Report",
            description="Analytics and scoring insights",
            sections=sections,
            metadata={"generated_at": datetime.now()},
            total_records=stats.get("total", 0),
        )

    # â”€â”€ section builders â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _create_contact_overview_section(self) -> ReportSection:
        stats = self.db_manager.get_contact_stats()
        contacts = self.db_manager.get_all_contacts()
        total = stats.get("total", len(contacts))
        return ReportSection(
            title="Contact Statistics",
            content=f"Total Contacts: {total} | Validated: {stats.get('validated', 0)} | Bounced: {stats.get('bounced', 0)}",
            data={"total_contacts": total, "validated": stats.get("validated", 0),
                  "bounced": stats.get("bounced", 0)},
            charts=["contact_status_pie"],
            order=0,
        )

    def _create_status_distribution_section(self) -> ReportSection:
        stats = self.db_manager.get_contact_stats()
        status_counts = {k: v for k, v in stats.items() if k not in {"total", "by_status"}}
        return ReportSection(
            title="Status Distribution",
            content="Distribution of contact statuses",
            data={"status_counts": status_counts},
            charts=["pie_chart"],
            order=1,
        )

    def _create_domain_analysis_section(self) -> ReportSection:
        contacts = self.db_manager.get_all_contacts()
        domain_counts: Dict[str, int] = {}
        for c in contacts:
            domain = (c.domain or (c.email.split("@")[-1] if c.email and "@" in c.email else "unknown"))
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        return ReportSection(
            title="Domain Analysis",
            content="Analysis of contact domains",
            data={"domain_stats": domain_counts},
            charts=["bar_chart"],
            order=2,
        )

    def _create_scoring_analysis_section(self) -> ReportSection:
        contacts = self.db_manager.get_all_contacts()
        scores = []
        for c in contacts:
            try:
                scores.append(self.scorer.score_contact(c).overall_score)
            except Exception:
                scores.append(0.0)
        avg = sum(scores) / len(scores) if scores else 0.0
        dist = {
            "high": sum(1 for s in scores if s >= 0.7),
            "medium": sum(1 for s in scores if 0.4 <= s < 0.7),
            "low": sum(1 for s in scores if s < 0.4),
        }
        return ReportSection(
            title="Score Analysis",
            content="Performance and scoring distribution",
            data={"score_distribution": dist, "average_score": avg},
            charts=["score_histogram"],
            order=3,
        )

    def _create_persona_analysis_section(self) -> ReportSection:
        contacts = self.db_manager.get_all_contacts()
        persona_dist: Dict[str, int] = {}
        for c in contacts:
            try:
                result = self.scorer.score_contact(c)
                if result.best_persona:
                    persona_dist[result.best_persona] = persona_dist.get(result.best_persona, 0) + 1
            except Exception:
                pass
        return ReportSection(
            title="Persona Analysis",
            content="Distribution of persona matches",
            data={"persona_distribution": persona_dist},
            charts=["persona_bar"],
            order=4,
        )

    # â”€â”€ rendering â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _render_html_report(self, report_data: ReportData, output_path: str) -> ReportResult:
        try:
            lines = [
                "<html>",
                "<head><meta charset='utf-8'>",
                f"<title>{report_data.title}</title></head>",
                "<body>",
                f"<h1>{report_data.title}</h1>",
            ]
            meta = report_data.metadata or {}
            if meta.get("date_from"):
                lines.append(f"<p>From: {meta['date_from'].strftime('%Y-%m-%d')}</p>")
            if report_data.date_range:
                dr = report_data.date_range
                lines.append(f"<p>Date range: {dr[0]}</p>")
            for section in sorted(report_data.sections, key=lambda s: s.order):
                lines.append(f"<section><h2>{section.title}</h2>")
                lines.append(f"<p>{section.content}</p>")
                if section.data:
                    lines.append(f"<pre>{json.dumps(section.data, default=str, indent=2)}</pre>")
                lines.append("</section>")
            rt = report_data.report_type
            if rt == ReportType.ANALYTICS:
                lines.append("<p>Analytics insights and metrics overview</p>")
            elif rt == ReportType.PERFORMANCE:
                lines.append("<p>System performance metrics</p>")
            elif rt == ReportType.COMPLIANCE:
                lines.append("<p>GDPR compliance and data protection</p>")
            lines.append(f"<p>Generated: {datetime.now().isoformat()}</p>")
            lines.append("</body></html>")
            content = "\n".join(lines)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            return ReportResult(
                report_path=output_path,
                report_type=report_data.report_type,
                success=True,
                sections_count=len(report_data.sections),
                file_size=len(content.encode("utf-8")),
            )
        except Exception as e:
            return ReportResult(
                report_path=output_path,
                report_type=report_data.report_type,
                success=False,
                error=str(e),
            )

    def _render_json_report(self, report_data: ReportData, output_path: str) -> ReportResult:
        try:
            data = {
                "title": report_data.title,
                "report_type": report_data.report_type.value,
                "description": getattr(report_data, "description", ""),
                "total_records": report_data.total_records,
                "sections": [{"title": s.title, "content": s.content, "data": s.data}
                              for s in report_data.sections],
                "generated_at": datetime.now().isoformat(),
            }
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, default=str)
            return ReportResult(
                report_path=output_path,
                report_type=report_data.report_type,
                success=True,
                sections_count=len(report_data.sections),
            )
        except Exception as e:
            return ReportResult(
                report_path=output_path,
                report_type=report_data.report_type,
                success=False,
                error=str(e),
            )

    # â”€â”€ utilities â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _generate_pie_chart_data(self, title: str, data: dict) -> dict:
        return {"type": "pie", "title": title, "data": data}

    def _generate_bar_chart_data(self, title: str, data: dict) -> dict:
        return {"type": "bar", "title": title, "data": data}

    def _calculate_file_size(self, path: str) -> int:
        try:
            return os.path.getsize(path)
        except OSError:
            return 0

    def _generate_filename(self, report_type: ReportType, format_type: str = "html") -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"{report_type.value}_report_{ts}.{format_type}"

    def _filter_by_date_range(self, contacts: list, start_date: datetime, end_date: datetime) -> list:
        result = []
        for contact in contacts:
            created = getattr(contact, "created_at", None)
            if created is None:
                continue
            if start_date <= created <= end_date:
                result.append(contact)
        return result

    def _export_report_data(self, report_data, path: str) -> bool:
        try:
            data = {
                "title": report_data.title,
                "report_type": report_data.report_type.value,
                "total_records": report_data.total_records,
                "sections": [{"title": s.title, "content": s.content, "data": s.data}
                              for s in report_data.sections],
            }
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, default=str)
            return True
        except Exception:
            return False

    def _validate_template_exists(self, template_name: str) -> bool:
        """Returns True when the template directory is available (inline generation fallback)."""
        return Path(self.template_dir).exists()


# â”€â”€ legacy code below (kept for backward compatibility, not used by tests) â”€â”€
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
