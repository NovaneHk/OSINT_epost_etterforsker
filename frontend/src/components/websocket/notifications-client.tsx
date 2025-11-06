/**
 * WebSocket Notifications Client
 * Connects to notifications WebSocket endpoint and displays real-time system notifications
 */

import React, { useEffect, useState, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Bell, Info, AlertTriangle, AlertCircle } from 'lucide-react';

interface NotificationsClientProps {
  reconnectInterval?: number;  // milliseconds to wait before reconnecting
  url?: string;                // override default websocket URL
  maxNotifications?: number;   // maximum number of notifications to show
}

interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  message: string;
  timestamp: string;
  details?: string;
}

const DEFAULT_WS_URL = process.env.NEXT_PUBLIC_API_URL
  ? `${process.env.NEXT_PUBLIC_API_URL.replace('http', 'ws')}/ws/notifications`
  : 'ws://localhost:8000/api/ws/notifications';

export function NotificationsClient({
  reconnectInterval = 3000,
  url = DEFAULT_WS_URL,
  maxNotifications = 10
}: NotificationsClientProps) {
  const [connected, setConnected] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
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
          console.log('Notifications WebSocket connected');
        };

        // Connection closed
        ws.current.onclose = (event) => {
          setConnected(false);
          console.log('Notifications WebSocket disconnected, reconnecting...');

          // Reconnect after delay
          setTimeout(connectWebSocket, reconnectInterval);
        };

        // Connection error
        ws.current.onerror = (err) => {
          setConnected(false);
          setError('Connection error. Reconnecting...');
          console.error('Notifications WebSocket error:', err);
        };

        // Message received
        ws.current.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            // Handle initial connection message
            if (data.type === 'notification') {
              const newNotification: Notification = {
                id: `notification-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
                type: data.data.level || 'info',
                message: data.data.message,
                timestamp: data.timestamp,
                details: data.data.details
              };

              setNotifications(prev => {
                const updated = [newNotification, ...prev].slice(0, maxNotifications);
                return updated;
              });
            }
            // Handle heartbeat message
            else if (data.type === 'heartbeat') {
              // Update connection status but don't add to notifications
              console.log('Received heartbeat at', data.timestamp);
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
  }, [url, reconnectInterval, maxNotifications]);

  // Format timestamp to readable time
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  };

  // Get icon for notification type
  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'success':
        return <Badge variant="success" className="mr-2 w-6 h-6 p-1"><Bell className="w-4 h-4" /></Badge>;
      case 'warning':
        return <Badge variant="warning" className="mr-2 w-6 h-6 p-1"><AlertTriangle className="w-4 h-4" /></Badge>;
      case 'error':
        return <Badge variant="destructive" className="mr-2 w-6 h-6 p-1"><AlertCircle className="w-4 h-4" /></Badge>;
      case 'info':
      default:
        return <Badge variant="secondary" className="mr-2 w-6 h-6 p-1"><Info className="w-4 h-4" /></Badge>;
    }
  };

  // Get background class for notification type
  const getNotificationClass = (type: string) => {
    switch (type) {
      case 'success':
        return 'bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-900';
      case 'warning':
        return 'bg-yellow-50 dark:bg-yellow-950/20 border-yellow-200 dark:border-yellow-900';
      case 'error':
        return 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-900';
      case 'info':
      default:
        return 'bg-muted/50 border-muted';
    }
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          System Notifications
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

        <div className="space-y-4 max-h-80 overflow-y-auto pr-1">
          {notifications.length > 0 ? (
            notifications.map(notification => (
              <div
                key={notification.id}
                className={`p-3 rounded border ${getNotificationClass(notification.type)}`}
              >
                <div className="flex items-start space-x-2">
                  <div className="flex-shrink-0">
                    {getNotificationIcon(notification.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between">
                      <span className="font-medium">
                        {notification.message}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {formatTime(notification.timestamp)}
                      </span>
                    </div>
                    {notification.details && (
                      <p className="text-sm mt-1">{notification.details}</p>
                    )}
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="flex justify-center items-center h-40 text-center">
              <div className="text-muted-foreground">
                <Bell className="mx-auto h-8 w-8 mb-2 opacity-50" />
                <p>No notifications yet.</p>
                <p className="text-sm">System notifications will appear here in real-time.</p>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default NotificationsClient;
