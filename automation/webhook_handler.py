"""
Webhook handler for receiving and processing incoming webhook payloads.
Provides WebhookHandler and WebhookResult used by the automation package.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class WebhookResult:
    """Result from processing a webhook payload."""

    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    status_code: int = 200


class WebhookHandler:
    """Handles incoming webhook requests and routes them to appropriate processors."""

    def __init__(self, secret: Optional[str] = None):
        self._secret = secret
        self._handlers: Dict[str, Any] = {}

    def register(self, event_type: str, handler) -> None:
        """Register a handler callable for a specific event type."""
        self._handlers[event_type] = handler
        logger.debug("Registered webhook handler for event: %s", event_type)

    def handle(self, payload: Dict[str, Any]) -> WebhookResult:
        """
        Process an incoming webhook payload synchronously.

        Dispatches to a registered handler matching ``payload['event']``, or
        returns a generic success result if no handler is registered.
        """
        try:
            event_type = payload.get("event", "unknown")
            handler = self._handlers.get(event_type)
            if handler:
                result_data = handler(payload)
                return WebhookResult(success=True, data=result_data or {})
            # No specific handler — accept and log
            logger.info("Received unhandled webhook event: %s", event_type)
            return WebhookResult(success=True, data={"event": event_type, "handled": False})
        except Exception as exc:
            logger.error("Webhook processing error: %s", exc, exc_info=True)
            return WebhookResult(success=False, error=str(exc), status_code=500)

    async def handle_async(self, payload: Dict[str, Any]) -> WebhookResult:
        """
        Async version of handle().  Awaits the handler if it is a coroutine.
        """
        import asyncio

        try:
            event_type = payload.get("event", "unknown")
            handler = self._handlers.get(event_type)
            if handler:
                if asyncio.iscoroutinefunction(handler):
                    result_data = await handler(payload)
                else:
                    result_data = handler(payload)
                return WebhookResult(success=True, data=result_data or {})
            logger.info("Received unhandled webhook event: %s", event_type)
            return WebhookResult(success=True, data={"event": event_type, "handled": False})
        except Exception as exc:
            logger.error("Webhook processing error: %s", exc, exc_info=True)
            return WebhookResult(success=False, error=str(exc), status_code=500)
