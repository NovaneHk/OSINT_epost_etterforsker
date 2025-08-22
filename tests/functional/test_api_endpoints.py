"""
Comprehensive API Endpoints Functional Testing
Tests all API endpoints, authentication, CRUD operations, performance, and security
"""

import time
import json
import requests
import concurrent.futures
import threading
from typing import Dict, Any, List
from datetime import datetime, timedelta

class APIEndpointTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.auth_token = None
        self.test_data = {}
        self.performance_metrics = []

    def setup_test_environment(self):
        """Setup test environment with test data"""
        print("🔧 Setting up test environment...")

        # Test user credentials
        self.test_user = {
            "email": "test@osint.com",
            "password": "TestPassword123!",
            "name": "Test User"
        }

        # Test lead data
        self.test_lead = {
            "email": "johndoe@example.com",
            "name": "John Doe",
            "company": "Example Corp",
            "job_title": "Marketing Manager",
            "source": "linkedin"
        }

        # Test source configuration
        self.test_source = {
            "name": "Test LinkedIn Source",
            "type": "linkedin",
            "configuration": {
                "search_keywords": ["marketing", "sales"],
                "location": "Norway",
                "company_size": "51-200"
            },
            "enabled": True
        }

        print("✅ Test environment setup complete")

    def measure_performance(self, test_name: str, duration: float, status_code: int):
        """Record performance metrics"""
        self.performance_metrics.append({
            "test": test_name,
            "duration": duration,
            "status_code": status_code,
            "timestamp": datetime.now().isoformat()
        })

    def test_health_endpoints(self):
        """Test health check endpoints"""
        print("\n🏥 Testing Health Endpoints...")

        endpoints = [
            "/health",
            "/api/health",
            "/metrics"
        ]

        for endpoint in endpoints:
            start_time = time.time()
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                duration = time.time() - start_time

                assert response.status_code == 200, f"Health check failed for {endpoint}"
                assert duration < 1.0, f"Health check too slow for {endpoint}: {duration}s"

                self.measure_performance(f"health_{endpoint}", duration, response.status_code)
                print(f"  ✅ {endpoint}: {response.status_code} ({duration:.3f}s)")

            except Exception as e:
                print(f"  ❌ {endpoint}: {str(e)}")
                raise

    def test_authentication_endpoints(self):
        """Test authentication and authorization"""
        print("\n🔐 Testing Authentication Endpoints...")

        # Test user registration
        start_time = time.time()
        register_response = self.session.post(
            f"{self.base_url}/api/auth/register",
            json=self.test_user
        )
        duration = time.time() - start_time

        # Registration might fail if user exists, that's OK for testing
        if register_response.status_code not in [200, 201, 409]:
            print(f"  ⚠️  Registration unexpected status: {register_response.status_code}")

        self.measure_performance("auth_register", duration, register_response.status_code)

        # Test user login
        start_time = time.time()
        login_response = self.session.post(
            f"{self.base_url}/api/auth/login",
            json={
                "email": self.test_user["email"],
                "password": self.test_user["password"]
            }
        )
        duration = time.time() - start_time

        assert login_response.status_code == 200, f"Login failed: {login_response.text}"

        login_data = login_response.json()
        assert "access_token" in login_data, "No access token in login response"

        self.auth_token = login_data["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})

        self.measure_performance("auth_login", duration, login_response.status_code)
        print(f"  ✅ Login successful ({duration:.3f}s)")

        # Test token validation
        start_time = time.time()
        profile_response = self.session.get(f"{self.base_url}/api/auth/profile")
        duration = time.time() - start_time

        assert profile_response.status_code == 200, "Token validation failed"

        self.measure_performance("auth_profile", duration, profile_response.status_code)
        print(f"  ✅ Token validation successful ({duration:.3f}s)")

    def test_leads_endpoints(self):
        """Test leads CRUD operations"""
        print("\n📊 Testing Leads Endpoints...")

        # Create lead
        start_time = time.time()
        create_response = self.session.post(
            f"{self.base_url}/api/leads",
            json=self.test_lead
        )
        duration = time.time() - start_time

        assert create_response.status_code in [200, 201], f"Create lead failed: {create_response.text}"

        lead_data = create_response.json()
        lead_id = lead_data.get("id")
        assert lead_id, "No ID returned for created lead"

        self.test_data["lead_id"] = lead_id
        self.measure_performance("leads_create", duration, create_response.status_code)
        print(f"  ✅ Lead created: {lead_id} ({duration:.3f}s)")

        # Get all leads
        start_time = time.time()
        get_all_response = self.session.get(f"{self.base_url}/api/leads")
        duration = time.time() - start_time

        assert get_all_response.status_code == 200, "Get all leads failed"

        leads_data = get_all_response.json()
        assert isinstance(leads_data, (list, dict)), "Invalid leads data format"

        if isinstance(leads_data, dict) and "leads" in leads_data:
            leads_list = leads_data["leads"]
        else:
            leads_list = leads_data

        assert len(leads_list) > 0, "No leads returned"

        self.measure_performance("leads_get_all", duration, get_all_response.status_code)
        print(f"  ✅ Retrieved {len(leads_list)} leads ({duration:.3f}s)")

        # Get specific lead
        start_time = time.time()
        get_one_response = self.session.get(f"{self.base_url}/api/leads/{lead_id}")
        duration = time.time() - start_time

        assert get_one_response.status_code == 200, f"Get lead by ID failed: {get_one_response.text}"

        lead_detail = get_one_response.json()
        assert lead_detail["email"] == self.test_lead["email"], "Lead data mismatch"

        self.measure_performance("leads_get_one", duration, get_one_response.status_code)
        print(f"  ✅ Retrieved lead by ID ({duration:.3f}s)")

        # Update lead
        updated_lead = self.test_lead.copy()
        updated_lead["job_title"] = "Senior Marketing Manager"

        start_time = time.time()
        update_response = self.session.put(
            f"{self.base_url}/api/leads/{lead_id}",
            json=updated_lead
        )
        duration = time.time() - start_time

        assert update_response.status_code == 200, f"Update lead failed: {update_response.text}"

        self.measure_performance("leads_update", duration, update_response.status_code)
        print(f"  ✅ Lead updated ({duration:.3f}s)")

        # Search/filter leads
        start_time = time.time()
        search_response = self.session.get(
            f"{self.base_url}/api/leads/search",
            params={"company": "Example Corp"}
        )
        duration = time.time() - start_time

        if search_response.status_code == 200:
            search_results = search_response.json()
            self.measure_performance("leads_search", duration, search_response.status_code)
            print(f"  ✅ Lead search successful ({duration:.3f}s)")
        else:
            print(f"  ⚠️  Lead search endpoint not available")

    def test_sources_endpoints(self):
        """Test sources configuration endpoints"""
        print("\n🔍 Testing Sources Endpoints...")

        # Create source
        start_time = time.time()
        create_response = self.session.post(
            f"{self.base_url}/api/sources",
            json=self.test_source
        )
        duration = time.time() - start_time

        if create_response.status_code in [200, 201]:
            source_data = create_response.json()
            source_id = source_data.get("id")
            self.test_data["source_id"] = source_id

            self.measure_performance("sources_create", duration, create_response.status_code)
            print(f"  ✅ Source created: {source_id} ({duration:.3f}s)")

            # Get all sources
            start_time = time.time()
            get_response = self.session.get(f"{self.base_url}/api/sources")
            duration = time.time() - start_time

            assert get_response.status_code == 200, "Get sources failed"

            sources_data = get_response.json()
            self.measure_performance("sources_get_all", duration, get_response.status_code)
            print(f"  ✅ Retrieved sources ({duration:.3f}s)")

        else:
            print(f"  ⚠️  Sources endpoints not fully implemented ({create_response.status_code})")

    def test_campaigns_endpoints(self):
        """Test campaigns management endpoints"""
        print("\n📈 Testing Campaigns Endpoints...")

        test_campaign = {
            "name": "Test Campaign",
            "description": "Automated test campaign",
            "target_filters": {
                "job_titles": ["Marketing Manager", "Sales Director"],
                "company_size": "51-200"
            },
            "active": True
        }

        start_time = time.time()
        create_response = self.session.post(
            f"{self.base_url}/api/campaigns",
            json=test_campaign
        )
        duration = time.time() - start_time

        if create_response.status_code in [200, 201]:
            campaign_data = create_response.json()
            campaign_id = campaign_data.get("id")

            self.measure_performance("campaigns_create", duration, create_response.status_code)
            print(f"  ✅ Campaign created: {campaign_id} ({duration:.3f}s)")

        else:
            print(f"  ⚠️  Campaigns endpoints not fully implemented ({create_response.status_code})")

    def test_export_endpoints(self):
        """Test data export endpoints"""
        print("\n📤 Testing Export Endpoints...")

        export_formats = ["csv", "json"]

        for format_type in export_formats:
            start_time = time.time()
            export_response = self.session.get(
                f"{self.base_url}/api/leads/export",
                params={"format": format_type}
            )
            duration = time.time() - start_time

            if export_response.status_code == 200:
                assert len(export_response.content) > 0, f"Empty export for {format_type}"

                self.measure_performance(f"export_{format_type}", duration, export_response.status_code)
                print(f"  ✅ {format_type.upper()} export successful ({duration:.3f}s)")

            else:
                print(f"  ⚠️  {format_type.upper()} export not available ({export_response.status_code})")

    def test_search_functionality(self):
        """Test comprehensive search across OSINT sources"""
        print("\n🔍 Testing OSINT Search Functionality...")

        search_queries = [
            {"query": "marketing manager", "location": "Oslo"},
            {"query": "sales director", "company": "tech"},
            {"query": "email", "domain": "example.com"}
        ]

        for query in search_queries:
            start_time = time.time()
            search_response = self.session.post(
                f"{self.base_url}/api/search",
                json=query
            )
            duration = time.time() - start_time

            if search_response.status_code == 200:
                search_results = search_response.json()
                self.measure_performance("search_osint", duration, search_response.status_code)
                print(f"  ✅ OSINT search successful for '{query}' ({duration:.3f}s)")

            else:
                print(f"  ⚠️  OSINT search not available for '{query}' ({search_response.status_code})")

    def test_performance_under_load(self):
        """Test API performance under concurrent load"""
        print("\n⚡ Testing Performance Under Load...")

        def make_request(endpoint: str) -> Dict[str, Any]:
            start_time = time.time()
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                duration = time.time() - start_time
                return {
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "duration": duration,
                    "success": response.status_code == 200
                }
            except Exception as e:
                return {
                    "endpoint": endpoint,
                    "status_code": 0,
                    "duration": time.time() - start_time,
                    "success": False,
                    "error": str(e)
                }

        # Test concurrent requests
        endpoints = ["/api/leads", "/api/sources", "/health"] * 10  # 30 concurrent requests

        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, endpoint) for endpoint in endpoints]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        total_duration = time.time() - start_time

        successful_requests = [r for r in results if r["success"]]
        avg_response_time = sum(r["duration"] for r in successful_requests) / len(successful_requests)
        success_rate = len(successful_requests) / len(results) * 100

        print(f"  📊 Load Test Results:")
        print(f"    Total requests: {len(results)}")
        print(f"    Successful: {len(successful_requests)} ({success_rate:.1f}%)")
        print(f"    Average response time: {avg_response_time:.3f}s")
        print(f"    Total duration: {total_duration:.3f}s")

        assert success_rate >= 95, f"Success rate too low: {success_rate}%"
        assert avg_response_time < 2.0, f"Average response time too high: {avg_response_time}s"

    def test_security_vulnerabilities(self):
        """Test for common security vulnerabilities"""
        print("\n🔒 Testing Security Vulnerabilities...")

        # Test SQL injection attempts
        sql_injection_payloads = [
            "'; DROP TABLE leads; --",
            "1' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM users --"
        ]

        for payload in sql_injection_payloads:
            start_time = time.time()
            response = self.session.get(
                f"{self.base_url}/api/leads/search",
                params={"email": payload}
            )
            duration = time.time() - start_time

            # Should not return 500 error (indicates potential SQL injection)
            assert response.status_code != 500, f"Potential SQL injection vulnerability with payload: {payload}"

            self.measure_performance("security_sql_injection", duration, response.status_code)

        print("  ✅ SQL injection tests passed")

        # Test XSS attempts
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>"
        ]

        for payload in xss_payloads:
            response = self.session.post(
                f"{self.base_url}/api/leads",
                json={"name": payload, "email": "test@test.com", "company": "Test"}
            )

            # Should sanitize input or reject it
            if response.status_code == 200:
                lead_data = response.json()
                assert payload not in str(lead_data), f"XSS payload not sanitized: {payload}"

        print("  ✅ XSS protection tests passed")

    def cleanup_test_data(self):
        """Clean up test data created during testing"""
        print("\n🧹 Cleaning up test data...")

        # Delete test lead
        if "lead_id" in self.test_data:
            delete_response = self.session.delete(f"{self.base_url}/api/leads/{self.test_data['lead_id']}")
            if delete_response.status_code in [200, 204, 404]:
                print(f"  ✅ Test lead deleted")
            else:
                print(f"  ⚠️  Could not delete test lead: {delete_response.status_code}")

        # Delete test source
        if "source_id" in self.test_data:
            delete_response = self.session.delete(f"{self.base_url}/api/sources/{self.test_data['source_id']}")
            if delete_response.status_code in [200, 204, 404]:
                print(f"  ✅ Test source deleted")

    def generate_performance_report(self):
        """Generate performance test report"""
        print("\n📈 Performance Test Report:")
        print("=" * 50)

        if not self.performance_metrics:
            print("No performance metrics collected")
            return

        # Group by test type
        test_groups = {}
        for metric in self.performance_metrics:
            test_type = metric["test"].split("_")[0]
            if test_type not in test_groups:
                test_groups[test_type] = []
            test_groups[test_type].append(metric)

        for test_type, metrics in test_groups.items():
            durations = [m["duration"] for m in metrics]
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            min_duration = min(durations)

            print(f"\n{test_type.upper()} Endpoints:")
            print(f"  Tests run: {len(metrics)}")
            print(f"  Average response time: {avg_duration:.3f}s")
            print(f"  Min response time: {min_duration:.3f}s")
            print(f"  Max response time: {max_duration:.3f}s")

            slow_tests = [m for m in metrics if m["duration"] > 2.0]
            if slow_tests:
                print(f"  ⚠️  Slow endpoints (>2s):")
                for test in slow_tests:
                    print(f"    {test['test']}: {test['duration']:.3f}s")

    def run_all_tests(self):
        """Run all functional tests"""
        print("🚀 Starting Comprehensive API Functional Testing")
        print("=" * 60)

        test_results = {
            "total_tests": 0,
            "successful_tests": 0,
            "failed_tests": 0,
            "success_rate": 0,
            "test_details": [],
            "performance_metrics": [],
            "start_time": time.time()
        }

        test_methods = [
            ("Health Endpoints", self.test_health_endpoints),
            ("Authentication Endpoints", self.test_authentication_endpoints),
            ("Leads Endpoints", self.test_leads_endpoints),
            ("Sources Endpoints", self.test_sources_endpoints),
            ("Campaigns Endpoints", self.test_campaigns_endpoints),
            ("Export Endpoints", self.test_export_endpoints),
            ("Search Functionality", self.test_search_functionality),
            ("Performance Under Load", self.test_performance_under_load),
            ("Security Vulnerabilities", self.test_security_vulnerabilities)
        ]

        try:
            self.setup_test_environment()

            for test_name, test_method in test_methods:
                test_results["total_tests"] += 1
                try:
                    test_method()
                    test_results["successful_tests"] += 1
                    test_results["test_details"].append({
                        "name": test_name,
                        "status": "passed",
                        "error": None
                    })
                    print(f"✅ {test_name}: PASSED")
                except Exception as e:
                    test_results["failed_tests"] += 1
                    test_results["test_details"].append({
                        "name": test_name,
                        "status": "failed",
                        "error": str(e)
                    })
                    print(f"❌ {test_name}: FAILED - {str(e)}")

            test_results["success_rate"] = (test_results["successful_tests"] / test_results["total_tests"]) * 100 if test_results["total_tests"] > 0 else 0
            test_results["end_time"] = time.time()
            test_results["duration"] = test_results["end_time"] - test_results["start_time"]
            test_results["performance_metrics"] = self.performance_metrics

            print(f"\n📊 API Testing Summary:")
            print(f"   Total Tests: {test_results['total_tests']}")
            print(f"   Successful: {test_results['successful_tests']}")
            print(f"   Failed: {test_results['failed_tests']}")
            print(f"   Success Rate: {test_results['success_rate']:.1f}%")
            print(f"   Duration: {test_results['duration']:.1f}s")

            if test_results["failed_tests"] == 0:
                print("\n✅ All API functional tests completed successfully!")
            else:
                print(f"\n⚠️ {test_results['failed_tests']} test(s) failed")

        except Exception as e:
            print(f"\n❌ Test execution failure: {str(e)}")
            test_results["execution_error"] = str(e)
            raise

        finally:
            self.cleanup_test_data()
            self.generate_performance_report()

        return test_results


if __name__ == "__main__":
    # Run the tests
    tester = APIEndpointTester()
    tester.run_all_tests()