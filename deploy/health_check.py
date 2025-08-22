#!/usr/bin/env python3
"""
Health check script for OSINT B2B Email System
Used by Docker and monitoring systems to verify application health
"""

import sys
import os
import asyncio
import aiohttp
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import DatabaseManager
from core.config import ConfigManager
from monitoring.health import HealthMonitor


class HealthChecker:
    """Health check implementation for production deployment"""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.db_manager = DatabaseManager()
        self.health_monitor = HealthMonitor(self.db_manager, self.config_manager)

    async def check_database_connection(self):
        """Check database connectivity"""
        try:
            stats = self.db_manager.get_contact_stats()
            return True, f"Database accessible, {stats.get('total', 0)} contacts"
        except Exception as e:
            return False, f"Database error: {str(e)}"

    async def check_web_access(self):
        """Check if web scraping functionality is accessible"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://httpbin.org/status/200', timeout=5) as response:
                    if response.status == 200:
                        return True, "Web access functional"
                    else:
                        return False, f"Web access failed with status {response.status}"
        except Exception as e:
            return False, f"Web access error: {str(e)}"

    async def check_file_system(self):
        """Check file system access for logs, exports, etc."""
        try:
            # Check if critical directories are accessible
            critical_dirs = ['/app/logs', '/app/exports', '/app/cache']
            for dir_path in critical_dirs:
                if not os.path.exists(dir_path):
                    return False, f"Missing directory: {dir_path}"
                if not os.access(dir_path, os.W_OK):
                    return False, f"Directory not writable: {dir_path}"

            # Test write access
            test_file = '/app/logs/health_check.tmp'
            with open(test_file, 'w') as f:
                f.write('health_check')
            os.remove(test_file)

            return True, "File system access functional"
        except Exception as e:
            return False, f"File system error: {str(e)}"

    async def check_configuration(self):
        """Check configuration validity"""
        try:
            config = self.config_manager.get_current_config()
            if not config:
                return False, "No configuration loaded"

            # Check critical configuration sections
            required_sections = ['system', 'personas', 'scoring']
            for section in required_sections:
                if section not in config:
                    return False, f"Missing configuration section: {section}"

            return True, "Configuration valid"
        except Exception as e:
            return False, f"Configuration error: {str(e)}"

    async def perform_health_check(self):
        """Perform comprehensive health check"""
        checks = {
            'database': self.check_database_connection,
            'web_access': self.check_web_access,
            'file_system': self.check_file_system,
            'configuration': self.check_configuration
        }

        results = {}
        overall_healthy = True

        for check_name, check_func in checks.items():
            try:
                success, message = await check_func()
                results[check_name] = {
                    'status': 'healthy' if success else 'unhealthy',
                    'message': message
                }
                if not success:
                    overall_healthy = False
            except Exception as e:
                results[check_name] = {
                    'status': 'error',
                    'message': f"Check failed: {str(e)}"
                }
                overall_healthy = False

        return overall_healthy, results

    async def run(self):
        """Run health check and return appropriate exit code"""
        try:
            healthy, results = await self.perform_health_check()

            # Output results
            health_data = {
                'overall_status': 'healthy' if healthy else 'unhealthy',
                'timestamp': str(asyncio.get_event_loop().time()),
                'checks': results
            }

            print(json.dumps(health_data, indent=2))

            # Return exit code
            return 0 if healthy else 1

        except Exception as e:
            error_data = {
                'overall_status': 'error',
                'timestamp': str(asyncio.get_event_loop().time()),
                'error': str(e)
            }
            print(json.dumps(error_data, indent=2))
            return 1


def main():
    """Main entry point for health check"""
    try:
        # Set up event loop for async operations
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        checker = HealthChecker()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            exit_code = loop.run_until_complete(checker.run())
            sys.exit(exit_code)
        finally:
            loop.close()

    except Exception as e:
        error_data = {
            'overall_status': 'error',
            'timestamp': str(asyncio.get_event_loop().time()),
            'error': f"Health check script failed: {str(e)}"
        }
        print(json.dumps(error_data, indent=2))
        sys.exit(1)


if __name__ == '__main__':
    main()