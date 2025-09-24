@echo off
echo ========================================
echo OSINT B2B Email System - Quick Start
echo ========================================
echo.

echo Checking system health...
python cli.py health-check
echo.

echo Available commands:
echo.
echo 1. Generate search seeds (dry run):
echo    python cli.py seed --persona technical_leaders --sector technology --geo nordics --dry-run
echo.
echo 2. Full workflow example:
echo    python cli.py seed --persona technical_leaders --sector technology --geo nordics
echo    python cli.py crawl --limit 100 --rate-limit 2.0
echo    python cli.py extract --min-confidence 0.7
echo    python cli.py validate
echo    python cli.py score --min-score 75
echo    python cli.py export --format csv,jsonl
echo.
echo 3. Get help for any command:
echo    python cli.py COMMAND --help
echo.
echo 4. Show all available commands:
echo    python cli.py --help
echo.
echo For detailed documentation, see TERMINAL_USAGE_GUIDE.md
echo ========================================
