"""
Comprehensive Frontend Component Functional Testing
Tests React components, UI interactions, and responsive design
"""

import time
import json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class FrontendComponentTester:
    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url
        self.driver = None
        self.wait = None
        self.test_results = []
        self.performance_metrics = []

    def setup_driver(self):
        """Setup Chrome driver with appropriate options"""
        print("🔧 Setting up Chrome driver...")

        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-gpu")

        # Enable logging
        chrome_options.add_argument("--enable-logging")
        chrome_options.add_argument("--log-level=0")

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
            self.wait = WebDriverWait(self.driver, 15)
            print("✅ Chrome driver setup complete")
        except Exception as e:
            print(f"❌ Failed to setup Chrome driver: {str(e)}")
            raise

    def teardown_driver(self):
        """Clean up driver resources"""
        if self.driver:
            self.driver.quit()
            print("🧹 Chrome driver cleaned up")

    def record_test_result(self, test_name: str, success: bool, duration: float, details: str = ""):
        """Record test results"""
        self.test_results.append({
            "test": test_name,
            "success": success,
            "duration": duration,
            "details": details,
            "timestamp": time.time()
        })

    def measure_page_load_time(self, url: str) -> float:
        """Measure page load time"""
        start_time = time.time()
        self.driver.get(url)

        # Wait for page to be fully loaded
        self.wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")

        return time.time() - start_time

    def test_page_accessibility(self):
        """Test page accessibility features"""
        print("\n♿ Testing Page Accessibility...")

        accessibility_tests = [
            {
                "name": "Alt text for images",
                "selector": "img",
                "attribute": "alt",
                "required": True
            },
            {
                "name": "Form labels",
                "selector": "input[type='text'], input[type='email'], input[type='password']",
                "attribute": "aria-label",
                "required": False  # Can also have labels
            },
            {
                "name": "Button accessibility",
                "selector": "button",
                "attribute": "aria-label",
                "required": False  # Text content is also acceptable
            },
            {
                "name": "Navigation landmarks",
                "selector": "nav, [role='navigation']",
                "attribute": None,
                "required": True
            }
        ]

        for test in accessibility_tests:
            start_time = time.time()
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, test["selector"])

                if test["required"] and len(elements) == 0:
                    self.record_test_result(
                        f"accessibility_{test['name']}",
                        False,
                        time.time() - start_time,
                        f"No {test['name']} found"
                    )
                    print(f"  ❌ {test['name']}: No elements found")
                    continue

                accessibility_issues = []
                for element in elements:
                    if test["attribute"]:
                        attr_value = element.get_attribute(test["attribute"])
                        if not attr_value or attr_value.strip() == "":
                            accessibility_issues.append(f"Missing {test['attribute']}")
                    elif test["name"] == "Button accessibility":
                        # Check if button has text content or aria-label
                        text_content = element.text.strip()
                        aria_label = element.get_attribute("aria-label")
                        if not text_content and not aria_label:
                            accessibility_issues.append("Button missing accessible name")

                success = len(accessibility_issues) == 0
                details = f"Issues: {', '.join(accessibility_issues)}" if accessibility_issues else "All elements accessible"

                self.record_test_result(
                    f"accessibility_{test['name']}",
                    success,
                    time.time() - start_time,
                    details
                )

                status = "✅" if success else "⚠️"
                print(f"  {status} {test['name']}: {details}")

            except Exception as e:
                self.record_test_result(
                    f"accessibility_{test['name']}",
                    False,
                    time.time() - start_time,
                    f"Error: {str(e)}"
                )
                print(f"  ❌ {test['name']}: {str(e)}")

    def test_responsive_design(self):
        """Test responsive design across different screen sizes"""
        print("\n📱 Testing Responsive Design...")

        screen_sizes = [
            {"name": "Mobile", "width": 375, "height": 667},
            {"name": "Tablet", "width": 768, "height": 1024},
            {"name": "Desktop", "width": 1920, "height": 1080},
            {"name": "Large Desktop", "width": 2560, "height": 1440}
        ]

        for size in screen_sizes:
            start_time = time.time()
            try:
                # Set window size
                self.driver.set_window_size(size["width"], size["height"])
                time.sleep(1)  # Allow layout to adjust

                # Check if navigation is accessible
                nav_visible = self.driver.execute_script("""
                    const nav = document.querySelector('nav, [data-testid="top-nav"]');
                    if (!nav) return false;
                    const rect = nav.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0;
                """)

                # Check if main content is visible
                content_visible = self.driver.execute_script("""
                    const main = document.querySelector('main, [role="main"], .main-content');
                    if (!main) return true; // If no main element, assume content is visible
                    const rect = main.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0;
                """)

                # Check for horizontal scroll on mobile
                has_horizontal_scroll = self.driver.execute_script("""
                    return document.body.scrollWidth > window.innerWidth;
                """)

                # For mobile, horizontal scroll is usually bad
                scroll_issue = has_horizontal_scroll and size["width"] <= 768

                success = nav_visible and content_visible and not scroll_issue

                issues = []
                if not nav_visible:
                    issues.append("Navigation not visible")
                if not content_visible:
                    issues.append("Main content not visible")
                if scroll_issue:
                    issues.append("Unwanted horizontal scroll")

                details = f"Issues: {', '.join(issues)}" if issues else "Layout responsive"

                self.record_test_result(
                    f"responsive_{size['name'].lower()}",
                    success,
                    time.time() - start_time,
                    details
                )

                status = "✅" if success else "❌"
                print(f"  {status} {size['name']} ({size['width']}x{size['height']}): {details}")

            except Exception as e:
                self.record_test_result(
                    f"responsive_{size['name'].lower()}",
                    False,
                    time.time() - start_time,
                    f"Error: {str(e)}"
                )
                print(f"  ❌ {size['name']}: {str(e)}")

        # Reset to desktop size
        self.driver.set_window_size(1920, 1080)

    def test_navigation_components(self):
        """Test navigation components functionality"""
        print("\n🧭 Testing Navigation Components...")

        start_time = time.time()
        try:
            # Test top navigation
            nav_elements = self.driver.find_elements(By.CSS_SELECTOR, "nav, [data-testid='top-nav']")
            assert len(nav_elements) > 0, "No navigation elements found"

            # Test navigation links
            nav_links = self.driver.find_elements(By.CSS_SELECTOR, "nav a, [data-testid='top-nav'] a")

            clickable_links = 0
            for link in nav_links:
                href = link.get_attribute("href")
                if href and href != "#":
                    clickable_links += 1

            assert clickable_links > 0, "No functional navigation links found"

            # Test user menu (if present)
            user_menu_triggers = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='user-menu'], .user-menu")

            if user_menu_triggers:
                # Try to click user menu
                user_menu_triggers[0].click()
                time.sleep(0.5)

                # Check if dropdown appeared
                dropdown = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='user-dropdown'], .user-dropdown")
                user_menu_works = len(dropdown) > 0
            else:
                user_menu_works = True  # No user menu is also acceptable

            success = user_menu_works
            details = f"Navigation links: {clickable_links}, User menu: {'Working' if user_menu_works else 'Not working'}"

            self.record_test_result("navigation_functionality", success, time.time() - start_time, details)

            status = "✅" if success else "❌"
            print(f"  {status} Navigation functionality: {details}")

        except Exception as e:
            self.record_test_result("navigation_functionality", False, time.time() - start_time, f"Error: {str(e)}")
            print(f"  ❌ Navigation test failed: {str(e)}")

    def test_form_validation(self):
        """Test form validation and user input handling"""
        print("\n📝 Testing Form Validation...")

        # Try to find forms on the page
        forms = self.driver.find_elements(By.TAG_NAME, "form")

        if not forms:
            print("  ⚠️  No forms found on current page")
            return

        for i, form in enumerate(forms):
            start_time = time.time()
            try:
                # Find input fields in the form
                inputs = form.find_elements(By.CSS_SELECTOR, "input[type='text'], input[type='email'], input[type='password']")

                if not inputs:
                    continue

                # Test empty form submission
                submit_buttons = form.find_elements(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")

                if submit_buttons:
                    # Clear all inputs
                    for input_field in inputs:
                        input_field.clear()

                    # Try to submit empty form
                    submit_buttons[0].click()
                    time.sleep(1)

                    # Check for validation messages
                    validation_messages = self.driver.find_elements(By.CSS_SELECTOR,
                        ".error, .error-message, [data-testid*='error'], .text-red-500")

                    has_validation = len(validation_messages) > 0

                    # Check HTML5 validation
                    html5_validation = any(
                        input_field.get_attribute("required") for input_field in inputs
                    )

                    validation_working = has_validation or html5_validation

                    details = f"Form {i+1}: Validation messages: {len(validation_messages)}, HTML5 validation: {html5_validation}"

                    self.record_test_result(
                        f"form_validation_{i+1}",
                        validation_working,
                        time.time() - start_time,
                        details
                    )

                    status = "✅" if validation_working else "⚠️"
                    print(f"  {status} {details}")

            except Exception as e:
                self.record_test_result(
                    f"form_validation_{i+1}",
                    False,
                    time.time() - start_time,
                    f"Error: {str(e)}"
                )
                print(f"  ❌ Form {i+1} validation test failed: {str(e)}")

    def test_dashboard_components(self):
        """Test dashboard components and data visualization"""
        print("\n📊 Testing Dashboard Components...")

        # Navigate to dashboard if not already there
        current_url = self.driver.current_url
        if "/dashboard" not in current_url and current_url.endswith("/"):
            dashboard_url = f"{self.base_url}/dashboard"
            load_time = self.measure_page_load_time(dashboard_url)
            print(f"  📍 Navigated to dashboard ({load_time:.3f}s)")

        start_time = time.time()
        try:
            # Check for KPI cards
            kpi_cards = self.driver.find_elements(By.CSS_SELECTOR,
                "[data-testid*='kpi'], .kpi-card, .metric-card, .stat-card")

            # Check for charts/visualizations
            charts = self.driver.find_elements(By.CSS_SELECTOR,
                "canvas, svg, .chart, .visualization, [data-testid*='chart']")

            # Check for data tables
            tables = self.driver.find_elements(By.CSS_SELECTOR,
                "table, .data-table, [data-testid*='table']")

            # Verify dashboard content is loaded
            dashboard_content_loaded = len(kpi_cards) > 0 or len(charts) > 0 or len(tables) > 0

            details = f"KPI cards: {len(kpi_cards)}, Charts: {len(charts)}, Tables: {len(tables)}"

            self.record_test_result(
                "dashboard_components",
                dashboard_content_loaded,
                time.time() - start_time,
                details
            )

            status = "✅" if dashboard_content_loaded else "⚠️"
            print(f"  {status} Dashboard components: {details}")

            # Test interactive elements
            if charts:
                try:
                    # Try to interact with first chart
                    chart = charts[0]
                    ActionChains(self.driver).move_to_element(chart).perform()
                    time.sleep(0.5)

                    # Check for tooltips or interactive feedback
                    tooltips = self.driver.find_elements(By.CSS_SELECTOR,
                        ".tooltip, [data-testid*='tooltip'], .chart-tooltip")

                    interactive = len(tooltips) > 0
                    print(f"  {'✅' if interactive else '⚠️'} Chart interactivity: {'Working' if interactive else 'Limited'}")

                except Exception:
                    print("  ⚠️  Chart interactivity test inconclusive")

        except Exception as e:
            self.record_test_result("dashboard_components", False, time.time() - start_time, f"Error: {str(e)}")
            print(f"  ❌ Dashboard test failed: {str(e)}")

    def test_leads_management(self):
        """Test leads management functionality"""
        print("\n📋 Testing Leads Management...")

        # Navigate to leads page
        leads_url = f"{self.base_url}/leads"
        load_time = self.measure_page_load_time(leads_url)
        print(f"  📍 Navigated to leads page ({load_time:.3f}s)")

        start_time = time.time()
        try:
            # Check for leads table
            tables = self.driver.find_elements(By.CSS_SELECTOR,
                "table, [data-testid*='table'], .leads-table")

            # Check for filter controls
            filters = self.driver.find_elements(By.CSS_SELECTOR,
                "[data-testid*='filter'], .filter, input[type='search']")

            # Check for action buttons
            add_buttons = self.driver.find_elements(By.CSS_SELECTOR,
                "button:contains('Add'), [data-testid*='add'], .add-button")

            # Check for export functionality
            export_buttons = self.driver.find_elements(By.CSS_SELECTOR,
                "button:contains('Export'), [data-testid*='export']")

            functionality_score = 0
            functionality_score += 1 if tables else 0
            functionality_score += 1 if filters else 0
            functionality_score += 1 if add_buttons else 0
            functionality_score += 1 if export_buttons else 0

            success = functionality_score >= 2  # At least table and one other feature

            details = f"Table: {len(tables)}, Filters: {len(filters)}, Add: {len(add_buttons)}, Export: {len(export_buttons)}"

            self.record_test_result("leads_management", success, time.time() - start_time, details)

            status = "✅" if success else "⚠️"
            print(f"  {status} Leads management: {details}")

            # Test search functionality if available
            search_inputs = self.driver.find_elements(By.CSS_SELECTOR,
                "input[type='search'], [data-testid*='search'], .search-input")

            if search_inputs:
                try:
                    search_input = search_inputs[0]
                    search_input.clear()
                    search_input.send_keys("test")
                    search_input.send_keys(Keys.ENTER)
                    time.sleep(1)

                    print("  ✅ Search functionality available")
                except Exception:
                    print("  ⚠️  Search functionality test failed")

        except Exception as e:
            self.record_test_result("leads_management", False, time.time() - start_time, f"Error: {str(e)}")
            print(f"  ❌ Leads management test failed: {str(e)}")

    def test_performance_metrics(self):
        """Test frontend performance metrics"""
        print("\n⚡ Testing Frontend Performance...")

        # Measure Core Web Vitals using JavaScript
        core_web_vitals = self.driver.execute_script("""
            return new Promise((resolve) => {
                const observer = new PerformanceObserver((list) => {
                    const entries = list.getEntries();
                    const metrics = {};

                    entries.forEach(entry => {
                        if (entry.entryType === 'navigation') {
                            metrics.loadTime = entry.loadEventEnd - entry.loadEventStart;
                            metrics.domContentLoaded = entry.domContentLoadedEventEnd - entry.domContentLoadedEventStart;
                        }
                        if (entry.entryType === 'largest-contentful-paint') {
                            metrics.lcp = entry.startTime;
                        }
                        if (entry.entryType === 'first-input') {
                            metrics.fid = entry.processingStart - entry.startTime;
                        }
                        if (entry.entryType === 'layout-shift') {
                            metrics.cls = (metrics.cls || 0) + entry.value;
                        }
                    });

                    resolve(metrics);
                });

                observer.observe({entryTypes: ['navigation', 'largest-contentful-paint', 'first-input', 'layout-shift']});

                // Fallback timeout
                setTimeout(() => {
                    resolve({
                        loadTime: performance.timing.loadEventEnd - performance.timing.loadEventStart,
                        domContentLoaded: performance.timing.domContentLoadedEventEnd - performance.timing.domContentLoadedEventStart
                    });
                }, 3000);
            });
        """)

        try:
            # Get performance metrics
            performance_timing = self.driver.execute_script("""
                const timing = performance.timing;
                return {
                    navigationStart: timing.navigationStart,
                    domContentLoaded: timing.domContentLoadedEventEnd - timing.navigationStart,
                    loadComplete: timing.loadEventEnd - timing.navigationStart,
                    firstByte: timing.responseStart - timing.navigationStart
                };
            """)

            # Evaluate performance
            dom_load_time = performance_timing.get('domContentLoaded', 0) / 1000
            full_load_time = performance_timing.get('loadComplete', 0) / 1000
            first_byte_time = performance_timing.get('firstByte', 0) / 1000

            # Performance thresholds (in seconds)
            performance_good = (
                dom_load_time < 3.0 and
                full_load_time < 5.0 and
                first_byte_time < 1.0
            )

            details = f"DOM: {dom_load_time:.2f}s, Load: {full_load_time:.2f}s, TTFB: {first_byte_time:.2f}s"

            self.record_test_result("performance_metrics", performance_good, full_load_time, details)

            status = "✅" if performance_good else "⚠️"
            print(f"  {status} Performance metrics: {details}")

        except Exception as e:
            print(f"  ❌ Performance metrics test failed: {str(e)}")

    def test_error_handling(self):
        """Test error handling and edge cases"""
        print("\n🚨 Testing Error Handling...")

        start_time = time.time()
        try:
            # Test 404 page
            not_found_url = f"{self.base_url}/non-existent-page"
            self.driver.get(not_found_url)
            time.sleep(2)

            # Check if proper 404 page is shown
            page_content = self.driver.page_source.lower()
            has_404_handling = (
                "404" in page_content or
                "not found" in page_content or
                "page not found" in page_content
            )

            details = "404 page: " + ("Found" if has_404_handling else "Missing")

            self.record_test_result("error_404_handling", has_404_handling, time.time() - start_time, details)

            status = "✅" if has_404_handling else "⚠️"
            print(f"  {status} {details}")

            # Test JavaScript errors
            js_errors = self.driver.get_log('browser')
            severe_errors = [error for error in js_errors if error['level'] == 'SEVERE']

            no_severe_errors = len(severe_errors) == 0
            error_details = f"Severe JS errors: {len(severe_errors)}"

            self.record_test_result("javascript_errors", no_severe_errors, 0, error_details)

            status = "✅" if no_severe_errors else "❌"
            print(f"  {status} {error_details}")

        except Exception as e:
            self.record_test_result("error_handling", False, time.time() - start_time, f"Error: {str(e)}")
            print(f"  ❌ Error handling test failed: {str(e)}")

    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n📋 Frontend Component Test Report:")
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
            rate = (successful / total) * 100
            print(f"  {category.capitalize()}: {successful}/{total} ({rate:.1f}%)")

        # Show failed tests
        failed_tests = [r for r in self.test_results if not r["success"]]
        if failed_tests:
            print(f"\nFailed Tests:")
            for test in failed_tests:
                print(f"  ❌ {test['test']}: {test['details']}")

        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": success_rate,
            "categories": categories,
            "failed_tests": failed_tests
        }

    def run_all_tests(self):
        """Run all frontend component tests"""
        print("🚀 Starting Comprehensive Frontend Component Testing")
        print("=" * 70)

        try:
            self.setup_driver()

            # Navigate to home page
            load_time = self.measure_page_load_time(self.base_url)
            print(f"📍 Initial page load: {load_time:.3f}s")

            # Run all tests
            self.test_responsive_design()
            self.test_page_accessibility()
            self.test_navigation_components()
            self.test_form_validation()
            self.test_dashboard_components()
            self.test_leads_management()
            self.test_performance_metrics()
            self.test_error_handling()

            print("\n✅ All frontend component tests completed!")

            return self.generate_test_report()

        except Exception as e:
            print(f"\n❌ Frontend testing failed: {str(e)}")
            raise

        finally:
            self.teardown_driver()


if __name__ == "__main__":
    # Run the tests
    tester = FrontendComponentTester()
    report = tester.run_all_tests()

    # Save report to file
    with open("frontend_test_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 Test report saved to frontend_test_report.json")