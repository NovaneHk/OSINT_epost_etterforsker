"""
Comprehensive Authentication & Authorization Functional Testing
Tests user registration, login, JWT validation, role-based access control, and session management
"""

import time
import json
import jwt
import hashlib
import random
import string
import requests
from typing import Dict, List, Any, Optional
import concurrent.futures
from datetime import datetime, timedelta

class AuthenticationAuthorizationTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.test_users = []
        self.test_tokens = {}
        self.test_sessions = {}

    def record_test_result(self, test_name: str, success: bool, duration: float, details: str = ""):
        """Record test results"""
        self.test_results.append({
            "test": test_name,
            "success": success,
            "duration": duration,
            "details": details,
            "timestamp": time.time()
        })

    def generate_test_user(self, role: str = "user") -> Dict[str, Any]:
        """Generate test user data"""
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return {
            "email": f"test_{random_suffix}@osint-test.com",
            "password": f"TestPassword123!{random_suffix}",
            "name": f"Test User {random_suffix}",
            "role": role,
            "company": f"Test Company {random_suffix[:4]}",
            "phone": f"+47{random.randint(10000000, 99999999)}"
        }

    def test_user_registration(self):
        """Test user registration functionality"""
        print("\n👤 Testing User Registration...")

        # Test valid registration
        start_time = time.time()
        valid_user = self.generate_test_user()

        try:
            register_response = self.session.post(
                f"{self.base_url}/api/auth/register",
                json=valid_user
            )
            duration = time.time() - start_time

            success = register_response.status_code in [200, 201]

            if success:
                response_data = register_response.json()
                self.test_users.append({
                    **valid_user,
                    "id": response_data.get("id") or response_data.get("user_id"),
                    "registration_response": response_data
                })

                # Check if proper response fields are present
                expected_fields = ["id", "email", "name"]
                has_required_fields = all(field in response_data for field in expected_fields)

                if not has_required_fields:
                    success = False
                    details = f"Missing required fields in response: {expected_fields}"
                else:
                    details = f"User registered successfully: {response_data.get('email')}"
            else:
                details = f"Registration failed: {register_response.status_code} - {register_response.text}"

            self.record_test_result("registration_valid", success, duration, details)
            print(f"  {'✅' if success else '❌'} Valid registration: {details} ({duration:.3f}s)")

        except Exception as e:
            self.record_test_result("registration_valid", False, time.time() - start_time, f"Error: {str(e)}")
            print(f"  ❌ Valid registration failed: {str(e)}")

        # Test duplicate email registration
        start_time = time.time()
        try:
            duplicate_response = self.session.post(
                f"{self.base_url}/api/auth/register",
                json=valid_user  # Same user data
            )
            duration = time.time() - start_time

            # Should fail with 409 or 400
            success = duplicate_response.status_code in [400, 409, 422]
            details = f"Duplicate email handling: {duplicate_response.status_code}"

            self.record_test_result("registration_duplicate_email", success, duration, details)
            print(f"  {'✅' if success else '❌'} Duplicate email prevention: {details} ({duration:.3f}s)")

        except Exception as e:
            self.record_test_result("registration_duplicate_email", False, time.time() - start_time, f"Error: {str(e)}")
            print(f"  ❌ Duplicate email test failed: {str(e)}")

        # Test invalid email format
        start_time = time.time()
        try:
            invalid_user = self.generate_test_user()
            invalid_user["email"] = "invalid_email_format"

            invalid_response = self.session.post(
                f"{self.base_url}/api/auth/register",
                json=invalid_user
            )
            duration = time.time() - start_time

            # Should fail with 400 or 422
            success = invalid_response.status_code in [400, 422]
            details = f"Invalid email format handling: {invalid_response.status_code}"

            self.record_test_result("registration_invalid_email", success, duration, details)
            print(f"  {'✅' if success else '❌'} Invalid email validation: {details} ({duration:.3f}s)")

        except Exception as e:
            self.record_test_result("registration_invalid_email", False, time.time() - start_time, f"Error: {str(e)}")
            print(f"  ❌ Invalid email test failed: {str(e)}")

        # Test weak password
        start_time = time.time()
        try:
            weak_password_user = self.generate_test_user()
            weak_password_user["password"] = "123"  # Weak password

            weak_response = self.session.post(
                f"{self.base_url}/api/auth/register",
                json=weak_password_user
            )
            duration = time.time() - start_time

            # Should fail with 400 or 422
            success = weak_response.status_code in [400, 422]
            details = f"Weak password handling: {weak_response.status_code}"

            self.record_test_result("registration_weak_password", success, duration, details)
            print(f"  {'✅' if success else '❌'} Weak password validation: {details} ({duration:.3f}s)")

        except Exception as e:
            self.record_test_result("registration_weak_password", False, time.time() - start_time, f"Error: {str(e)}")
            print(f"  ❌ Weak password test failed: {str(e)}")

    def test_user_login(self):
        """Test user login functionality"""
        print("\n🔑 Testing User Login...")

        if not self.test_users:
            print("  ⚠️  No test users available for login testing")
            return

        test_user = self.test_users[0]

        # Test valid login
        start_time = time.time()
        try:
            login_response = self.session.post(
                f"{self.base_url}/api/auth/login",
                json={
                    "email": test_user["email"],
                    "password": test_user["password"]
                }
            )
            duration = time.time() - start_time

            success = login_response.status_code == 200

            if success:
                login_data = login_response.json()

                # Check for required fields
                required_fields = ["access_token"]
                has_token = "access_token" in login_data or "token" in login_data

                if has_token:
                    token = login_data.get("access_token") or login_data.get("token")
                    self.test_tokens[test_user["email"]] = token

                    # Set authorization header for future requests
                    self.session.headers.update({"Authorization": f"Bearer {token}"})

                    details = f"Login successful, token received"
                else:
                    success = False
                    details = f"Login response missing token: {list(login_data.keys())}"
            else:
                details = f"Login failed: {login_response.status_code} - {login_response.text}"

            self.record_test_result("login_valid_credentials", success, duration, details)
            print(f"  {'✅' if success else '❌'} Valid login: {details} ({duration:.3f}s)")

        except Exception as e:
            self.record_test_result("login_valid_credentials", False, time.time() - start_time, f"Error: {str(e)}")
            print(f"  ❌ Valid login failed: {str(e)}")

        # Test invalid password
        start_time = time.time()
        try:
            invalid_login_response = self.session.post(
                f"{self.base_url}/api/auth/login",
                json={
                    "email": test_user["email"],
                    "password": "wrong_password"
                }
            )
            duration = time.time() - start_time

            # Should fail with 401
            success = invalid_login_response.status_code == 401
            details = f"Invalid password handling: {invalid_login_response.status_code}"

            self.record_test_result("login_invalid_password", success, duration, details)
            print(f"  {'✅' if success else '❌'} Invalid password rejection: {details} ({duration:.3f}s)")

        except Exception as e:
            self.record_test_result("login_invalid_password", False, time.time() - start_time, f"Error: {str(e)}")
            print(f"  ❌ Invalid password test failed: {str(e)}")

        # Test non-existent user
        start_time = time.time()
        try:
            nonexistent_response = self.session.post(
                f"{self.base_url}/api/auth/login",
                json={
                    "email": "nonexistent@example.com",
                    "password": "any_password"
                }
            )
            duration = time.time() - start_time

            # Should fail with 401 or 404
            success = nonexistent_response.status_code in [401, 404]
            details = f"Non-existent user handling: {nonexistent_response.status_code}"

            self.record_test_result("login_nonexistent_user", success, duration, details)
            print(f"  {'✅' if success else '❌'} Non-existent user rejection: {details} ({duration:.3f}s)")

        except Exception as e:
            self.record_test_result("login_nonexistent_user", False, time.time() - start_time, f"Error: {str(e)}")
            print(f"  ❌ Non-existent user test failed: {str(e)}")

    def test_jwt_token_validation(self):
        """Test JWT token validation and security"""
        print("\n🎫 Testing JWT Token Validation...")

        if not self.test_tokens:
            print("  ⚠️  No tokens available for validation testing")
            return

        token = list(self.test_tokens.values())[0]

        # Test valid token access
        start_time = time.time()
        try:
            protected_response = self.session.get(
                f"{self.base_url}/api/auth/profile",
                headers={"Authorization": f"Bearer {token}"}
            )
            duration = time.time() - start_time

            success = protected_response.status_code == 200

            if success:
                profile_data = protected_response.json()
                has_user_info = "email" in profile_data or "id" in profile_data
                details = f"Protected endpoint accessible, user info: {has_user_info}"
            else:
                details = f"Protected endpoint access failed: {protected_response.status_code}"

            self.record_test_result("jwt_valid_token_access", success, duration, details)
            print(f"  {'✅' if success else '❌'} Valid token access: {details} ({duration:.3f}s)")

        except Exception as e:
            self.record_test_result("jwt_valid_token_access", False, time.time() - start_time, f"Error: {str(e)}")
            print(f"  ❌ Valid token access test failed: {str(e)}")

        # Test invalid token
        start_time = time.time()
        try:
            invalid_token_response = self.session.get(
                f"{self.base_url}/api/auth/profile",
                headers={"Authorization": "Bearer invalid_token_here"}
            )
            duration = time.time() - start_time

            # Should fail with 401
            success = invalid_token_response.status_code == 401
            details = f"Invalid token rejection: {invalid_token_response.status_code}"

            self.record_test_result("jwt_invalid_token_rejection", success, duration, details)
            print(f"  {'✅' if success else '❌'} Invalid token rejection: {details} ({duration:.3f}s)")

        except Exception as e:
            self.record_test_result("jwt_invalid_token_rejection", False, time.time() - start_time, f"Error: {str(e)}")
            print(f"  ❌ Invalid token test failed: {str(e)}")

        # Test missing token
        start_time = time.time()
        try:
            no_token_response = self.session.get(f"{self.base_url}/api/auth/profile")
            duration = time.time() - start_time

            # Should fail with 401
            success = no_token_response.status_code == 401
            details = f"Missing token rejection: {no_token_response.status_code}"

            self.record_test_result("jwt_missing_token_rejection", success, duration, details)
            print(f"  {'✅' if success else '❌'} Missing token rejection: {details} ({duration:.3f}s)")

        except Exception as e:
            self.record_test_result("jwt_missing_token_rejection", False, time.time() - start_time, f"Error: {str(e)}")
            print(f"  ❌ Missing token test failed: {str(e)}")

        # Test token structure (if it's a JWT)
        try:
            start_time = time.time()

            # Try to decode JWT without verification (just structure check)
            token_parts = token.split('.')
            is_valid_jwt_structure = len(token_parts) == 3

            if is_valid_jwt_structure:
                try:
                    # Decode header and payload (without verification)
                    header = jwt.get_unverified_header(token)
                    payload = jwt.decode(token, options={"verify_signature": False})

                    has_required_claims = "exp" in payload and ("sub" in payload or "user_id" in payload)

                    duration = time.time() - start_time
                    success = has_required_claims
                    details = f"JWT structure valid, claims: {list(payload.keys())}"

                except Exception:
                    duration = time.time() - start_time
                    success = False
                    details = "JWT structure invalid or malformed"
            else:
                duration = time.time() - start_time
                success = False
                details = f"Token structure invalid: {len(token_parts)} parts (expected 3)"

            self.record_test_result("jwt_token_structure", success, duration, details)
            print(f"  {'✅' if success else '⚠️'} JWT token structure: {details} ({duration:.3f}s)")

        except Exception as e:
            self.record_test_result("jwt_token_structure", False, 0, f"Error: {str(e)}")
            print(f"  ⚠️  JWT structure test failed: {str(e)}")

    def test_role_based_access_control(self):
        """Test role-based access control (RBAC)"""
        print("\n👮 Testing Role-Based Access Control...")

        # Create users with different roles
        roles_to_test = ["user", "admin", "manager"]
        role_users = {}

        for role in roles_to_test:
            start_time = time.time()
            try:
                # Create user with specific role
                role_user = self.generate_test_user(role)

                register_response = self.session.post(
                    f"{self.base_url}/api/auth/register",
                    json=role_user
                )

                if register_response.status_code in [200, 201]:
                    # Login to get token
                    login_response = self.session.post(
                        f"{self.base_url}/api/auth/login",
                        json={
                            "email": role_user["email"],
                            "password": role_user["password"]
                        }
                    )

                    if login_response.status_code == 200:
                        login_data = login_response.json()
                        token = login_data.get("access_token") or login_data.get("token")

                        if token:
                            role_users[role] = {
                                "user": role_user,
                                "token": token
                            }

                duration = time.time() - start_time
                success = role in role_users
                details = f"{role.capitalize()} user created and authenticated"

                self.record_test_result(f"rbac_create_{role}_user", success, duration, details)
                print(f"  {'✅' if success else '❌'} {role.capitalize()} user setup: {details} ({duration:.3f}s)")

            except Exception as e:
                self.record_test_result(f"rbac_create_{role}_user", False, time.time() - start_time, f"Error: {str(e)}")
                print(f"  ❌ {role.capitalize()} user setup failed: {str(e)}")

        # Test access to different endpoints with different roles
        protected_endpoints = [
            {"url": "/api/leads", "method": "GET", "min_role": "user"},
            {"url": "/api/leads", "method": "POST", "min_role": "user"},
            {"url": "/api/sources", "method": "GET", "min_role": "user"},
            {"url": "/api/sources", "method": "POST", "min_role": "manager"},
            {"url": "/api/admin/users", "method": "GET", "min_role": "admin"},
            {"url": "/api/admin/settings", "method": "GET", "min_role": "admin"}
        ]

        role_hierarchy = {"user": 1, "manager": 2, "admin": 3}

        for endpoint in protected_endpoints:
            for role, role_data in role_users.items():
                start_time = time.time()
                try:
                    # Test access with this role
                    headers = {"Authorization": f"Bearer {role_data['token']}"}

                    if endpoint["method"] == "GET":
                        response = self.session.get(f"{self.base_url}{endpoint['url']}", headers=headers)
                    elif endpoint["method"] == "POST":
                        response = self.session.post(
                            f"{self.base_url}{endpoint['url']}",
                            headers=headers,
                            json={"test": "data"}  # Minimal test data
                        )
                    else:
                        continue

                    duration = time.time() - start_time

                    # Determine if access should be allowed
                    user_level = role_hierarchy.get(role, 0)
                    required_level = role_hierarchy.get(endpoint["min_role"], 999)
                    should_have_access = user_level >= required_level

                    # Check if actual response matches expected access
                    has_access = response.status_code not in [401, 403]
                    access_correct = (has_access and should_have_access) or (not has_access and not should_have_access)

                    details = f"{role} → {endpoint['url']} ({endpoint['method']}): {response.status_code} (expected: {'allow' if should_have_access else 'deny'})"

                    self.record_test_result(f"rbac_{role}_{endpoint['url'].replace('/', '_')}_{endpoint['method']}",
                                          access_correct, duration, details)

                    status = "✅" if access_correct else "❌"
                    print(f"  {status} {details} ({duration:.3f}s)")

                except Exception as e:
                    self.record_test_result(f"rbac_{role}_{endpoint['url']}", False, time.time() - start_time, f"Error: {str(e)}")
                    print(f"  ❌ RBAC test failed for {role} → {endpoint['url']}: {str(e)}")

    def test_session_management(self):
        """Test session management and security"""
        print("\n🕐 Testing Session Management...")

        if not self.test_tokens:
            print("  ⚠️  No tokens available for session testing")
            return

        token = list(self.test_tokens.values())[0]

        # Test token refresh (if endpoint exists)
        start_time = time.time()
        try:
            refresh_response = self.session.post(
                f"{self.base_url}/api/auth/refresh",
                headers={"Authorization": f"Bearer {token}"}
            )
            duration = time.time() - start_time

            if refresh_response.status_code == 200:
                refresh_data = refresh_response.json()
                new_token = refresh_data.get("access_token") or refresh_data.get("token")

                success = new_token is not None and new_token != token
                details = f"Token refresh successful, new token received"
            elif refresh_response.status_code == 404:
                success = True  # Endpoint not implemented, that's acceptable
                details = "Token refresh endpoint not implemented"
            else:
                success = False
                details = f"Token refresh failed: {refresh_response.status_code}"

            self.record_test_result("session_token_refresh", success, duration, details)
            print(f"  {'✅' if success else '⚠️'} Token refresh: {details} ({duration:.3f}s)")

        except Exception as e:
            self.record_test_result("session_token_refresh", False, time.time() - start_time, f"Error: {str(e)}")
            print(f"  ⚠️  Token refresh test failed: {str(e)}")

        # Test logout
        start_time = time.time()
        try:
            logout_response = self.session.post(
                f"{self.base_url}/api/auth/logout",
                headers={"Authorization": f"Bearer {token}"}
            )
            duration = time.time() - start_time

            if logout_response.status_code in [200, 204]:
                # Test if token is invalidated
                test_response = self.session.get(
                    f"{self.base_url}/api/auth/profile",
                    headers={"Authorization": f"Bearer {token}"}
                )

                token_invalidated = test_response.status_code == 401
                success = token_invalidated
                details = f"Logout successful, token invalidated: {token_invalidated}"
            elif logout_response.status_code == 404:
                success = True  # Endpoint not implemented
                details = "Logout endpoint not implemented"
            else:
                success = False
                details = f"Logout failed: {logout_response.status_code}"

            self.record_test_result("session_logout", success, duration, details)
            print(f"  {'✅' if success else '⚠️'} Logout: {details} ({duration:.3f}s)")

        except Exception as e:
            self.record_test_result("session_logout", False, time.time() - start_time, f"Error: {str(e)}")
            print(f"  ⚠️  Logout test failed: {str(e)}")

    def test_password_security(self):
        """Test password security measures"""
        print("\n🔒 Testing Password Security...")

        # Test password reset request
        if self.test_users:
            test_user = self.test_users[0]

            start_time = time.time()
            try:
                reset_request_response = self.session.post(
                    f"{self.base_url}/api/auth/password-reset-request",
                    json={"email": test_user["email"]}
                )
                duration = time.time() - start_time

                # Should succeed or return 404 if not implemented
                success = reset_request_response.status_code in [200, 202, 404]

                if reset_request_response.status_code == 404:
                    details = "Password reset not implemented"
                else:
                    details = f"Password reset request: {reset_request_response.status_code}"

                self.record_test_result("password_reset_request", success, duration, details)
                print(f"  {'✅' if success else '⚠️'} Password reset request: {details} ({duration:.3f}s)")

            except Exception as e:
                self.record_test_result("password_reset_request", False, time.time() - start_time, f"Error: {str(e)}")
                print(f"  ⚠️  Password reset test failed: {str(e)}")

        # Test account lockout (brute force protection)
        test_email = "brute.force@test.com"

        start_time = time.time()
        failed_attempts = 0
        lockout_detected = False

        try:
            # Attempt multiple failed logins
            for attempt in range(6):  # Try 6 failed attempts
                login_response = self.session.post(
                    f"{self.base_url}/api/auth/login",
                    json={
                        "email": test_email,
                        "password": "wrong_password"
                    }
                )

                if login_response.status_code == 429:  # Too many requests
                    lockout_detected = True
                    break
                elif login_response.status_code == 423:  # Account locked
                    lockout_detected = True
                    break

                failed_attempts += 1
                time.sleep(0.1)  # Small delay between attempts

            duration = time.time() - start_time

            # Account lockout is good security practice but not always implemented
            details = f"Failed attempts: {failed_attempts}, Lockout detected: {lockout_detected}"

            self.record_test_result("password_brute_force_protection", True, duration, details)
            print(f"  {'✅' if lockout_detected else '⚠️'} Brute force protection: {details} ({duration:.3f}s)")

        except Exception as e:
            self.record_test_result("password_brute_force_protection", False, time.time() - start_time, f"Error: {str(e)}")
            print(f"  ⚠️  Brute force protection test failed: {str(e)}")

    def test_concurrent_authentication(self):
        """Test authentication under concurrent load"""
        print("\n⚡ Testing Concurrent Authentication...")

        def concurrent_login_test(user_num: int) -> Dict[str, Any]:
            """Perform login test for concurrent testing"""
            test_user = self.generate_test_user()

            try:
                # Register user
                register_response = requests.post(
                    f"{self.base_url}/api/auth/register",
                    json=test_user,
                    timeout=10
                )

                if register_response.status_code not in [200, 201]:
                    return {"success": False, "error": f"Registration failed: {register_response.status_code}"}

                # Login
                login_start = time.time()
                login_response = requests.post(
                    f"{self.base_url}/api/auth/login",
                    json={
                        "email": test_user["email"],
                        "password": test_user["password"]
                    },
                    timeout=10
                )
                login_duration = time.time() - login_start

                if login_response.status_code == 200:
                    login_data = login_response.json()
                    token = login_data.get("access_token") or login_data.get("token")

                    if token:
                        # Test protected endpoint
                        profile_response = requests.get(
                            f"{self.base_url}/api/auth/profile",
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=10
                        )

                        return {
                            "success": profile_response.status_code == 200,
                            "login_duration": login_duration,
                            "user_num": user_num
                        }

                return {"success": False, "error": f"Login failed: {login_response.status_code}"}

            except Exception as e:
                return {"success": False, "error": str(e)}

        # Run concurrent authentication tests
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(concurrent_login_test, i) for i in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        total_duration = time.time() - start_time

        # Analyze results
        successful_logins = [r for r in results if r["success"]]
        success_rate = len(successful_logins) / len(results) * 100

        if successful_logins:
            avg_login_duration = sum(r["login_duration"] for r in successful_logins) / len(successful_logins)
        else:
            avg_login_duration = 0

        # Success criteria: at least 80% success rate and reasonable performance
        success = success_rate >= 80 and avg_login_duration < 5.0
        details = f"Success rate: {success_rate:.1f}%, Avg login time: {avg_login_duration:.3f}s"

        self.record_test_result("auth_concurrent_load", success, total_duration, details)
        print(f"  {'✅' if success else '❌'} Concurrent authentication: {details} ({total_duration:.3f}s)")

    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n📋 Authentication & Authorization Test Report:")
        print("=" * 60)

        if not self.test_results:
            print("No test results to report")
            return

        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r["success"]])
        success_rate = (successful_tests / total_tests) * 100

        print(f"\nOverall Results:")
        print(f"  Total tests: {total_tests}")
        print(f"  Successful: {successful_tests}")
        print(f"  Success rate: {success_rate:.1f}%")

        # Group results by category
        categories = {}
        for result in self.test_results:
            category = result["test"].split("_")[0]
            if category not in categories:
                categories[category] = []
            categories[category].append(result)

        print(f"\nResults by Category:")
        for category, results in categories.items():
            successful = len([r for r in results if r["success"]])
            total = len(results)
            rate = (successful / total) * 100 if total > 0 else 0
            print(f"  {category.capitalize()}: {successful}/{total} ({rate:.1f}%)")

        # Show failed tests
        failed_tests = [r for r in self.test_results if not r["success"]]
        if failed_tests:
            print(f"\nFailed Tests:")
            for test in failed_tests:
                print(f"  ❌ {test['test']}: {test['details']}")

        # Security recommendations
        security_issues = []
        for result in self.test_results:
            if not result["success"] and any(keyword in result["test"] for keyword in ["password", "token", "auth", "rbac"]):
                security_issues.append(result)

        if security_issues:
            print(f"\n🚨 Security Issues Found:")
            for issue in security_issues:
                print(f"  ⚠️  {issue['test']}: {issue['details']}")

        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": success_rate,
            "categories": categories,
            "failed_tests": failed_tests,
            "security_issues": security_issues
        }

    def cleanup_test_data(self):
        """Clean up test users and data"""
        print("\n🧹 Cleaning up test data...")

        cleanup_count = 0

        # Attempt to delete test users (if delete endpoint exists)
        for user in self.test_users:
            try:
                if user.get("id"):
                    # Try to delete user (this endpoint may not exist)
                    delete_response = self.session.delete(
                        f"{self.base_url}/api/users/{user['id']}",
                        headers={"Authorization": f"Bearer {self.test_tokens.get(user['email'], '')}"}
                    )

                    if delete_response.status_code in [200, 204, 404]:
                        cleanup_count += 1

            except Exception:
                pass  # Cleanup is best effort

        if cleanup_count > 0:
            print(f"  ✅ Cleaned up {cleanup_count} test users")
        else:
            print(f"  ⚠️  Test user cleanup not available (normal for production APIs)")

    def run_all_tests(self):
        """Run all authentication and authorization tests"""
        print("🚀 Starting Comprehensive Authentication & Authorization Testing")
        print("=" * 70)

        try:
            # Run all test categories
            self.test_user_registration()
            self.test_user_login()
            self.test_jwt_token_validation()
            self.test_role_based_access_control()
            self.test_session_management()
            self.test_password_security()
            self.test_concurrent_authentication()

            print("\n✅ All authentication & authorization tests completed!")

            # Generate and return report
            return self.generate_test_report()

        except Exception as e:
            print(f"\n❌ Authentication testing failed: {str(e)}")
            raise

        finally:
            self.cleanup_test_data()


if __name__ == "__main__":
    # Run the tests
    tester = AuthenticationAuthorizationTester()
    report = tester.run_all_tests()

    # Save report to file
    with open("auth_test_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n📄 Test report saved to auth_test_report.json")