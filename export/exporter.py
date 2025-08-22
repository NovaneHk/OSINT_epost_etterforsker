"""
Data Export Module
Export processed leads to various formats with compliance features
"""

import csv
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd

from core.config import ConfigManager
from core.database import DatabaseManager

logger = logging.getLogger(__name__)

class DataExporter:
    """Export leads to various formats with compliance features."""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.db_manager = DatabaseManager()
        self.rules_config = config_manager.load_rules()

    def export_leads(self, formats: List[str], output_dir: str = "out",
                    include_audit: bool = True, compliance_mode: bool = True,
                    segment: Optional[str] = None, min_score: int = 0) -> Dict[str, Any]:
        """Export leads to specified formats."""

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Get leads data
        leads_data = self._prepare_leads_data(min_score, segment)

        if not leads_data:
            logger.warning("No leads data to export")
            return {}

        results = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        logger.info(f"Exporting {len(leads_data)} leads to {len(formats)} format(s)")

        for format_type in formats:
            try:
                if format_type.lower() == 'csv':
                    result = self._export_csv(leads_data, output_path, timestamp, compliance_mode)
                elif format_type.lower() == 'jsonl':
                    result = self._export_jsonl(leads_data, output_path, timestamp, compliance_mode)
                elif format_type.lower() == 'excel':
                    result = self._export_excel(leads_data, output_path, timestamp, compliance_mode)
                elif format_type.lower() == 'hubspot':
                    result = self._export_hubspot_format(leads_data, output_path, timestamp)
                elif format_type.lower() == 'mailerlite':
                    result = self._export_mailerlite_format(leads_data, output_path, timestamp)
                else:
                    logger.warning(f"Unknown export format: {format_type}")
                    continue

                results[format_type] = result
                logger.info(f"Successfully exported to {format_type}: {result['file_path']}")

            except Exception as e:
                logger.error(f"Error exporting to {format_type}: {e}")
                results[format_type] = {'error': str(e)}

        # Export audit log if requested
        if include_audit:
            audit_result = self._export_audit_log(output_path, timestamp)
            results['audit_log'] = audit_result

        return results

    def _prepare_leads_data(self, min_score: int = 0, segment: Optional[str] = None) -> List[Dict[str, Any]]:
        """Prepare leads data for export with all necessary fields."""

        # Get emails with company information
        emails = self.db_manager.get_emails(min_score=min_score)

        if not emails:
            return []

        # Prepare comprehensive lead data
        leads_data = []

        for email_record in emails:
            # Apply segment filtering if specified
            if segment and not self._matches_segment(email_record, segment):
                continue

            lead_data = {
                # Core email information
                'email': email_record.get('email', ''),
                'role': email_record.get('role', ''),
                'confidence': email_record.get('confidence', 0.0),
                'final_score': email_record.get('final_score', 0),

                # Company information
                'company_name': email_record.get('company_name', ''),
                'domain': email_record.get('domain', ''),
                'industry': email_record.get('industry', ''),
                'country': email_record.get('country', ''),

                # Validation information
                'validation_status': email_record.get('validation_status', 'unknown'),
                'mx_valid': email_record.get('mx_valid', False),
                'deliverable': email_record.get('deliverable', False),
                'risk_score': email_record.get('risk_score', 0),

                # Source information
                'source_url': email_record.get('source_url', ''),
                'source_type': email_record.get('source_type', ''),
                'extracted_at': email_record.get('extracted_at', ''),

                # Context information
                'context': email_record.get('context', ''),

                # Compliance information
                'legal_basis': 'legitimate_interest',
                'collection_purpose': 'b2b_marketing',
                'privacy_policy_url': self.rules_config.get('compliance_settings', {}).get('privacy_policy_url', ''),
                'opt_out_available': True,
                'data_controller': 'Your Company Name'
            }

            leads_data.append(lead_data)

        return leads_data

    def _matches_segment(self, email_record: Dict[str, Any], segment: str) -> bool:
        """Check if email record matches the specified segment."""

        segment_lower = segment.lower()

        # Define segment matching logic
        if 'high-score' in segment_lower:
            return email_record.get('final_score', 0) >= 80
        elif 'medium-score' in segment_lower:
            return 60 <= email_record.get('final_score', 0) < 80
        elif 'low-score' in segment_lower:
            return email_record.get('final_score', 0) < 60
        elif 'validated' in segment_lower:
            return email_record.get('validation_status') == 'valid'
        elif 'technical' in segment_lower:
            return 'tech' in email_record.get('role', '').lower()
        elif 'executive' in segment_lower:
            return any(term in email_record.get('role', '').lower() for term in ['ceo', 'cto', 'cfo', 'president'])
        elif 'procurement' in segment_lower:
            return 'procurement' in email_record.get('role', '').lower()

        return True  # Default: include all

    def _export_csv(self, leads_data: List[Dict[str, Any]], output_path: Path,
                   timestamp: str, compliance_mode: bool) -> Dict[str, Any]:
        """Export leads to CSV format."""

        filename = f"leads_{timestamp}.csv"
        file_path = output_path / filename

        # Define CSV columns
        csv_columns = [
            'email', 'role', 'confidence', 'final_score',
            'company_name', 'domain', 'industry', 'country',
            'validation_status', 'mx_valid', 'deliverable', 'risk_score',
            'source_url', 'source_type', 'extracted_at'
        ]

        if compliance_mode:
            csv_columns.extend([
                'legal_basis', 'collection_purpose', 'privacy_policy_url',
                'opt_out_available', 'data_controller'
            ])

        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns)

            # Write compliance header if enabled
            if compliance_mode:
                csvfile.write("# GDPR Compliant B2B Lead Export\n")
                csvfile.write(f"# Generated: {datetime.now().isoformat()}\n")
                csvfile.write("# Legal Basis: Legitimate Interest (Article 6(1)(f) GDPR)\n")
                csvfile.write("# Purpose: B2B Marketing and Lead Generation\n")
                csvfile.write("# Data Controller: Your Company Name\n")
                csvfile.write("# Opt-out: Contact privacy@yourcompany.com\n")
                csvfile.write("#\n")

            writer.writeheader()

            for lead in leads_data:
                # Filter data to include only specified columns
                filtered_lead = {col: lead.get(col, '') for col in csv_columns}
                writer.writerow(filtered_lead)

        return {
            'file_path': str(file_path),
            'record_count': len(leads_data),
            'format': 'csv',
            'compliance_mode': compliance_mode
        }

    def _export_jsonl(self, leads_data: List[Dict[str, Any]], output_path: Path,
                     timestamp: str, compliance_mode: bool) -> Dict[str, Any]:
        """Export leads to JSONL format."""

        filename = f"leads_{timestamp}.jsonl"
        file_path = output_path / filename

        with open(file_path, 'w', encoding='utf-8') as jsonlfile:
            # Write metadata header if compliance mode
            if compliance_mode:
                metadata = {
                    "_metadata": {
                        "export_type": "gdpr_compliant_b2b_leads",
                        "generated_at": datetime.now().isoformat(),
                        "legal_basis": "legitimate_interest",
                        "purpose": "b2b_marketing",
                        "data_controller": "Your Company Name",
                        "opt_out_contact": "privacy@yourcompany.com",
                        "record_count": len(leads_data)
                    }
                }
                jsonlfile.write(json.dumps(metadata) + '\n')

            # Write lead records
            for lead in leads_data:
                # Structure data according to schema
                structured_lead = {
                    "lead": {
                        "email": lead.get('email', ''),
                        "role": lead.get('role', ''),
                        "confidence": lead.get('confidence', 0.0)
                    },
                    "company": {
                        "name": lead.get('company_name', ''),
                        "domain": lead.get('domain', ''),
                        "industry": lead.get('industry', ''),
                        "country": lead.get('country', '')
                    },
                    "source": {
                        "url": lead.get('source_url', ''),
                        "type": lead.get('source_type', ''),
                        "retrieved_at": lead.get('extracted_at', '')
                    },
                    "validation": {
                        "status": lead.get('validation_status', 'unknown'),
                        "mx_valid": lead.get('mx_valid', False),
                        "deliverable": lead.get('deliverable', False),
                        "risk_score": lead.get('risk_score', 0)
                    },
                    "scoring": {
                        "final_score": lead.get('final_score', 0)
                    }
                }

                if compliance_mode:
                    structured_lead["compliance"] = {
                        "legal_basis": lead.get('legal_basis', 'legitimate_interest'),
                        "collection_purpose": lead.get('collection_purpose', 'b2b_marketing'),
                        "opt_out_available": lead.get('opt_out_available', True),
                        "privacy_policy_url": lead.get('privacy_policy_url', '')
                    }

                jsonlfile.write(json.dumps(structured_lead) + '\n')

        return {
            'file_path': str(file_path),
            'record_count': len(leads_data),
            'format': 'jsonl',
            'compliance_mode': compliance_mode
        }

    def _export_excel(self, leads_data: List[Dict[str, Any]], output_path: Path,
                     timestamp: str, compliance_mode: bool) -> Dict[str, Any]:
        """Export leads to Excel format with multiple sheets."""

        filename = f"leads_{timestamp}.xlsx"
        file_path = output_path / filename

        # Create DataFrame
        df = pd.DataFrame(leads_data)

        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            # Main leads sheet
            df.to_excel(writer, sheet_name='Leads', index=False)

            # Summary sheet
            summary_data = self._generate_summary_stats(leads_data)
            summary_df = pd.DataFrame(list(summary_data.items()), columns=['Metric', 'Value'])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)

            # Compliance sheet if enabled
            if compliance_mode:
                compliance_info = {
                    'Legal Basis': 'Legitimate Interest (Article 6(1)(f) GDPR)',
                    'Purpose': 'B2B Marketing and Lead Generation',
                    'Data Controller': 'Your Company Name',
                    'Generated': datetime.now().isoformat(),
                    'Opt-out Contact': 'privacy@yourcompany.com',
                    'Data Retention': '90 days maximum',
                    'Rights': 'Access, Rectification, Erasure, Object'
                }
                compliance_df = pd.DataFrame(list(compliance_info.items()), columns=['Compliance Item', 'Details'])
                compliance_df.to_excel(writer, sheet_name='Compliance', index=False)

        return {
            'file_path': str(file_path),
            'record_count': len(leads_data),
            'format': 'excel',
            'compliance_mode': compliance_mode
        }

    def _export_hubspot_format(self, leads_data: List[Dict[str, Any]], output_path: Path, timestamp: str) -> Dict[str, Any]:
        """Export leads in HubSpot import format."""

        filename = f"hubspot_import_{timestamp}.csv"
        file_path = output_path / filename

        # HubSpot specific columns
        hubspot_columns = [
            'Email', 'First Name', 'Last Name', 'Company Name', 'Job Title',
            'Website', 'Country', 'Lead Source', 'Lead Score', 'Lifecycle Stage'
        ]

        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=hubspot_columns)
            writer.writeheader()

            for lead in leads_data:
                # Map our data to HubSpot format
                hubspot_lead = {
                    'Email': lead.get('email', ''),
                    'First Name': '',  # Not available from role-based emails
                    'Last Name': '',   # Not available from role-based emails
                    'Company Name': lead.get('company_name', ''),
                    'Job Title': lead.get('role', ''),
                    'Website': f"https://{lead.get('domain', '')}" if lead.get('domain') else '',
                    'Country': lead.get('country', ''),
                    'Lead Source': f"OSINT - {lead.get('source_type', 'unknown')}",
                    'Lead Score': lead.get('final_score', 0),
                    'Lifecycle Stage': 'lead'
                }
                writer.writerow(hubspot_lead)

        return {
            'file_path': str(file_path),
            'record_count': len(leads_data),
            'format': 'hubspot_csv'
        }

    def _export_mailerlite_format(self, leads_data: List[Dict[str, Any]], output_path: Path, timestamp: str) -> Dict[str, Any]:
        """Export leads in MailerLite import format."""

        filename = f"mailerlite_import_{timestamp}.csv"
        file_path = output_path / filename

        # MailerLite specific columns
        mailerlite_columns = [
            'email', 'name', 'company', 'role', 'country', 'source', 'score'
        ]

        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=mailerlite_columns)
            writer.writeheader()

            for lead in leads_data:
                # Map our data to MailerLite format
                mailerlite_lead = {
                    'email': lead.get('email', ''),
                    'name': lead.get('role', ''),  # Use role as name for B2B
                    'company': lead.get('company_name', ''),
                    'role': lead.get('role', ''),
                    'country': lead.get('country', ''),
                    'source': lead.get('source_type', ''),
                    'score': lead.get('final_score', 0)
                }
                writer.writerow(mailerlite_lead)

        return {
            'file_path': str(file_path),
            'record_count': len(leads_data),
            'format': 'mailerlite_csv'
        }

    def _export_audit_log(self, output_path: Path, timestamp: str) -> Dict[str, Any]:
        """Export audit log for compliance."""

        filename = f"audit_log_{timestamp}.csv"
        file_path = output_path / filename

        # Get audit log from database
        audit_entries = self.db_manager.get_audit_log(limit=10000)

        if not audit_entries:
            logger.warning("No audit log entries to export")
            return {'file_path': str(file_path), 'record_count': 0}

        # Define audit log columns
        audit_columns = [
            'email', 'action', 'source_url', 'source_type',
            'legal_basis', 'purpose', 'timestamp', 'proof_note'
        ]

        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=audit_columns)

            # Write compliance header
            csvfile.write("# GDPR Compliance Audit Log\n")
            csvfile.write(f"# Generated: {datetime.now().isoformat()}\n")
            csvfile.write("# Purpose: Data Processing Audit Trail\n")
            csvfile.write("#\n")

            writer.writeheader()

            for entry in audit_entries:
                writer.writerow({
                    'email': entry.get('email', ''),
                    'action': entry.get('action', ''),
                    'source_url': entry.get('source_url', ''),
                    'source_type': entry.get('source_type', ''),
                    'legal_basis': entry.get('legal_basis', 'legitimate_interest'),
                    'purpose': entry.get('purpose', 'b2b_marketing'),
                    'timestamp': entry.get('timestamp', ''),
                    'proof_note': entry.get('proof_note', '')
                })

        return {
            'file_path': str(file_path),
            'record_count': len(audit_entries),
            'format': 'audit_csv'
        }

    def _generate_summary_stats(self, leads_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics for the export."""

        if not leads_data:
            return {}

        total_leads = len(leads_data)

        # Score distribution
        high_score = sum(1 for lead in leads_data if lead.get('final_score', 0) >= 80)
        medium_score = sum(1 for lead in leads_data if 60 <= lead.get('final_score', 0) < 80)
        low_score = sum(1 for lead in leads_data if lead.get('final_score', 0) < 60)

        # Validation status
        valid_emails = sum(1 for lead in leads_data if lead.get('validation_status') == 'valid')

        # Top roles
        role_counts = {}
        for lead in leads_data:
            role = lead.get('role', 'unknown')
            role_counts[role] = role_counts.get(role, 0) + 1

        top_role = max(role_counts.items(), key=lambda x: x[1])[0] if role_counts else 'unknown'

        return {
            'Total Leads': total_leads,
            'High Score (80+)': high_score,
            'Medium Score (60-79)': medium_score,
            'Low Score (<60)': low_score,
            'Valid Emails': valid_emails,
            'Validation Rate %': round((valid_emails / total_leads * 100), 1) if total_leads > 0 else 0,
            'Top Role': top_role,
            'Export Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }