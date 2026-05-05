"""
WebSocket Integration Test Script
Tests the integration between backend WebSocket endpoints and frontend clients
"""

import asyncio
import json
import logging
import argparse
import websockets
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default settings
DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_WS_BASE_URL = "ws://localhost:8000"

class WebSocketIntegrationTester:
    def __init__(self, base_url=DEFAULT_BASE_URL, ws_base_url=DEFAULT_WS_BASE_URL):
        self.base_url = base_url
        self.ws_base_url = ws_base_url
        self.active_websockets = []
        self.message_counts = {}
        self.test_results = {
            "metrics_endpoint": {"status": "Not Tested", "messages": 0, "errors": 0},
            "status_endpoint": {"status": "Not Tested", "messages": 0, "errors": 0},
            "notifications_endpoint": {"status": "Not Tested", "messages": 0, "errors": 0}
        }

    async def test_health_endpoint(self):
        """Test the HTTP health endpoint"""
        logger.info("Testing API health endpoint")
        try:
            response = requests.get(f"{self.base_url}/api/health")
            if response.status_code == 200:
                logger.info("✅ Health endpoint is working")
                return True
            else:
                logger.error(f"❌ Health endpoint returned status code {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Error checking health endpoint: {e}")
            return False

    async def test_metrics_websocket(self):
        """Test the metrics WebSocket endpoint"""
        endpoint = f"{self.ws_base_url}/api/ws/metrics"
        logger.info(f"Testing WebSocket metrics endpoint: {endpoint}")

        self.test_results["metrics_endpoint"]["status"] = "Testing"

        try:
            async with websockets.connect(endpoint) as websocket:
                self.active_websockets.append(websocket)
                self.test_results["metrics_endpoint"]["status"] = "Connected"

                # Listen for messages for 10 seconds
                for _ in range(3):  # 3 messages / 15 seconds
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        data = json.loads(message)

                        if "type" in data and data["type"] == "metrics_update":
                            self.test_results["metrics_endpoint"]["messages"] += 1

                            # Log the first message for debugging
                            if self.test_results["metrics_endpoint"]["messages"] == 1:
                                logger.info(f"Metrics data format: {json.dumps(data, indent=2)}")

                            logger.info(f"✅ Received metric update #{self.test_results['metrics_endpoint']['messages']}")
                        else:
                            logger.warning(f"❓ Unexpected message format: {data}")
                    except asyncio.TimeoutError:
                        logger.warning("⚠️ Timeout waiting for metrics update")
                    except Exception as e:
                        logger.error(f"❌ Error receiving metrics message: {e}")
                        self.test_results["metrics_endpoint"]["errors"] += 1

                if self.test_results["metrics_endpoint"]["messages"] > 0:
                    self.test_results["metrics_endpoint"]["status"] = "Success"
                else:
                    self.test_results["metrics_endpoint"]["status"] = "Failed (No Messages)"

        except Exception as e:
            logger.error(f"❌ Failed to connect to metrics endpoint: {e}")
            self.test_results["metrics_endpoint"]["status"] = f"Failed: {str(e)}"
            self.test_results["metrics_endpoint"]["errors"] += 1

    async def test_status_websocket(self):
        """Test the system status WebSocket endpoint"""
        endpoint = f"{self.ws_base_url}/api/ws/status"
        logger.info(f"Testing WebSocket status endpoint: {endpoint}")

        self.test_results["status_endpoint"]["status"] = "Testing"

        try:
            async with websockets.connect(endpoint) as websocket:
                self.active_websockets.append(websocket)
                self.test_results["status_endpoint"]["status"] = "Connected"

                # Listen for 2 status updates
                for _ in range(2):
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        data = json.loads(message)

                        if "type" in data and data["type"] == "status_update":
                            self.test_results["status_endpoint"]["messages"] += 1

                            # Log the first message for debugging
                            if self.test_results["status_endpoint"]["messages"] == 1:
                                logger.info(f"Status data format: {json.dumps(data, indent=2)}")

                            logger.info(f"✅ Received status update #{self.test_results['status_endpoint']['messages']}")
                        else:
                            logger.warning(f"❓ Unexpected message format: {data}")
                    except asyncio.TimeoutError:
                        logger.warning("⚠️ Timeout waiting for status update")
                    except Exception as e:
                        logger.error(f"❌ Error receiving status message: {e}")
                        self.test_results["status_endpoint"]["errors"] += 1

                if self.test_results["status_endpoint"]["messages"] > 0:
                    self.test_results["status_endpoint"]["status"] = "Success"
                else:
                    self.test_results["status_endpoint"]["status"] = "Failed (No Messages)"

        except Exception as e:
            logger.error(f"❌ Failed to connect to status endpoint: {e}")
            self.test_results["status_endpoint"]["status"] = f"Failed: {str(e)}"
            self.test_results["status_endpoint"]["errors"] += 1

    async def test_notification_websocket(self):
        """Test the notification WebSocket endpoint"""
        endpoint = f"{self.ws_base_url}/api/ws/notifications"
        logger.info(f"Testing WebSocket notifications endpoint: {endpoint}")

        self.test_results["notifications_endpoint"]["status"] = "Testing"

        try:
            async with websockets.connect(endpoint) as websocket:
                self.active_websockets.append(websocket)
                self.test_results["notifications_endpoint"]["status"] = "Connected"

                # For notifications, we expect at least an initial connection message
                # plus possibly heartbeats
                for _ in range(2):
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        data = json.loads(message)

                        if "type" in data:
                            self.test_results["notifications_endpoint"]["messages"] += 1

                            # Log the first message for debugging
                            if self.test_results["notifications_endpoint"]["messages"] == 1:
                                logger.info(f"Notification data format: {json.dumps(data, indent=2)}")

                            logger.info(f"✅ Received notification: {data['type']}")
                        else:
                            logger.warning(f"❓ Unexpected message format: {data}")
                    except asyncio.TimeoutError:
                        logger.warning("⚠️ Timeout waiting for notification")
                    except Exception as e:
                        logger.error(f"❌ Error receiving notification message: {e}")
                        self.test_results["notifications_endpoint"]["errors"] += 1

                if self.test_results["notifications_endpoint"]["messages"] > 0:
                    self.test_results["notifications_endpoint"]["status"] = "Success"
                else:
                    self.test_results["notifications_endpoint"]["status"] = "Failed (No Messages)"

        except Exception as e:
            logger.error(f"❌ Failed to connect to notifications endpoint: {e}")
            self.test_results["notifications_endpoint"]["status"] = f"Failed: {str(e)}"
            self.test_results["notifications_endpoint"]["errors"] += 1

    async def run_all_tests(self):
        """Run all integration tests"""
        logger.info("Starting WebSocket integration tests")

        health_check = await self.test_health_endpoint()
        if not health_check:
            logger.error("❌ API health check failed. Skipping WebSocket tests.")
            return

        await asyncio.gather(
            self.test_metrics_websocket(),
            self.test_status_websocket(),
            self.test_notification_websocket()
        )

        # Print summary
        logger.info("\n" + "="*50)
        logger.info("WebSocket Integration Test Results")
        logger.info("="*50)
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"WebSocket Base URL: {self.ws_base_url}")
        logger.info("-"*50)

        for endpoint, results in self.test_results.items():
            status_emoji = "✅" if "Success" in results["status"] else "❌"
            logger.info(f"{status_emoji} {endpoint}: {results['status']}")
            logger.info(f"   Messages received: {results['messages']}")
            logger.info(f"   Errors encountered: {results['errors']}")
            logger.info("-"*50)

        all_successful = all("Success" in results["status"] for results in self.test_results.values())
        if all_successful:
            logger.info("✅ All WebSocket endpoints are working correctly!")
        else:
            logger.warning("⚠️ Some WebSocket endpoints failed testing. Check logs for details.")

def main():
    parser = argparse.ArgumentParser(description='WebSocket Integration Test Script')
    parser.add_argument('--base-url', default=DEFAULT_BASE_URL, help='Base URL for HTTP requests')
    parser.add_argument('--ws-base-url', default=DEFAULT_WS_BASE_URL, help='Base URL for WebSocket connections')
    args = parser.parse_args()

    tester = WebSocketIntegrationTester(base_url=args.base_url, ws_base_url=args.ws_base_url)

    # Run the event loop
    asyncio.run(tester.run_all_tests())

if __name__ == "__main__":
    main()
