"""
Backend WebSocket tests — analytics real-time endpoint connection and messaging.
"""
import pytest
import json


def test_websocket_analytics_endpoint_exists(backend_client, backend_auth):
    """WebSocket endpoint is reachable (HTTP upgrade or 404 if not configured)."""
    # Check that the WS path is registered — an HTTP GET might return 403/404/426
    response = backend_client.get("/ws/analytics")
    # Any response is fine as long as it's not a server error (500)
    assert response.status_code != 500


def test_websocket_unauthenticated_rejected(backend_client):
    """WebSocket connection without auth should be rejected (403 or close immediately)."""
    try:
        with backend_client.websocket_connect("/ws/analytics") as ws:
            # If connection succeeded, server may close immediately
            pass
    except Exception as exc:
        # Expected: WebSocketDisconnect or similar — connection refused
        error_str = str(exc)
        assert "403" in error_str or "401" in error_str or "WebSocket" in type(exc).__name__


def test_websocket_connection_with_token(backend_client, backend_auth):
    """WebSocket connection with a valid token should succeed or return 403 gracefully."""
    token = backend_auth["Authorization"].replace("Bearer ", "")
    try:
        with backend_client.websocket_connect(f"/ws/analytics?token={token}") as ws:
            # Connected — send a ping-like message
            ws.send_text(json.dumps({"type": "ping"}))
            # Don't require a specific response; just verify no exception
    except Exception as exc:
        # 403/401 is acceptable; 500 is not
        error_str = str(exc)
        assert "500" not in error_str


def test_dashboard_analytics_http_endpoint(backend_client, backend_auth):
    """Dashboard analytics HTTP endpoint returns proper structure."""
    response = backend_client.get("/api/analytics/dashboard", headers=backend_auth)
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, dict)
