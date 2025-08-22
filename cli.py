#!/usr/bin/env python3
"""
OSINT B2B Email List Generation System
Advanced CLI interface for ethical lead generation
"""

import typer
import asyncio
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
import yaml
import json
from datetime import datetime

# Import our modules
from scraping.crawler import OSINTCrawler
from extract.email_extractor import EmailExtractor
from validate.validator import EmailValidator
from scoring.scorer import LeadScorer
from export.exporter import DataExporter
from core.database import DatabaseManager
from core.config import ConfigManager

app = typer.Typer(
    name="osint-lists",
    help="Advanced OSINT B2B Email List Generation System",
    rich_markup_mode="rich"
)
console = Console()

# Global configuration
config_manager = ConfigManager()
db_manager = DatabaseManager()

@app.command()
def seed(
    persona: str = typer.Option(..., help="Target persona (e.g., 'CTO', 'procurement')"),
    sector: str = typer.Option(..., help="Target sector (e.g., 'technology', 'ecommerce')"),
    geo: str = typer.Option(..., help="Geographic target (e.g., 'nordics', 'dach')"),
    output_limit: int = typer.Option(10000, help="Maximum number of leads to generate"),
    sources: str = typer.Option("directories,events,sites", help="Comma-separated source types"),
    dry_run: bool = typer.Option(False, help="Perform dry run without actual crawling")
):
    """Generate search seeds and initialize crawling targets."""

    console.print(f"[bold blue][SEED] Generating seeds for {persona} in {sector} sector ({geo})[/bold blue]")

    # Load configuration
    personas_config = config_manager.load_personas()
    sources_config = config_manager.load_sources()

    # Validate inputs
    if persona not in personas_config.get('personas', {}):
        console.print(f"[red]❌ Unknown persona: {persona}[/red]")
        console.print(f"Available personas: {list(personas_config.get('personas', {}).keys())}")
        raise typer.Exit(1)

    # Generate search queries
    crawler = OSINTCrawler(config_manager)
    search_queries = crawler.generate_search_queries(persona, sector, geo)

    # Store seeds in database
    db_manager.store_seeds(search_queries, persona, sector, geo)

    console.print(f"[green][VALIDATE] Generated {len(search_queries)} search queries[/green]")

    if not dry_run:
        console.print("[yellow][SAVE] Seeds stored in database[/yellow]")
    else:
        console.print("[yellow][ENRICH] Dry run - seeds not stored[/yellow]")
        for i, query in enumerate(search_queries[:5], 1):
            console.print(f"  {i}. {query}")

@app.command()
def crawl(
    sources: str = typer.Option("directories,events,sites", help="Source types to crawl"),
    concurrent_workers: int = typer.Option(8, help="Number of concurrent workers"),
    rate_limit: float = typer.Option(2.0, help="Requests per second limit"),
    limit: int = typer.Option(1000, help="Maximum pages to crawl"),
    dry_run: bool = typer.Option(False, help="Perform dry run"),
    respect_robots: bool = typer.Option(True, help="Respect robots.txt")
):
    """Execute web crawling to collect company data."""

    console.print(f"[bold blue][CRAWL] Starting crawl with {concurrent_workers} workers[/bold blue]")

    source_list = [s.strip() for s in sources.split(',')]

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:

        crawl_task = progress.add_task("Crawling sources...", total=None)

        crawler = OSINTCrawler(config_manager)

        if dry_run:
            results = crawler.dry_run_crawl(source_list, limit)
            console.print(f"[yellow][ENRICH] Dry run completed - would crawl {results['estimated_pages']} pages[/yellow]")
        else:
            results = asyncio.run(crawler.crawl_sources(
                source_list,
                concurrent_workers,
                rate_limit,
                limit,
                respect_robots
            ))

            progress.update(crawl_task, completed=True)

            # Display results
            table = Table(title="Crawling Results")
            table.add_column("Source Type", style="cyan")
            table.add_column("Pages Crawled", justify="right")
            table.add_column("Companies Found", justify="right")
            table.add_column("Success Rate", justify="right")

            for source_type, stats in results.items():
                table.add_row(
                    source_type,
                    str(stats.get('pages_crawled', 0)),
                    str(stats.get('companies_found', 0)),
                    f"{stats.get('success_rate', 0):.1%}"
                )

            console.print(table)

@app.command()
def extract(
    min_confidence: float = typer.Option(0.6, help="Minimum confidence score for email extraction"),
    role_based_only: bool = typer.Option(True, help="Extract only role-based emails"),
    context_analysis: bool = typer.Option(True, help="Enable context analysis")
):
    """Extract emails from crawled data."""

    console.print("[bold blue][EMAIL] Extracting emails from crawled data[/bold blue]")

    extractor = EmailExtractor(config_manager)

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:

        extract_task = progress.add_task("Extracting emails...", total=None)

        results = extractor.extract_all_emails(
            min_confidence=min_confidence,
            role_based_only=role_based_only,
            context_analysis=context_analysis
        )

        progress.update(extract_task, completed=True)

        console.print(f"[green][VALIDATE] Extracted {results['total_emails']} emails[/green]")
        console.print(f"[yellow][REPORT] Average confidence: {results['avg_confidence']:.2f}[/yellow]")

@app.command()
def enrich(
    enable_tech_fingerprinting: bool = typer.Option(True, help="Enable technology fingerprinting"),
    company_size_estimation: bool = typer.Option(True, help="Estimate company sizes"),
    external_apis: bool = typer.Option(False, help="Use external APIs for enrichment")
):
    """Enrich company data with additional information."""

    console.print("[bold blue][ENRICH] Enriching company data[/bold blue]")

    from enrich.enricher import DataEnricher
    enricher = DataEnricher(config_manager)

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:

        enrich_task = progress.add_task("Enriching data...", total=None)

        results = enricher.enrich_all_companies(
            tech_fingerprinting=enable_tech_fingerprinting,
            size_estimation=company_size_estimation,
            external_apis=external_apis
        )

        progress.update(enrich_task, completed=True)

        console.print(f"[green][VALIDATE] Enriched {results['companies_processed']} companies[/green]")

@app.command()
def validate(
    mx_check: bool = typer.Option(True, help="Perform MX record validation"),
    smtp_probe: bool = typer.Option(False, help="Perform SMTP probing (careful!)"),
    dedupe_aggressive: bool = typer.Option(True, help="Aggressive deduplication"),
    risk_assessment: bool = typer.Option(True, help="Perform risk assessment")
):
    """Validate and clean email addresses."""

    console.print("[bold blue][VALIDATE] Validating email addresses[/bold blue]")

    validator = EmailValidator(config_manager)

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:

        validate_task = progress.add_task("Validating emails...", total=None)

        results = validator.validate_all_emails(
            mx_check=mx_check,
            smtp_probe=smtp_probe,
            aggressive_dedupe=dedupe_aggressive,
            risk_assessment=risk_assessment
        )

        progress.update(validate_task, completed=True)

        # Display validation results
        table = Table(title="Validation Results")
        table.add_column("Status", style="cyan")
        table.add_column("Count", justify="right")
        table.add_column("Percentage", justify="right")

        total = results['total_processed']
        for status, count in results['status_breakdown'].items():
            percentage = (count / total * 100) if total > 0 else 0
            table.add_row(status, str(count), f"{percentage:.1f}%")

        console.print(table)

@app.command()
def score(
    min_score: int = typer.Option(70, help="Minimum score threshold"),
    persona_weight: int = typer.Option(35, help="Persona matching weight percentage"),
    sector_weight: int = typer.Option(25, help="Sector relevance weight percentage")
):
    """Score and rank email leads."""

    console.print("[bold blue][SCORE] Scoring email leads[/bold blue]")

    scorer = LeadScorer(config_manager)

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:

        score_task = progress.add_task("Scoring leads...", total=None)

        results = scorer.score_all_leads(
            min_score=min_score,
            weights={
                'persona_match': persona_weight / 100,
                'sector_relevance': sector_weight / 100,
                'geographic_preference': 0.20,
                'source_credibility': 0.15,
                'data_freshness': 0.05
            }
        )

        progress.update(score_task, completed=True)

        console.print(f"[green][VALIDATE] Scored {results['total_leads']} leads[/green]")
        console.print(f"[yellow][TOP] {results['high_quality_leads']} leads above threshold[/yellow]")

@app.command()
def export(
    format: str = typer.Option("csv,jsonl", help="Export formats (csv,jsonl,hubspot)"),
    output_dir: str = typer.Option("out", help="Output directory"),
    include_audit_log: bool = typer.Option(True, help="Include audit log"),
    compliance_headers: bool = typer.Option(True, help="Add compliance headers"),
    segment: Optional[str] = typer.Option(None, help="Export specific segment")
):
    """Export processed leads to various formats."""

    console.print(f"[bold blue][EXPORT] Exporting leads to {format} format(s)[/bold blue]")

    formats = [f.strip() for f in format.split(',')]

    exporter = DataExporter(config_manager)

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:

        export_task = progress.add_task("Exporting data...", total=None)

        results = exporter.export_leads(
            formats=formats,
            output_dir=output_dir,
            include_audit=include_audit_log,
            compliance_mode=compliance_headers,
            segment=segment
        )

        progress.update(export_task, completed=True)

        # Display export results
        table = Table(title="Export Results")
        table.add_column("Format", style="cyan")
        table.add_column("File Path", style="green")
        table.add_column("Records", justify="right")

        for format_type, info in results.items():
            table.add_row(
                format_type,
                info['file_path'],
                str(info['record_count'])
            )

        console.print(table)

@app.command()
def report(
    include_statistics: bool = typer.Option(True, help="Include detailed statistics"),
    recommendations: bool = typer.Option(True, help="Include recommendations"),
    output_file: str = typer.Option("out/summary_report.md", help="Output file path")
):
    """Generate summary report."""

    console.print("[bold blue][REPORT] Generating summary report[/bold blue]")

    from report.generator import ReportGenerator
    generator = ReportGenerator(config_manager, db_manager)

    report_data = generator.generate_summary_report(
        include_stats=include_statistics,
        include_recommendations=recommendations
    )

    # Write report to file
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report_data)

    console.print(f"[green][VALIDATE] Report generated: {output_file}[/green]")

@app.command()
def health_check():
    """Perform system health check."""

    console.print("[bold blue][HEALTH] Performing system health check[/bold blue]")

    from monitoring.health import HealthChecker
    checker = HealthChecker(config_manager)

    results = checker.run_all_checks()

    # Display health status
    status_color = {
        'healthy': 'green',
        'warning': 'yellow',
        'critical': 'red',
        'error': 'red'
    }

    table = Table(title="System Health Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details")

    for check_name, check_result in results['checks'].items():
        status = check_result['status']
        color = status_color.get(status, 'white')

        table.add_row(
            check_name.replace('_', ' ').title(),
            f"[{color}]{status.upper()}[/{color}]",
            str(check_result.get('details', {}).get('message', ''))
        )

    console.print(table)

    overall_status = results['overall_status']
    overall_color = status_color.get(overall_status, 'white')
    console.print(f"\n[{overall_color}]Overall Status: {overall_status.upper()}[/{overall_color}]")

@app.command()
def configure(
    persona: Optional[str] = typer.Option(None, help="Set default persona"),
    sector: Optional[str] = typer.Option(None, help="Set default sector"),
    geo: Optional[str] = typer.Option(None, help="Set default geography"),
    rate_limit: Optional[float] = typer.Option(None, help="Set rate limit"),
    show_config: bool = typer.Option(False, help="Show current configuration")
):
    """Configure system settings."""

    if show_config:
        config = config_manager.get_current_config()
        console.print("[bold blue][CONFIG] Current Configuration[/bold blue]")
        console.print(yaml.dump(config, default_flow_style=False))
        return

    # Update configuration
    updates = {}
    if persona:
        updates['default_persona'] = persona
    if sector:
        updates['default_sector'] = sector
    if geo:
        updates['default_geo'] = geo
    if rate_limit:
        updates['rate_limit'] = rate_limit

    if updates:
        config_manager.update_config(updates)
        console.print("[green][VALIDATE] Configuration updated[/green]")
    else:
        console.print("[yellow][INFO] No configuration changes specified[/yellow]")

if __name__ == "__main__":
    app()