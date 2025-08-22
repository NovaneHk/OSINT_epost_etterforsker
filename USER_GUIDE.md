# OSINT B2B Email System - User Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [Command Reference](#command-reference)
6. [Workflow Guide](#workflow-guide)
7. [Best Practices](#best-practices)
8. [Compliance & Ethics](#compliance--ethics)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Usage](#advanced-usage)

## Introduction

The OSINT B2B Email System is a comprehensive, ethical lead generation tool designed for business-to-business marketing and research. It combines advanced web scraping, email extraction, validation, and scoring capabilities while maintaining strict compliance with GDPR and other privacy regulations.

### Key Features
- **Multi-source data collection** from business directories, events, and company websites
- **Advanced email extraction** with role-based classification
- **Comprehensive validation** including MX records and deliverability checks
- **Intelligent scoring** based on persona matching and sector relevance
- **Multiple export formats** (CSV, JSON, Excel, HubSpot, MailerLite)
- **GDPR compliance** with audit logging and data retention controls
- **Health monitoring** and performance analytics

### Legal & Ethical Usage
This system is designed for legitimate business purposes under GDPR Article 6(1)(f) - legitimate interest. Always ensure compliance with local privacy laws and respect robots.txt files.

## Installation

### Prerequisites
- Python 3.12 or higher
- Windows 10/11, macOS, or Linux
- 4GB RAM minimum (8GB recommended)
- 10GB free disk space

### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd OSINT_epost_etterforsker
```

### Step 2: Install Dependencies
```bash
pip install -r requirements_core.txt
```

### Step 3: Verify Installation
```bash
python test_system.py
```

You should see output confirming all system components are working correctly.

## Quick Start

### 1. Check System Health
```bash
python cli.py health-check
```

### 2. Generate Search Seeds
```bash
python cli.py seed --persona technical_leaders --sector technology --geo nordics
```

### 3. Run a Test Crawl (Dry Run)
```bash
python cli.py crawl --sources directories,events --dry-run --limit 100
```

### 4. View Configuration
```bash
python cli.py configure --show-config
```

## Configuration

The system uses three main configuration files in the `configs/` directory:

### `personas.yml` - Target Personas
Define the types of professionals you want to target:

```yaml
personas:
  technical_leaders:
    description: "Technical decision makers and engineering leaders"
    roles:
      - "CTO"
      - "Tech Lead"
      - "VP Engineering"
    email_patterns:
      - "cto@"
      - "tech@"
      - "engineering@"
    priority_level: "high"
    scoring_weight: 40
```

### `sources.yml` - Data Sources
Configure where to collect company data:

```yaml
source_categories:
  directories:
    priority: 1
    daily_limit: 1000
    sources:
      - name: "Norwegian Chamber of Commerce"
        url: "https://www.chamber.no/member-directory"
        credibility_score: 95
        enabled: true
```

### `rules.yml` - Processing Rules
Control validation, scoring, and compliance settings:

```yaml
processing_rules:
  validation_thresholds:
    min_confidence_score: 0.6
    require_mx_validation: true
  scoring_weights:
    persona_match: 0.35
    sector_relevance: 0.25
    geographic_preference: 0.20
```

## Command Reference

### `seed` - Generate Search Queries
Create targeted search queries for data collection.

```bash
python cli.py seed --persona PERSONA --sector SECTOR --geo GEOGRAPHY [options]
```

**Options:**
- `--output-limit`: Maximum leads to generate (default: 10000)
- `--sources`: Source types to use (default: "directories,events,sites")
- `--dry-run`: Preview queries without storing

**Example:**
```bash
python cli.py seed --persona procurement_specialists --sector manufacturing --geo dach --dry-run
```

### `crawl` - Collect Company Data
Execute web crawling to gather company information.

```bash
python cli.py crawl --sources SOURCES [options]
```

**Options:**
- `--concurrent-workers`: Number of parallel workers (default: 8)
- `--rate-limit`: Requests per second (default: 2.0)
- `--limit`: Maximum pages to crawl (default: 1000)
- `--dry-run`: Estimate crawling scope
- `--respect-robots`: Honor robots.txt (default: true)

**Example:**
```bash
python cli.py crawl --sources directories,events --limit 500 --rate-limit 1.5
```

### `extract` - Extract Email Addresses
Extract and classify email addresses from collected data.

```bash
python cli.py extract [options]
```

**Options:**
- `--min-confidence`: Minimum confidence score (default: 0.6)
- `--role-based-only`: Extract only role-based emails (default: true)
- `--context-analysis`: Enable context analysis (default: true)

### `validate` - Validate Email Addresses
Verify email addresses through multiple validation layers.

```bash
python cli.py validate [options]
```

**Options:**
- `--mx-check`: Perform MX record validation (default: true)
- `--smtp-probe`: Enable SMTP probing (use carefully!)
- `--dedupe-aggressive`: Aggressive deduplication (default: true)
- `--risk-assessment`: Perform risk assessment (default: true)

### `enrich` - Enhance Company Data
Add additional information to company records.

```bash
python cli.py enrich [options]
```

**Options:**
- `--enable-tech-fingerprinting`: Detect technologies (default: true)
- `--company-size-estimation`: Estimate company sizes (default: true)
- `--external-apis`: Use external APIs (default: false)

### `score` - Score Email Leads
Calculate quality scores for leads based on multiple factors.

```bash
python cli.py score [options]
```

**Options:**
- `--min-score`: Minimum score threshold (default: 70)
- `--persona-weight`: Persona matching weight % (default: 35)
- `--sector-weight`: Sector relevance weight % (default: 25)

### `export` - Export Processed Leads
Export leads to various formats for use in marketing tools.

```bash
python cli.py export --format FORMATS [options]
```

**Options:**
- `--format`: Export formats (csv,jsonl,excel,hubspot,mailerlite)
- `--output-dir`: Output directory (default: "out")
- `--include-audit-log`: Include compliance audit log (default: true)
- `--compliance-headers`: Add GDPR compliance headers (default: true)
- `--segment`: Export specific segment only

**Examples:**
```bash
python cli.py export --format csv,excel --output-dir results
python cli.py export --format hubspot --segment high-score
```

### `report` - Generate Summary Reports
Create comprehensive reports and analytics.

```bash
python cli.py report [options]
```

**Options:**
- `--include-statistics`: Include detailed statistics (default: true)
- `--recommendations`: Include recommendations (default: true)
- `--output-file`: Report file path (default: "out/summary_report.md")

### `health-check` - System Health Check
Perform comprehensive system health monitoring.

```bash
python cli.py health-check
```

### `configure` - System Configuration
View or modify system configuration.

```bash
python cli.py configure [options]
```

**Options:**
- `--show-config`: Display current configuration
- `--persona`: Set default persona
- `--sector`: Set default sector
- `--geo`: Set default geography
- `--rate-limit`: Set default rate limit

## Workflow Guide

### Complete Lead Generation Workflow

#### 1. Preparation Phase
```bash
# Check system health
python cli.py health-check

# Review configuration
python cli.py configure --show-config

# Set defaults (optional)
python cli.py configure --persona technical_leaders --sector technology --geo nordics
```

#### 2. Data Collection Phase
```bash
# Generate search seeds
python cli.py seed --persona technical_leaders --sector technology --geo nordics

# Test crawl scope
python cli.py crawl --sources directories,events --dry-run --limit 1000

# Execute crawling
python cli.py crawl --sources directories,events --limit 1000 --rate-limit 2.0
```

#### 3. Processing Phase
```bash
# Extract emails
python cli.py extract --min-confidence 0.7 --role-based-only

# Enrich company data
python cli.py enrich --enable-tech-fingerprinting --company-size-estimation

# Validate emails
python cli.py validate --mx-check --risk-assessment

# Score leads
python cli.py score --min-score 75
```

#### 4. Export Phase
```bash
# Generate report
python cli.py report --include-statistics --recommendations

# Export high-quality leads
python cli.py export --format csv,hubspot --segment high-score

# Health check after processing
python cli.py health-check
```

### Incremental Updates
For ongoing lead generation, you can run incremental updates:

```bash
# Daily updates
python cli.py crawl --sources directories --limit 200
python cli.py extract
python cli.py validate
python cli.py score
```

## Best Practices

### Data Quality
1. **Start with dry runs** to understand scope and estimate resources
2. **Use appropriate confidence thresholds** (0.6-0.8 recommended)
3. **Enable MX validation** for better deliverability
4. **Regular data refresh** to maintain freshness

### Performance Optimization
1. **Adjust rate limits** based on target sites' capacity
2. **Use concurrent workers** efficiently (8-12 recommended)
3. **Monitor system resources** during large crawls
4. **Implement incremental processing** for large datasets

### Compliance
1. **Always respect robots.txt** files
2. **Maintain audit logs** for compliance purposes
3. **Set appropriate data retention** periods
4. **Document legal basis** for data collection

### Target Selection
1. **Define clear personas** before starting
2. **Focus on specific sectors** for better results
3. **Use geographic targeting** for relevance
4. **Regular persona refinement** based on results

## Compliance & Ethics

### GDPR Compliance
The system is designed with GDPR compliance in mind:

- **Legitimate Interest (Article 6(1)(f))** as legal basis for B2B processing
- **Automatic audit logging** of all data processing activities
- **Data retention controls** with automatic cleanup
- **Opt-out mechanisms** for data subjects
- **Transparency** through comprehensive logging

### Data Subject Rights
The system supports data subject rights under GDPR:

- **Right of Access**: Audit logs provide complete processing history
- **Right to Rectification**: Database allows data correction
- **Right to Erasure**: Automatic and manual data deletion
- **Right to Object**: Opt-out mechanisms implemented

### Ethical Guidelines
1. **Business Purpose Only**: Use only for legitimate business purposes
2. **Respect Privacy**: Avoid personal emails and private information
3. **Honor Opt-outs**: Respect unsubscribe requests immediately
4. **Transparency**: Be clear about data collection purposes
5. **Proportionality**: Collect only necessary data

## Troubleshooting

### Common Issues

#### Unicode Encoding Errors (Windows)
**Problem**: UnicodeEncodeError when running commands
**Solution**: The system automatically handles encoding issues. If you encounter problems, ensure your terminal supports UTF-8.

#### Low Quality Results
**Problem**: Most leads have low scores
**Solutions**:
- Refine persona definitions in `configs/personas.yml`
- Adjust scoring weights in `configs/rules.yml`
- Improve source selection in `configs/sources.yml`
- Increase minimum confidence thresholds

#### Slow Performance
**Problem**: Crawling takes too long
**Solutions**:
- Reduce concurrent workers
- Increase rate limiting delays
- Use smaller batch sizes
- Check system resources with `health-check`

#### Validation Failures
**Problem**: Many emails marked as invalid
**Solutions**:
- Disable SMTP probing if causing issues
- Adjust risk assessment thresholds
- Check MX validation settings
- Review domain blacklists

### Health Check Interpretation

| Status | Meaning | Action Required |
|--------|---------|----------------|
| HEALTHY | All systems operational | None |
| DEGRADED | Some warnings present | Review warnings, monitor |
| UNHEALTHY | Critical issues found | Immediate attention required |

Common warning reasons:
- **No recent data**: Normal for new installations
- **High resource usage**: Monitor system performance
- **Low validation rate**: Review validation settings

### Log Files
The system creates detailed logs in the `logs/` directory:

- `osint.log`: Main system log
- `scrapy.log`: Web scraping logs (if Scrapy is used)

Use these logs to diagnose issues and monitor system behavior.

## Advanced Usage

### Custom Personas
Create specialized personas for your industry:

```yaml
custom_persona:
  description: "Custom role for specific industry"
  roles:
    - "Chief Data Officer"
    - "Head of Analytics"
  email_patterns:
    - "cdo@"
    - "data@"
    - "analytics@"
  scoring_weight: 45
  priority_level: "high"
```

### Sector-Specific Configuration
Customize sector definitions for better targeting:

```yaml
fintech:
  keywords:
    - "fintech"
    - "financial technology"
    - "digital banking"
  technology_signals:
    - "Stripe"
    - "Plaid"
    - "Open Banking"
  scoring_multiplier: 1.6
```

### Geographic Expansion
Add new geographic regions:

```yaml
apac:
  countries: ["JP", "SG", "AU", "HK"]
  languages: ["en", "ja"]
  tld_preferences: [".jp", ".com.au", ".sg"]
  scoring_boost: 15
```

### API Integration
For programmatic access, you can import modules directly:

```python
from core.config import ConfigManager
from scraping.crawler import OSINTCrawler
from validate.validator import EmailValidator

# Initialize components
config = ConfigManager()
crawler = OSINTCrawler(config)
validator = EmailValidator(config)

# Use programmatically
results = crawler.dry_run_crawl(['directories'], 100)
```

### Batch Processing
For large-scale operations, consider batch processing:

```bash
# Process in smaller chunks
for i in {1..10}; do
    python cli.py crawl --sources directories --limit 100
    python cli.py extract
    python cli.py validate
    sleep 300  # 5-minute pause between batches
done
```

### Custom Export Formats
The system supports custom export formats. Modify `export/exporter.py` to add new formats or customize existing ones.

### Performance Tuning
For high-volume operations:

1. **Database optimization**: Consider using PostgreSQL for large datasets
2. **Caching strategies**: Implement Redis for performance caching
3. **Distributed processing**: Use Celery for background task processing
4. **Monitoring**: Implement Prometheus/Grafana for detailed monitoring

---

## Support

For additional support:
1. Check the [GitHub Issues](link-to-issues) for known problems
2. Review the system logs in `logs/osint.log`
3. Run `python cli.py health-check` for system diagnostics
4. Consult the [Technical Documentation](OSINT_B2B_Email_System_Documentation.md) for implementation details

## Version Information
- **Current Version**: 1.0.0
- **Python Compatibility**: 3.12+
- **Last Updated**: 2024

---

*This system is designed for ethical, legitimate business use only. Always comply with applicable privacy laws and respect website terms of service.*