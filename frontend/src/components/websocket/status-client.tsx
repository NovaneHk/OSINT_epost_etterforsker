/**
 * WebSocket Status Client
 * Connects to status WebSocket endpoint and displays real-time system status
 */

import React, { useEffect, useState, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';

interface StatusClientProps {
  reconnectInterval?: number;  // milliseconds to wait before reconnecting
  url?: string;                 // override default websocket URL
}

interface StatusData {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  active_connections: number;
  active_searches: number;
  queue_length: number;
  status: string;
}

const DEFAULT_WS_URL = process.env.NEXT_PUBLIC_API_URL
  ? `${process.env.NEXT_PUBLIC_API_URL.replace('http', 'ws')}/ws/status`
  : 'ws://localhost:8000/api/ws/status';

export function StatusClient({
  reconnectInterval = 3000,
  url = DEFAULT_WS_URL
}: StatusClientProps) {
  const [connected, setConnected] = useState(false);
  const [status, setStatus] = useState<StatusData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const ws = useRef<WebSocket | null>(null);

  // Connect to WebSocket
  useEffect(() => {
    // Connection setup function
    const connectWebSocket = () => {
      try {
        // Close existing connection if any
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
          ws.current.close();
        }

        // Create new connection
        ws.current = new WebSocket(url);

        // Connection opened
        ws.current.onopen = () => {
          setConnected(true);
          setError(null);
          console.log('Status WebSocket connected');
        };

        // Connection closed
        ws.current.onclose = (event) => {
          setConnected(false);
          console.log('Status WebSocket disconnected, reconnecting...');

          // Reconnect after delay
          setTimeout(connectWebSocket, reconnectInterval);
        };

        // Connection error
        ws.current.onerror = (err) => {
          setConnected(false);
          setError('Connection error. Reconnecting...');
          console.error('Status WebSocket error:', err);
        };

        // Message received
        ws.current.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            if (data.type === 'status_update') {
              setStatus(data.data);
            }
          } catch (e) {
            console.error('Failed to parse WebSocket message:', e);
          }
        };
      } catch (e) {
        console.error('WebSocket connection failed:', e);
        setError('Failed to connect. Retrying...');
        setTimeout(connectWebSocket, reconnectInterval);
      }
    };

    // Initial connection
    connectWebSocket();

    // Cleanup on component unmount
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [url, reconnectInterval]);

  // Get status badge color
  const getStatusColor = (statusValue: string) => {
    switch (statusValue) {
      case 'healthy':
        return 'bg-green-500';
      case 'degraded':
        return 'bg-yellow-500';
      case 'critical':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  // Get progress indicator class based on usage level
  const getProgressClass = (value: number) => {
    if (value > 90) return 'bg-red-500';
    if (value > 70) return 'bg-yellow-500';
    return 'bg-blue-500'; // default color
  };

  // Format usage value to rounded percentage
  const formatUsage = (value: number) => {
    return `${Math.round(value)}%`;
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          System Status
          <Badge variant={connected ? "success" : "destructive"}>
            {connected ? "Connected" : "Disconnected"}
          </Badge>
        </CardTitle>
      </CardHeader>

      <CardContent>
        {error && (
          <Alert variant="destructive" className="mb-4">
            <AlertTitle>Connection Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {status ? (
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${getStatusColor(status.status)}`}></div>
              <span className="font-medium">System Status: {status.status}</span>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="bg-muted rounded p-3">
                <div className="text-sm font-medium">Active Connections</div>
                <div className="text-2xl font-bold">{status.active_connections}</div>
              </div>

              <div className="bg-muted rounded p-3">
                <div className="text-sm font-medium">Active Searches</div>
                <div className="text-2xl font-bold">{status.active_searches}</div>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm">CPU Usage</span>
                  <span className="text-sm font-medium">{formatUsage(status.cpu_usage)}</span>
                </div>
                <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
                  <div
                    className={`h-2 ${getProgressClass(status.cpu_usage)}`}
                    style={{ width: `${Math.min(100, status.cpu_usage)}%` }}
                  ></div>
                </div>
              </div>

              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm">Memory Usage</span>
                  <span className="text-sm font-medium">{formatUsage(status.memory_usage)}</span>
                </div>
                <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
                  <div
                    className={`h-2 ${getProgressClass(status.memory_usage)}`}
                    style={{ width: `${Math.min(100, status.memory_usage)}%` }}
                  ></div>
                </div>
              </div>

              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm">Disk Usage</span>
                  <span className="text-sm font-medium">{formatUsage(status.disk_usage)}</span>
                </div>
                <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
                  <div
                    className={`h-2 ${getProgressClass(status.disk_usage)}`}
                    style={{ width: `${Math.min(100, status.disk_usage)}%` }}
                  ></div>
                </div>
              </div>
            </div>

            <div className="bg-card border rounded p-3">
              <div className="flex justify-between items-center">
                <span className="font-medium">Queue Length</span>
                <span className="text-sm">{status.queue_length} items</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex justify-center items-center h-40">
            <p className="text-muted-foreground">Waiting for system status data...</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default StatusClient;
