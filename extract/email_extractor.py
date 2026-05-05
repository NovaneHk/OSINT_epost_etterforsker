"""
Email Extraction Module
Advanced email extraction with role classification and context analysis
"""

import re
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from core.config import ConfigManager
from core.database import DatabaseManager

logger = logging.getLogger(__name__)

# ── New test-compatible dataclasses ──────────────────────────────────────────

@dataclass
class EmailMatch:
    """Data class for email extraction results (test-compatible API)."""
    email: str
    domain: str
    local_part: str
    role: Optional[str] = None
    context: Optional[str] = None
    position: int = 0
    confidence: float = 1.0
    match_type: str = "standard"
    company_id: Optional[int] = None
    source_element: Optional[str] = None

    def to_contact(self, source_url: str = "", company: str = "") -> "Any":
        """Convert to a Contact instance for storage in the contacts table."""
        from core.database import Contact, ContactStatus
        return Contact(
            email=self.email,
            domain=self.domain,
            name=None,
            role=self.role,
            company=company or None,
            confidence_score=self.confidence,
            source_url=source_url or None,
            source="crawler",
            status=ContactStatus.UNVALIDATED,
        )


@dataclass
class ExtractionResult:
    """Result of an extraction run."""
    source_url: str
    email_matches: List[EmailMatch] = field(default_factory=list)
    total_emails: int = 0
    unique_domains: Set[str] = field(default_factory=set)
    extraction_time: float = 0.0
    success: bool = True
    error: Optional[str] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


# ── Extractor ─────────────────────────────────────────────────────────────────

# Generic email pattern
_EMAIL_RE = re.compile(
    r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b'
)


class EmailExtractor:
    """Advanced email extraction with role classification."""

    def __init__(self,
                 min_confidence: float = 0.5,
                 max_context_chars: int = 100,
                 exclude_domains: Optional[Set[str]] = None,
                 exclude_patterns: Optional[List[str]] = None,
                 config_manager: Optional[ConfigManager] = None):
        self.min_confidence = min_confidence
        self.max_context_chars = max_context_chars
        self.exclude_domains: Set[str] = set(exclude_domains) if exclude_domains else set()
        self.exclude_patterns: List[re.Pattern] = (
            [re.compile(p) for p in exclude_patterns] if exclude_patterns else []
        )
        # Optional legacy support
        if config_manager is not None:
            self.config_manager = config_manager
            self.db_manager = DatabaseManager()
        self.role_patterns = self._build_role_patterns()
        self.negative_patterns = self._build_negative_patterns()

    # ── Public API (test-compatible) ─────────────────────────────────────────

    def extract_from_text(self, text: str, source_url: str = "") -> ExtractionResult:
        """Extract emails from plain text."""
        import time
        start = time.perf_counter()
        if text is None:
            return ExtractionResult(source_url=source_url, success=False, error="No content provided")
        try:
            matches = self._find_emails(text)
            elapsed = time.perf_counter() - start
            return ExtractionResult(
                source_url=source_url,
                email_matches=matches,
                total_emails=len(matches),
                unique_domains={m.domain for m in matches},
                extraction_time=elapsed,
                success=True,
            )
        except Exception as e:
            return ExtractionResult(
                source_url=source_url,
                success=False,
                error=str(e),
            )

    def extract_from_html(self, html: str, source_url: str = "") -> ExtractionResult:
        """Extract emails from HTML content."""
        import time
        if html is None:
            return ExtractionResult(source_url=source_url, success=False, error="No content provided")
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            text = f"{html} {soup.get_text(separator=' ')}"
        except Exception:
            text = html
        start = time.time()
        try:
            matches = self._find_emails(text)
            elapsed = time.time() - start
            return ExtractionResult(
                source_url=source_url,
                email_matches=matches,
                total_emails=len(matches),
                unique_domains={m.domain for m in matches},
                extraction_time=elapsed,
                success=True,
            )
        except Exception as e:
            return ExtractionResult(source_url=source_url, success=False, error=str(e))

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _find_emails(self, text: str) -> List[EmailMatch]:
        """Find all valid emails in text, applying filters."""
        results: List[EmailMatch] = []

        for m in _EMAIL_RE.finditer(text):
            email = m.group()
            if not self._is_valid_email(email):
                continue

            local, domain = email.split('@', 1)
            if domain.lower() in self.exclude_domains:
                continue

            if any(p.search(email) for p in self.exclude_patterns):
                continue

            context = self._extract_context(text, m.start(), m.end())
            confidence = self._calculate_confidence(email, context)
            role = self._detect_role(email, context)

            if confidence < self.min_confidence:
                continue

            results.append(EmailMatch(
                email=email,
                domain=domain.lower(),
                local_part=local,
                role=role,
                context=context,
                position=m.start(),
                confidence=confidence,
            ))

        return results

    def _calculate_confidence(self, email: str, context: Optional[str] = None) -> float:
        """Calculate confidence score for an email match."""
        score = 1.0
        local, domain = email.lower().split('@', 1)
        # Lower confidence for generic local parts
        generic = {'info', 'contact', 'support', 'admin', 'mail', 'hello', 'webmaster'}
        if local in generic:
            score -= 0.15
        if domain.split('.')[-1] in {'z'} or len(domain.split('.')[-1]) < 2:
            score -= 0.45
        if domain in {'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com'}:
            score -= 0.25
        if len(local) <= 1:
            score -= 0.2
        # Boost if context has business keywords
        if context:
            ctx_lower = context.lower()
            for kw in ('ceo', 'cto', 'manager', 'director', 'engineer', 'sales'):
                if kw in ctx_lower:
                    score = min(1.0, score + 0.05)
            for kw in ('personal', 'private', 'home', 'individual'):
                if kw in ctx_lower:
                    score -= 0.2
        return max(0.0, min(1.0, score))

    def _extract_context(self, text: str, start: int, end: int) -> str:
        """Extract surrounding context."""
        ctx_start = max(0, start - self.max_context_chars)
        ctx_end = min(len(text), end + self.max_context_chars)
        return text[ctx_start:ctx_end].strip()

    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation."""
        if not email or email.count('@') != 1:
            return False
        local, domain = email.split('@', 1)
        if not local or not domain or domain.startswith('.') or domain.endswith('.'):
            return False
        return bool(_EMAIL_RE.fullmatch(email))

    def _detect_role(self, email: str, context: Optional[str]) -> Optional[str]:
        """Infer a coarse role from the email local part or surrounding context."""
        local_part = email.split('@', 1)[0].lower()
        for role_name, pattern in self.role_patterns.items():
            if pattern.search(email):
                return role_name
        if context:
            ctx_lower = context.lower()
            for role_name in self.role_patterns:
                if role_name in ctx_lower:
                    return role_name
        role_keywords = {
            'executive': {'ceo', 'cto', 'cfo', 'coo', 'chief', 'director', 'vp'},
            'technical': {'tech', 'engineering', 'dev', 'developer', 'architect'},
            'operations': {'ops', 'operations', 'admin'},
            'sales': {'sales', 'business', 'revenue'},
            'marketing': {'marketing', 'press', 'brand'},
            'support': {'support', 'help', 'service', 'contact', 'info'},
            'finance': {'finance', 'accounting', 'billing'},
            'hr': {'hr', 'careers', 'recruiting', 'talent'},
            'procurement': {'procurement', 'purchasing', 'buyer', 'sourcing'},
        }
        for role_name, keywords in role_keywords.items():
            if any(keyword in local_part for keyword in keywords):
                return role_name
        return None

    # ── Legacy compatibility (role-based extraction) ──────────────────────────

    def _build_role_patterns(self) -> Dict[str, re.Pattern]:
        """Build comprehensive role-based email patterns."""

        return {
            'executive': re.compile(
                r'\b(ceo|cto|cfo|coo|president|vp|vice\.president|director|head\.of|chief)@'
                r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
                re.IGNORECASE
            ),
            'technical': re.compile(
                r'\b(tech|engineering|dev|development|it|systems|architect|lead)@'
                r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
                re.IGNORECASE
            ),
            'operations': re.compile(
                r'\b(ops|operations|admin|office|facilities|logistics)@'
                r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
                re.IGNORECASE
            ),
            'sales': re.compile(
                r'\b(sales|business|commercial|partnerships|bd|revenue)@'
                r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
                re.IGNORECASE
            ),
            'marketing': re.compile(
                r'\b(marketing|pr|press|communications|brand|growth)@'
                r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
                re.IGNORECASE
            ),
            'support': re.compile(
                r'\b(support|help|service|customer|contact|info)@'
                r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
                re.IGNORECASE
            ),
            'finance': re.compile(
                r'\b(finance|accounting|billing|invoices|payments)@'
                r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
                re.IGNORECASE
            ),
            'hr': re.compile(
                r'\b(hr|human\.resources|careers|jobs|recruiting|talent)@'
                r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
                re.IGNORECASE
            ),
            'procurement': re.compile(
                r'\b(procurement|purchasing|sourcing|buyer|supply)@'
                r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
                re.IGNORECASE
            )
        }

    def _build_negative_patterns(self) -> List[re.Pattern]:
        """Build patterns for emails to exclude."""

        return [
            # Personal email patterns
            re.compile(r'\b[a-z]+\.[a-z]+@', re.IGNORECASE),  # firstname.lastname
            re.compile(r'\b[a-z]+[0-9]+@', re.IGNORECASE),    # name+numbers

            # Non-business roles
            re.compile(r'\b(no-reply|noreply|donotreply)@', re.IGNORECASE),
            re.compile(r'\b(newsletter|spam|abuse)@', re.IGNORECASE),

            # Educational/government exclusions
            re.compile(r'@.*\.edu$', re.IGNORECASE),
            re.compile(r'@.*\.gov$', re.IGNORECASE),

            # Temporary/disposable patterns
            re.compile(r'@(10minutemail|tempmail|guerrillamail)', re.IGNORECASE),

            # Consumer email providers
            re.compile(r'@(gmail|yahoo|hotmail|outlook|aol|icloud)\.', re.IGNORECASE)
        ]

    def extract_all_emails(self, min_confidence: float = 0.6,
                          role_based_only: bool = True,
                          context_analysis: bool = True) -> Dict[str, Any]:
        """Extract emails from all companies in database."""

        companies = self.db_manager.get_companies()
        total_emails = 0
        total_confidence = 0.0
        extracted_emails = []

        for company in companies:
            # Simulate HTML content for the company
            html_content = self._simulate_company_html(company)

            # Extract emails from simulated content
            email_matches = self.extract_emails_with_context(
                html_content,
                company.get('url', ''),
                company.get('id')
            )

            # Filter by confidence and role requirements
            for match in email_matches:
                if match.confidence >= min_confidence:
                    if not role_based_only or self._is_role_based_email(match.email):
                        # Store in contacts table via canonical bridge
                        contact = match.to_contact(
                            source_url=company.get('url', ''),
                            company=company.get('name', '')
                        )
                        self.db_manager.add_contact(contact)
                        extracted_emails.append(match)
                        total_emails += 1
                        total_confidence += match.confidence

        avg_confidence = total_confidence / total_emails if total_emails > 0 else 0

        return {
            'total_emails': total_emails,
            'avg_confidence': avg_confidence,
            'companies_processed': len(companies),
            'extracted_emails': extracted_emails
        }

    def extract_emails_with_context(self, html_content: str, source_url: str,
                                   company_id: Optional[int] = None) -> List[EmailMatch]:
        """Extract emails with surrounding context and role classification (legacy API)."""
        result = self.extract_from_html(html_content, source_url=source_url)
        return result.email_matches

    def _simulate_company_html(self, company: Dict[str, Any]) -> str:
        """Simulate HTML content for a company (for demonstration)."""

        company_name = company.get('name', 'Example Company')
        domain = company.get('domain', 'example.com')

        # Simulate realistic company HTML with various email patterns
        html_content = f"""
        <html>
        <head><title>{company_name}</title></head>
        <body>
            <div class="header">
                <h1>{company_name}</h1>
                <nav>
                    <a href="/about">About</a>
                    <a href="/contact">Contact</a>
                    <a href="/team">Team</a>
                </nav>
            </div>

            <div class="contact-section">
                <h2>Contact Information</h2>
                <p>For general inquiries: <a href="mailto:info@{domain}">info@{domain}</a></p>
                <p>Sales team: <a href="mailto:sales@{domain}">sales@{domain}</a></p>
                <p>Technical support: <a href="mailto:support@{domain}">support@{domain}</a></p>
                <p>Business partnerships: <a href="mailto:business@{domain}">business@{domain}</a></p>
            </div>

            <div class="team-section">
                <h2>Leadership Team</h2>
                <div class="team-member">
                    <h3>Chief Technology Officer</h3>
                    <p>Contact our CTO at: <a href="mailto:cto@{domain}">cto@{domain}</a></p>
                </div>
                <div class="team-member">
                    <h3>Head of Operations</h3>
                    <p>Operations inquiries: <a href="mailto:ops@{domain}">ops@{domain}</a></p>
                </div>
                <div class="team-member">
                    <h3>Procurement Manager</h3>
                    <p>Supplier relations: <a href="mailto:procurement@{domain}">procurement@{domain}</a></p>
                </div>
            </div>

            <div class="footer">
                <p>© 2024 {company_name}. All rights reserved.</p>
                <p>Press inquiries: <a href="mailto:press@{domain}">press@{domain}</a></p>
            </div>
        </body>
        </html>
        """

        return html_content

    def _matches_negative_patterns(self, email: str) -> bool:
        """Check if email matches any negative patterns."""

        for pattern in self.negative_patterns:
            if pattern.search(email):
                return True
        return False

    def _is_role_based_email(self, email: str) -> bool:
        """Check if email is role-based (not personal)."""

        local_part = email.split('@')[0].lower()

        # Common role-based prefixes
        role_prefixes = [
            'info', 'contact', 'sales', 'support', 'admin', 'office',
            'ceo', 'cto', 'cfo', 'coo', 'tech', 'engineering', 'dev',
            'ops', 'operations', 'marketing', 'pr', 'press', 'hr',
            'finance', 'accounting', 'procurement', 'purchasing'
        ]

        return any(prefix in local_part for prefix in role_prefixes)

    def _calculate_role_confidence(self, email: str, role_type: str, context: str) -> float:
        """Calculate confidence score for email-role match (legacy)."""

        confidence = 0.5  # Base confidence

        # Boost confidence based on context indicators
        business_indicators = ['company', 'business', 'corporate', 'office', 'team', 'department']
        for indicator in business_indicators:
            if indicator.lower() in context.lower():
                confidence += 0.1

        # Reduce confidence for personal indicators
        personal_indicators = ['personal', 'private', 'home', 'individual']
        for indicator in personal_indicators:
            if indicator.lower() in context.lower():
                confidence -= 0.2

        return max(0.0, min(1.0, confidence))

    def _identify_source_element(self, html_content: str, position: int) -> str:
        """Identify the HTML element containing the email."""

        before_content = html_content[:position]

        tag_match = re.search(r'<(\w+)[^>]*>(?!.*<\w+[^>]*>)', before_content[::-1])
        if tag_match:
            return tag_match.group(1)[::-1]

        return 'unknown'

    def _deduplicate_matches(self, matches: List[EmailMatch]) -> List[EmailMatch]:
        """Remove duplicate email matches, keeping the highest confidence."""

        email_dict: Dict[str, EmailMatch] = {}

        for match in matches:
            email = match.email.lower()
            if email not in email_dict or match.confidence > email_dict[email].confidence:
                email_dict[email] = match

        return list(email_dict.values())

    def get_extraction_statistics(self) -> Dict[str, Any]:
        """Get statistics about extracted emails."""

        stats = self.db_manager.get_statistics()

        # Add extraction-specific statistics
        with self.db_manager._get_connection() as conn:
            cursor = conn.cursor()

            # Role distribution
            cursor.execute('''
                SELECT role, COUNT(*)
                FROM emails
                GROUP BY role
                ORDER BY COUNT(*) DESC
            ''')
            role_distribution = dict(cursor.fetchall())

            # Confidence distribution
            cursor.execute('''
                SELECT
                    CASE
                        WHEN confidence >= 0.8 THEN 'high'
                        WHEN confidence >= 0.6 THEN 'medium'
                        ELSE 'low'
                    END as confidence_category,
                    COUNT(*)
                FROM emails
                GROUP BY confidence_category
            ''')
            confidence_distribution = dict(cursor.fetchall())

            stats.update({
                'role_distribution': role_distribution,
                'confidence_distribution': confidence_distribution
            })

        return stats