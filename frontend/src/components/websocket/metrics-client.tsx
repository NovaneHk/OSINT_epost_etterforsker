/**
 * WebSocket Metrics Client
 * Connects to metrics WebSocket endpoint and displays real-time metrics
 */

import React, { useEffect, useState, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';

interface MetricsClientProps {
  reconnectInterval?: number;  // milliseconds to wait before reconnecting
  url?: string;                 // override default websocket URL
}

interface MetricsData {
  total_operations: number;
  average_time: number;
  operations: Array<{
    name: string;
    duration: number;
    timestamp: string;
    function?: string;
    category?: string;
  }>;
}

const DEFAULT_WS_URL = process.env.NEXT_PUBLIC_API_URL
  ? `${process.env.NEXT_PUBLIC_API_URL.replace('http', 'ws')}/ws/metrics`
  : 'ws://localhost:8000/api/ws/metrics';

export function MetricsClient({
  reconnectInterval = 3000,
  url = DEFAULT_WS_URL
}: MetricsClientProps) {
  const [connected, setConnected] = useState(false);
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
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
          console.log('WebSocket connected');
        };

        // Connection closed
        ws.current.onclose = (event) => {
          setConnected(false);
          console.log('WebSocket disconnected, reconnecting...');

          // Reconnect after delay
          setTimeout(connectWebSocket, reconnectInterval);
        };

        // Connection error
        ws.current.onerror = (err) => {
          setConnected(false);
          setError('Connection error. Reconnecting...');
          console.error('WebSocket error:', err);
        };

        // Message received
        ws.current.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            if (data.type === 'metrics_update') {
              setMetrics(data.data);
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

  // Format timestamp to readable time
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          Real-time Performance Metrics
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

        {metrics ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-muted rounded p-3">
                <div className="text-sm font-medium">Total Operations</div>
                <div className="text-2xl font-bold">{metrics.total_operations}</div>
              </div>

              <div className="bg-muted rounded p-3">
                <div className="text-sm font-medium">Average Time (ms)</div>
                <div className="text-2xl font-bold">{metrics.average_time.toFixed(2)}</div>
              </div>
            </div>

            <div>
              <h3 className="text-lg font-medium mb-2">Recent Operations</h3>
              <div className="space-y-2 max-h-80 overflow-y-auto pr-2">
                {metrics.operations.slice().reverse().map((op, index) => (
                  <div key={index} className="bg-card border rounded-md p-3">
                    <div className="flex justify-between items-center">
                      <span className="font-medium">{op.name}</span>
                      <span className="text-sm text-muted-foreground">{formatTime(op.timestamp)}</span>
                    </div>

                    <div className="mt-2">
                      <Progress
                        value={Math.min(100, (op.duration / (metrics.average_time * 2)) * 100)}
                        className="h-2"
                      />
                    </div>

                    <div className="flex justify-between items-center mt-1">
                      <span className="text-sm">{op.duration.toFixed(2)} ms</span>
                      {op.category && (
                        <Badge variant="outline" className="text-xs">
                          {op.category}
                        </Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="flex justify-center items-center h-40">
            <p className="text-muted-foreground">Waiting for metrics data...</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default MetricsClient;
