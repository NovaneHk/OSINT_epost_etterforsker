# OSINT B2B Email System - Terminal Usage Guide

## System Overview

The OSINT B2B Email System is a comprehensive command-line tool for ethical lead generation and email discovery. It provides a complete pipeline from search seed generation to validated email export.

## Prerequisites

### 1. Environment Setup
```bash
# Copy environment configuration
copy .env.example .env

# Install dependencies
pip install -r requirements_core.txt
```

### 2. System Health Check
Always start by checking system health:
```bash
python cli.py health-check
```

## Available Commands

### Core Workflow Commands

#### 1. `seed` - Generate Search Seeds
Generate search queries and initialize crawling targets.

```bash
python cli.py seed --persona PERSONA --sector SECTOR --geo GEOGRAPHY [OPTIONS]
```

**Required Parameters:**
- `--persona`: Target persona (e.g., 'technical_leaders', 'procurement_specialists')
- `--sector`: Target sector (e.g., 'technology', 'ecommerce', 'finance')
- `--geo`: Geographic target (e.g., 'nordics', 'dach', 'uk')

**Optional Parameters:**
- `--output-limit INTEGER`: Maximum number of leads to generate (default: 10000)
- `--sources TEXT`: Comma-separated source types (default: "directories,events,sites")
- `--dry-run`: Perform dry run without actual crawling

**Example:**
```bash
# Dry run to see what queries would be generated
python cli.py seed --persona technical_leaders --sector technology --geo nordics --dry-run

# Generate seeds for real
python cli.py seed --persona technical_leaders --sector technology --geo nordics
```

#### 2. `crawl` - Execute Web Crawling
Execute web crawling to collect company data.

```bash
python cli.py crawl [OPTIONS]
```

**Options:**
- `--sources TEXT`: Source types to crawl (default: "directories,events,sites")
- `--concurrent-workers INTEGER`: Number of concurrent workers (default: 8)
- `--rate-limit FLOAT`: Requests per second limit (default: 2.0)
- `--limit INTEGER`: Maximum pages to crawl (default: 1000)
- `--dry-run`: Perform dry run
- `--respect-robots`: Respect robots.txt (default: True)

**Example:**
```bash
# Basic crawling
python cli.py crawl

# Crawl with custom settings
python cli.py crawl --concurrent-workers 4 --rate-limit 1.5 --limit 500
```

#### 3. `extract` - Extract Emails
Extract emails from crawled data.

```bash
python cli.py extract [OPTIONS]
```

**Options:**
- `--min-confidence FLOAT`: Minimum confidence score (default: 0.6)
- `--role-based-only`: Extract only role-based emails (default: True)
- `--context-analysis`: Enable context analysis (default: True)

**Example:**
```bash
python cli.py extract --min-confidence 0.7
```

#### 4. `validate` - Validate Emails
Validate and clean email addresses.

```bash
python cli.py validate [OPTIONS]
```

**Options:**
- `--mx-check`: Perform MX record validation (default: True)
- `--smtp-probe`: Perform SMTP probing (default: False)
- `--dedupe-aggressive`: Aggressive deduplication (default: True)
- `--risk-assessment`: Perform risk assessment (default: True)

**Example:**
```bash
python cli.py validate --smtp-probe
```

#### 5. `score` - Score and Rank Leads
Score and rank email leads.

```bash
python cli.py score [OPTIONS]
```

**Options:**
- `--min-score INTEGER`: Minimum score threshold (default: 70)
- `--persona-weight INTEGER`: Persona matching weight percentage (default: 35)
- `--sector-weight INTEGER`: Sector relevance weight percentage (default: 25)

**Example:**
```bash
python cli.py score --min-score 80 --persona-weight 40
```

#### 6. `enrich` - Enrich Company Data
Enrich company data with additional information.

```bash
python cli.py enrich [OPTIONS]
```

**Options:**
- `--enable-tech-fingerprinting`: Enable technology fingerprinting (default: True)
- `--company-size-estimation`: Estimate company sizes (default: True)
- `--external-apis`: Use external APIs for enrichment (default: False)

**Example:**
```bash
python cli.py enrich --external-apis
```

#### 7. `export` - Export Results
Export processed leads to various formats.

```bash
python cli.py export [OPTIONS]
```

**Options:**
- `--format TEXT`: Export formats (default: "csv,jsonl")
- `--output-dir TEXT`: Output directory (default: "out")
- `--include-audit-log`: Include audit log (default: True)
- `--compliance-headers`: Add compliance headers (default: True)
- `--segment TEXT`: Export specific segment

**Example:**
```bash
python cli.py export --format "csv,jsonl,hubspot" --output-dir "exports"
```

### Utility Commands

#### 8. `report` - Generate Summary Report
Generate summary report.

```bash
python cli.py report [OPTIONS]
```

**Options:**
- `--include-statistics`: Include detailed statistics (default: True)
- `--recommendations`: Include recommendations (default: True)
- `--output-file TEXT`: Output file path (default: "out/summary_report.md")

**Example:**
```bash
python cli.py report --output-file "reports/analysis.md"
```

#### 9. `health-check` - System Health Check
Perform system health check.

```bash
python cli.py health-check
```

#### 10. `configure` - Configure System
Configure system settings.

```bash
python cli.py configure [OPTIONS]
```

**Options:**
- `--persona TEXT`: Set default persona
- `--sector TEXT`: Set default sector
- `--geo TEXT`: Set default geography
- `--rate-limit FLOAT`: Set rate limit
- `--show-config`: Show current configuration

**Example:**
```bash
# Show current configuration
python cli.py configure --show-config

# Update configuration
python cli.py configure --persona technical_leaders --rate-limit 1.5
```

## Available Personas

The system supports the following personas (defined in `configs/personas.yml`):

- **technical_leaders**: CTOs, Tech Leads, VP Engineering, etc.
- **procurement_specialists**: Procurement Managers, Purchasing Directors, etc.
- **operations_leaders**: COOs, Operations Managers, etc.
- **sales_leaders**: Sales Directors, VP Sales, etc.
- **marketing_leaders**: CMOs, Marketing Directors, etc.
- **finance_leaders**: CFOs, Finance Directors, etc.

## Complete Workflow Example

Here's a complete workflow from start to finish:

```bash
# 1. Check system health
python cli.py health-check

# 2. Generate search seeds (dry run first)
python cli.py seed --persona technical_leaders --sector technology --geo nordics --dry-run

# 3. Generate actual seeds
python cli.py seed --persona technical_leaders --sector technology --geo nordics

# 4. Crawl for data
python cli.py crawl --limit 500 --rate-limit 2.0

# 5. Extract emails
python cli.py extract --min-confidence 0.7

# 6. Validate emails
python cli.py validate

# 7. Score leads
python cli.py score --min-score 75

# 8. Enrich data
python cli.py enrich

# 9. Export results
python cli.py export --format "csv,jsonl"

# 10. Generate report
python cli.py report
```

## Output Files

The system generates various output files:

- **Database**: `data/osint_cache.db` - SQLite database with all data
- **Exports**: `out/` directory - CSV, JSONL, and other export formats
- **Logs**: `logs/osint_system.log` - System logs
- **Reports**: `out/summary_report.md` - Summary reports

## Configuration Files

Key configuration files:

- **Environment**: `.env` - Environment variables and API keys
- **Personas**: `configs/personas.yml` - Target persona definitions
- **Sources**: `configs/sources.yml` - Data source configurations
- **Rules**: `configs/rules.yml` - Processing rules and filters

## Best Practices

### 1. Rate Limiting
Always respect rate limits to avoid being blocked:
```bash
python cli.py crawl --rate-limit 1.0 --concurrent-workers 4
```

### 2. Dry Runs
Use dry runs to test configurations:
```bash
python cli.py seed --persona technical_leaders --sector technology --geo nordics --dry-run
```

### 3. Incremental Processing
Process data in stages and check results:
```bash
# Start small
python cli.py crawl --limit 100
python cli.py extract
python cli.py validate
```

### 4. Health Monitoring
Regularly check system health:
```bash
python cli.py health-check
```

### 5. Compliance
Always use compliance features:
```bash
python cli.py export --compliance-headers --include-audit-log
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
   ```bash
   pip install -r requirements_core.txt
   ```

2. **Database Issues**: Check database connectivity in health check
   ```bash
   python cli.py health-check
   ```

3. **Rate Limiting**: Reduce concurrent workers and increase delays
   ```bash
   python cli.py crawl --concurrent-workers 2 --rate-limit 0.5
   ```

4. **Memory Issues**: Process smaller batches
   ```bash
   python cli.py crawl --limit 200
   ```

### Getting Help

For detailed help on any command:
```bash
python cli.py COMMAND --help
```

For example:
```bash
python cli.py seed --help
python cli.py crawl --help
```

## Advanced Usage

### Custom Personas
You can modify `configs/personas.yml` to add custom personas or modify existing ones.

### API Integration
Set API keys in `.env` for enhanced functionality:
```
CLEARBIT_API_KEY=your_key_here
HUNTER_API_KEY=your_key_here
```

### Automation
The CLI can be integrated into scripts for automation:
```bash
#!/bin/bash
python cli.py seed --persona technical_leaders --sector technology --geo nordics
python cli.py crawl --limit 1000
python cli.py extract
python cli.py validate
python cli.py score
python cli.py export
```

## Legal and Ethical Considerations

- Always respect robots.txt files
- Use appropriate rate limiting
- Comply with GDPR and data protection laws
- Only use for legitimate business purposes
- Respect website terms of service
- Include proper opt-out mechanisms

## Support

For issues or questions:
1. Check the health status: `python cli.py health-check`
2. Review logs in `logs/osint_system.log`
3. Consult the documentation files in the project
