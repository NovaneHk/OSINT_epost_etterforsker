"""
Integration test configuration.
Excludes legacy script-style test files that are not yet pytest-compatible.
"""

collect_ignore_glob = [
    "test_phase2_integration.py",
    "test_phase4_dashboard.py",
    "test_web_scraping_integration.py",
    "test_pipeline_integration.py",
]
