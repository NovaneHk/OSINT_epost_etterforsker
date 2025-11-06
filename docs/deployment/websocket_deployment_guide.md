# WebSocket Deployment Guide

This guide outlines the process for deploying the WebSocket components of the OSINT E-post Etterforsker system to production environments.

## Overview

The system now includes real-time WebSocket capabilities for:
- Performance metrics streaming
- System status updates
- User notifications

These features enhance the user experience by providing real-time data without requiring page refreshes.

## Prerequisites

Before deploying the WebSocket functionality, ensure you have:

- Backend server with FastAPI installed
- Frontend built with Next.js
- PostgreSQL database configured
- Redis for WebSocket pub/sub (recommended for multi-instance setups)
- Proper network configuration to allow WebSocket traffic (ports, firewalls, etc.)
- SSL certificates for secure WebSocket connections (wss://)

## Deployment Steps

### 1. Environment Configuration

Update your `.env` or `.env.production` file with the following WebSocket-specific settings:

```
# WebSocket settings
WS_HEARTBEAT_INTERVAL=30000
WS_METRICS_UPDATE_INTERVAL=5000
WS_STATUS_UPDATE_INTERVAL=10000
WEBSOCKET_MAX_CONNECTIONS=1000
ENABLE_WEBSOCKET_AUTHENTICATION=true
```

### 2. Backend Configuration

The WebSocket endpoints are already integrated into the API router in `backend/api/routes.py`. Ensure this routing configuration is included in your production deployment.

#### Docker Deployment

In your `docker-compose.prod.yml` file, ensure the backend service includes:

```yaml
backend:
  # ... existing configuration ...
  environment:
    # ... existing environment variables ...
    - WS_HEARTBEAT_INTERVAL=${WS_HEARTBEAT_INTERVAL:-30000}
    - WS_METRICS_UPDATE_INTERVAL=${WS_METRICS_UPDATE_INTERVAL:-5000}
    - WS_STATUS_UPDATE_INTERVAL=${WS_STATUS_UPDATE_INTERVAL:-10000}
    - WEBSOCKET_MAX_CONNECTIONS=${WEBSOCKET_MAX_CONNECTIONS:-1000}
    - ENABLE_WEBSOCKET_AUTHENTICATION=${ENABLE_WEBSOCKET_AUTHENTICATION:-true}
  ports:
    - "8000:8000"  # HTTP
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 20s
```

### 3. Frontend Configuration

#### Environment Variables

Update the frontend `.env.production` file to include the WebSocket URL:

```
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_WEBSOCKET_URL=wss://api.yourdomain.com
```

#### Build Process

Ensure the frontend is built with production settings:

```bash
cd frontend
npm run build
```

### 4. Proxy Configuration

For production environments using Nginx, you need to configure the proxy to support WebSocket connections:

```nginx
# /etc/nginx/sites-available/osint-app.conf
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name api.yourdomain.com;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    # WebSocket support
    location /api/ws {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # WebSocket-specific timeouts
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # Standard API requests
    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Frontend app (if serving from the same domain)
    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 5. Scaling Considerations

For multi-instance deployments, implement a WebSocket message broker:

1. Add Redis to your `docker-compose.prod.yml`:

```yaml
redis:
  image: redis:7-alpine
  restart: always
  volumes:
    - redis-data:/data
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 30s
    timeout: 10s
    retries: 3
```

2. Configure the backend to use Redis for message broadcasting:

```yaml
backend:
  # ... existing configuration ...
  environment:
    # ... existing environment variables ...
    - USE_REDIS_PUBSUB=true
    - REDIS_URL=redis://redis:6379/0
  depends_on:
    - redis
```

### 6. Testing Deployment

After deployment, run the integration tests to verify WebSocket functionality:

```bash
python test_websocket_integration.py --base-url https://api.yourdomain.com --ws-base-url wss://api.yourdomain.com
```

Verify success by:
- Checking the test results for successful connections
- Monitoring the backend logs for WebSocket activities
- Visiting the monitoring dashboard in the frontend

## Monitoring WebSocket Health

Add WebSocket metrics to your monitoring systems:

1. Add Prometheus metrics collection for WebSockets:

```python
# Example metrics to collect
websocket_active_connections = Gauge('websocket_active_connections', 'Number of active WebSocket connections')
websocket_message_count = Counter('websocket_message_count', 'Number of WebSocket messages sent', ['endpoint'])
websocket_errors = Counter('websocket_errors', 'Number of WebSocket errors', ['type'])
```

2. Add an endpoint to the monitoring dashboard for WebSocket health:

```
GET /api/health/websocket
```

## Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure the WebSocket port is open in your firewall.

2. **Connection Closing Unexpectedly**: Check server timeout settings in Nginx/proxy.

3. **Authentication failures**: Verify token configuration is consistent.

4. **High Memory Usage**: Monitor WebSocket connections and implement connection limits.

### Logs to Check

- Backend application logs: Look for WebSocket connection/disconnection events
- Nginx error logs: Check for proxy issues
- Browser console: Client-side WebSocket errors

## BackgroundL WebSocket Architecture Notes

The OSINT E-post Etterforsker uses a custom WebSocket architecture:

1. **Connection Manager**: Located in `backend/api/websocket.py`, manages all WebSocket connections and broadcasts.

2. **WebSocket Endpoints**:
   - `/api/ws/metrics`: Real-time performance metrics
   - `/api/ws/status`: System status updates
   - `/api/ws/notifications`: User notifications

3. **Frontend Integration**:
   - `MetricsClient` component connects to WebSocket endpoints
   - Renders real-time data from the backend
   - Implements automatic reconnection

4. **Protocol**: Each message follows this JSON format:
   ```json
   {
     "type": "message_type",
     "data": {
       "key": "value"
     },
     "timestamp": "ISO datetime"
   }
