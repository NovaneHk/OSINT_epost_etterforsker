"""
Email Extraction Module
Advanced email extraction with role classification and context analysis
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from core.config import ConfigManager
from core.database import DatabaseManager

logger = logging.getLogger(__name__)

@dataclass
class EmailMatch:
    """Data class for email extraction results."""
    email: str
    role: str
    confidence: float
    context: str
    source_element: str
    company_id: Optional[int] = None

class EmailExtractor:
    """Advanced email extraction with role classification."""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.db_manager = DatabaseManager()
        self.role_patterns = self._build_role_patterns()
        self.negative_patterns = self._build_negative_patterns()

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
                        # Store in database
                        email_data = {
                            'email': match.email,
                            'role': match.role,
                            'confidence': match.confidence,
                            'context': match.context,
                            'company_id': match.company_id,
                            'source_url': company.get('url', ''),
                            'source_type': company.get('source_type', 'unknown'),
                            'extracted_at': datetime.now().isoformat()
                        }

                        self.db_manager.store_email(email_data)
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
        """Extract emails with surrounding context and role classification."""

        matches = []

        for role_type, pattern in self.role_patterns.items():
            for match in pattern.finditer(html_content):
                email = match.group()

                # Skip if matches negative patterns
                if self._matches_negative_patterns(email):
                    continue

                # Extract surrounding context (200 chars before and after)
                start_pos = max(0, match.start() - 200)
                end_pos = min(len(html_content), match.end() + 200)
                context = html_content[start_pos:end_pos]

                # Analyze context for confidence scoring
                confidence = self._calculate_confidence(email, role_type, context)

                # Determine source element (if within specific HTML elements)
                source_element = self._identify_source_element(html_content, match.start())

                matches.append(EmailMatch(
                    email=email,
                    role=role_type,
                    confidence=confidence,
                    context=context.strip(),
                    source_element=source_element,
                    company_id=company_id
                ))

        return self._deduplicate_matches(matches)

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

    def _calculate_confidence(self, email: str, role_type: str, context: str) -> float:
        """Calculate confidence score for email-role match."""

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

        # Role-specific confidence adjustments
        local_part = email.split('@')[0].lower()

        if role_type == 'executive':
            exec_terms = ['ceo', 'cto', 'cfo', 'president', 'director']
            if any(term in local_part for term in exec_terms):
                confidence += 0.3
        elif role_type == 'technical':
            tech_terms = ['tech', 'dev', 'engineering', 'it']
            if any(term in local_part for term in tech_terms):
                confidence += 0.2
        elif role_type == 'support':
            support_terms = ['support', 'help', 'contact', 'service']
            if any(term in local_part for term in support_terms):
                confidence += 0.2
        elif role_type == 'procurement':
            proc_terms = ['procurement', 'purchasing', 'sourcing', 'buyer']
            if any(term in local_part for term in proc_terms):
                confidence += 0.3

        # HTML structure confidence boost
        if '<a href="mailto:' in context:
            confidence += 0.1  # Properly formatted mailto link

        return max(0.0, min(1.0, confidence))

    def _identify_source_element(self, html_content: str, position: int) -> str:
        """Identify the HTML element containing the email."""

        # Look backwards and forwards from position to find HTML tags
        before_content = html_content[:position]
        after_content = html_content[position:]

        # Find the most recent opening tag before the email
        tag_match = re.search(r'<(\w+)[^>]*>(?!.*<\w+[^>]*>)', before_content[::-1])
        if tag_match:
            return tag_match.group(1)[::-1]  # Reverse the tag name back

        return 'unknown'

    def _deduplicate_matches(self, matches: List[EmailMatch]) -> List[EmailMatch]:
        """Remove duplicate email matches, keeping the highest confidence."""

        email_dict = {}

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