"""
Master Test Runner for Comprehensive OSINT Functional Testing
Coordinates and executes all functional test suites with reporting
"""

import sys
import os
import time
import json
from typing import Dict, List, Any
import argparse
from datetime import datetime
import traceback

# Add the tests directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import all test modules
try:
    from test_api_endpoints import APIEndpointTester
    from test_frontend_components import FrontendComponentTester
    from test_database_operations import DatabaseOperationsTester
    from test_authentication_authorization import AuthenticationAuthorizationTester
    from test_osint_search import OSINTSearchTester
    from test_data_visualization import DataVisualizationTester
except ImportError as e:
    print(f"Error importing test modules: {e}")
    sys.exit(1)

class MasterTestRunner:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {
            "api_url": "http://localhost:8000",
            "frontend_url": "http://localhost:3000",
            "skip_slow_tests": False,
            "parallel_execution": False,
            "generate_reports": True
        }

        self.test_results = {}
        self.overall_stats = {
            "total_tests": 0,
            "successful_tests": 0,
            "failed_tests": 0,
            "skipped_tests": 0,
            "total_duration": 0,
            "start_time": None,
            "end_time": None
        }

        # Test suite definitions
        self.test_suites = {
            "api_endpoints": {
                "name": "API Endpoints Testing",
                "class": APIEndpointTester,
                "description": "Tests all API endpoints, authentication, CRUD operations, performance, and security",
                "priority": 1,
                "estimated_duration": 300  # 5 minutes
            },
            "frontend_components": {
                "name": "Frontend Components Testing",
                "class": FrontendComponentTester,
                "description": "Tests React components, responsiveness, accessibility, and user interactions",
                "priority": 2,
                "estimated_duration": 240  # 4 minutes
            },
            "database_operations": {
                "name": "Database Operations Testing",
                "class": DatabaseOperationsTester,
                "description": "Tests PostgreSQL, MongoDB, Redis operations, performance, and data integrity",
                "priority": 1,
                "estimated_duration": 180  # 3 minutes
            },
            "authentication_authorization": {
                "name": "Authentication & Authorization Testing",
                "class": AuthenticationAuthorizationTester,
                "description": "Tests user management, JWT tokens, RBAC, and security measures",
                "priority": 1,
                "estimated_duration": 120  # 2 minutes
            },
            "osint_search": {
                "name": "OSINT Search Functionality Testing",
                "class": OSINTSearchTester,
                "description": "Tests LinkedIn, social media, domain intelligence, and data correlation",
                "priority": 2,
                "estimated_duration": 360  # 6 minutes
            },
            "data_visualization": {
                "name": "Data Visualization Testing",
                "class": DataVisualizationTester,
                "description": "Tests dashboard KPIs, charts, real-time updates, and mobile responsiveness",
                "priority": 3,
                "estimated_duration": 150  # 2.5 minutes
            }
        }

    def print_banner(self):
        """Print test execution banner"""
        print("=" * 80)
        print("🚀 OSINT E-POST ETTERFORSKER - COMPREHENSIVE FUNCTIONAL TESTING")
        print("=" * 80)
        print(f"📅 Test execution started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 API URL: {self.config['api_url']}")
        print(f"🖥️  Frontend URL: {self.config['frontend_url']}")

        total_estimated_time = sum(suite["estimated_duration"] for suite in self.test_suites.values())
        print(f"⏱️  Estimated total duration: {total_estimated_time // 60} minutes {total_estimated_time % 60} seconds")
        print()

    def print_test_suite_info(self):
        """Print information about all test suites"""
        print("📋 TEST SUITES OVERVIEW:")
        print("-" * 50)

        for suite_id, suite_info in self.test_suites.items():
            priority_emoji = "🔴" if suite_info["priority"] == 1 else "🟡" if suite_info["priority"] == 2 else "🟢"
            duration_min = suite_info["estimated_duration"] // 60
            duration_sec = suite_info["estimated_duration"] % 60

            print(f"{priority_emoji} {suite_info['name']}")
            print(f"   📖 {suite_info['description']}")
            print(f"   ⏱️  Estimated: {duration_min}m {duration_sec}s")
            print()

    def run_test_suite(self, suite_id: str, suite_info: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test suite"""
        print(f"🧪 RUNNING: {suite_info['name']}")
        print("-" * 60)

        start_time = time.time()

        try:
            # Initialize tester based on suite type
            if suite_id == "api_endpoints":
                tester = suite_info["class"](base_url=self.config["api_url"])
            elif suite_id == "frontend_components":
                tester = suite_info["class"](base_url=self.config["frontend_url"])
            elif suite_id == "data_visualization":
                tester = suite_info["class"](
                    base_url=self.config["frontend_url"],
                    api_url=self.config["api_url"]
                )
            elif suite_id == "osint_search":
                tester = suite_info["class"](base_url=self.config["api_url"])
            else:
                tester = suite_info["class"]()

            # Run the test suite
            report = tester.run_all_tests()

            duration = time.time() - start_time

            # Process results
            result = {
                "suite_id": suite_id,
                "suite_name": suite_info["name"],
                "success": True,
                "duration": duration,
                "report": report,
                "error": None
            }

            if report:
                result.update({
                    "total_tests": report.get("total_tests", 0),
                    "successful_tests": report.get("successful_tests", 0),
                    "success_rate": report.get("success_rate", 0)
                })

            print(f"✅ COMPLETED: {suite_info['name']} ({duration:.1f}s)")

        except Exception as e:
            duration = time.time() - start_time
            error_details = f"{str(e)}\n{traceback.format_exc()}"

            result = {
                "suite_id": suite_id,
                "suite_name": suite_info["name"],
                "success": False,
                "duration": duration,
                "report": None,
                "error": error_details,
                "total_tests": 0,
                "successful_tests": 0,
                "success_rate": 0
            }

            print(f"❌ FAILED: {suite_info['name']} - {str(e)}")

        print()
        return result

    def run_all_tests(self, selected_suites: List[str] = None) -> Dict[str, Any]:
        """Run all or selected test suites"""
        self.overall_stats["start_time"] = time.time()

        self.print_banner()
        self.print_test_suite_info()

        # Determine which suites to run
        suites_to_run = selected_suites or list(self.test_suites.keys())

        # Sort by priority
        suites_to_run.sort(key=lambda x: self.test_suites[x]["priority"])

        print(f"🎯 EXECUTING {len(suites_to_run)} TEST SUITES:")
        for suite_id in suites_to_run:
            print(f"   • {self.test_suites[suite_id]['name']}")
        print()

        # Run each test suite
        for suite_id in suites_to_run:
            if suite_id not in self.test_suites:
                print(f"⚠️  Unknown test suite: {suite_id}")
                continue

            suite_info = self.test_suites[suite_id]
            result = self.run_test_suite(suite_id, suite_info)
            self.test_results[suite_id] = result

            # Update overall stats
            self.overall_stats["total_tests"] += result["total_tests"]
            self.overall_stats["successful_tests"] += result["successful_tests"]
            if not result["success"]:
                self.overall_stats["failed_tests"] += 1

        self.overall_stats["end_time"] = time.time()
        self.overall_stats["total_duration"] = self.overall_stats["end_time"] - self.overall_stats["start_time"]

        return self.generate_final_report()

    def generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive final report"""
        print("📊 COMPREHENSIVE TEST EXECUTION REPORT")
        print("=" * 80)

        # Overall statistics
        total_duration_min = int(self.overall_stats["total_duration"] // 60)
        total_duration_sec = int(self.overall_stats["total_duration"] % 60)

        overall_success_rate = 0
        if self.overall_stats["total_tests"] > 0:
            overall_success_rate = (self.overall_stats["successful_tests"] / self.overall_stats["total_tests"]) * 100

        print(f"\n📈 OVERALL STATISTICS:")
        print(f"   Total Test Suites: {len(self.test_results)}")
        print(f"   Total Individual Tests: {self.overall_stats['total_tests']}")
        print(f"   Successful Tests: {self.overall_stats['successful_tests']}")
        print(f"   Failed Test Suites: {self.overall_stats['failed_tests']}")
        print(f"   Overall Success Rate: {overall_success_rate:.1f}%")
        print(f"   Total Execution Time: {total_duration_min}m {total_duration_sec}s")

        # Suite-by-suite results
        print(f"\n📋 SUITE-BY-SUITE RESULTS:")
        print("-" * 50)

        for suite_id, result in self.test_results.items():
            status_emoji = "✅" if result["success"] else "❌"
            duration_display = f"{result['duration']:.1f}s"

            print(f"{status_emoji} {result['suite_name']}")
            print(f"   Duration: {duration_display}")

            if result["success"] and result["report"]:
                success_rate = result.get("success_rate", 0)
                total_tests = result.get("total_tests", 0)
                successful_tests = result.get("successful_tests", 0)
                print(f"   Tests: {successful_tests}/{total_tests} ({success_rate:.1f}% success)")
            elif result["error"]:
                error_summary = result["error"].split('\n')[0][:100]
                print(f"   Error: {error_summary}")

            print()

        # Failed suites details
        failed_suites = [r for r in self.test_results.values() if not r["success"]]
        if failed_suites:
            print(f"\n🚨 FAILED SUITE DETAILS:")
            print("-" * 30)
            for suite in failed_suites:
                print(f"❌ {suite['suite_name']}:")
                print(f"   {suite['error']}")
                print()

        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        print("-" * 20)

        if overall_success_rate >= 95:
            print("🎉 Excellent! The OSINT application is performing very well.")
        elif overall_success_rate >= 85:
            print("👍 Good performance. Minor issues may need attention.")
        elif overall_success_rate >= 70:
            print("⚠️  Moderate performance. Several issues should be addressed.")
        else:
            print("🚨 Poor performance. Significant issues require immediate attention.")

        if failed_suites:
            print(f"   • Review and fix {len(failed_suites)} failed test suite(s)")

        if self.overall_stats["total_duration"] > 1800:  # 30 minutes
            print("   • Consider optimizing test execution time")

        # Generate summary report
        final_report = {
            "execution_summary": {
                "start_time": datetime.fromtimestamp(self.overall_stats["start_time"]).isoformat(),
                "end_time": datetime.fromtimestamp(self.overall_stats["end_time"]).isoformat(),
                "total_duration_seconds": self.overall_stats["total_duration"],
                "overall_success_rate": overall_success_rate
            },
            "statistics": self.overall_stats,
            "suite_results": self.test_results,
            "config": self.config
        }

        return final_report

    def save_reports(self, final_report: Dict[str, Any]):
        """Save comprehensive test reports"""
        if not self.config.get("generate_reports", True):
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save master report
        master_report_file = f"comprehensive_test_report_{timestamp}.json"
        with open(master_report_file, "w") as f:
            json.dump(final_report, f, indent=2, default=str)

        print(f"\n📄 REPORTS SAVED:")
        print(f"   📋 Master Report: {master_report_file}")

        # Save individual suite reports
        for suite_id, result in self.test_results.items():
            if result["success"] and result["report"]:
                suite_report_file = f"{suite_id}_test_report_{timestamp}.json"
                with open(suite_report_file, "w") as f:
                    json.dump(result["report"], f, indent=2, default=str)
                print(f"   📄 {result['suite_name']}: {suite_report_file}")


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description="OSINT Comprehensive Functional Testing")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--frontend-url", default="http://localhost:3000", help="Frontend base URL")
    parser.add_argument("--suites", nargs="+", help="Specific test suites to run",
                       choices=["api_endpoints", "frontend_components", "database_operations",
                               "authentication_authorization", "osint_search", "data_visualization"])
    parser.add_argument("--skip-slow", action="store_true", help="Skip slow-running tests")
    parser.add_argument("--no-reports", action="store_true", help="Don't generate report files")

    args = parser.parse_args()

    # Configure test runner
    config = {
        "api_url": args.api_url,
        "frontend_url": args.frontend_url,
        "skip_slow_tests": args.skip_slow,
        "generate_reports": not args.no_reports
    }

    # Run tests
    runner = MasterTestRunner(config)

    try:
        final_report = runner.run_all_tests(selected_suites=args.suites)

        if config["generate_reports"]:
            runner.save_reports(final_report)

        # Exit with appropriate code
        overall_success = all(result["success"] for result in runner.test_results.values())
        sys.exit(0 if overall_success else 1)

    except KeyboardInterrupt:
        print("\n⚠️  Test execution interrupted by user")
        sys.exit(2)
    except Exception as e:
        print(f"\n❌ Test execution failed: {str(e)}")
        traceback.print_exc()
        sys.exit(3)


if __name__ == "__main__":
    main()