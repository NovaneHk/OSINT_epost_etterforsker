/**
 * Monitoring Dashboard Page
 * Displays real-time system metrics, status, and notifications
 */

import React from 'react';
import { Metadata } from 'next';
import MetricsClient from '@/components/websocket/metrics-client';
import StatusClient from '@/components/websocket/status-client';
import NotificationsClient from '@/components/websocket/notifications-client';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export const metadata: Metadata = {
  title: 'System Monitoring | OSINT E-post Etterforsker',
  description: 'Real-time performance monitoring and system status',
};

export default function MonitoringPage() {
  return (
    <div className="container mx-auto py-8 space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">System Monitoring</h1>
        <p className="text-muted-foreground mt-2">
          Real-time performance metrics, system health status, and notifications
        </p>
      </div>

      {/* Desktop Layout - Side by side */}
      <div className="hidden md:grid md:grid-cols-2 gap-6">
        <div className="space-y-6">
          <MetricsClient />
          <NotificationsClient maxNotifications={5} />
        </div>

        <div className="space-y-6">
          <StatusClient />
          <Card>
            <CardHeader>
              <CardTitle>Monitoring Documentation</CardTitle>
              <CardDescription>Quick reference for monitoring features</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h3 className="font-medium mb-1">Real-time Metrics</h3>
                <p className="text-sm text-muted-foreground">
                  Performance metrics are streamed in real-time via WebSockets from the
                  backend. The system tracks operation durations, counts, and trends.
                </p>
              </div>

              <div>
                <h3 className="font-medium mb-1">System Status</h3>
                <p className="text-sm text-muted-foreground">
                  System health status includes CPU, memory, and disk usage metrics,
                  along with active connections and background tasks.
                </p>
              </div>

              <div>
                <h3 className="font-medium mb-1">Notifications</h3>
                <p className="text-sm text-muted-foreground">
                  System notifications provide real-time alerts for important events,
                  warnings, and informational messages from the backend.
                </p>
              </div>

              <div>
                <h3 className="font-medium mb-1">WebSocket Connections</h3>
                <p className="text-sm text-muted-foreground">
                  All monitoring panels utilize WebSocket connections that automatically
                  reconnect if disconnected. Connection status is shown in each panel.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Mobile Layout - Tabs */}
      <div className="md:hidden">
        <Tabs defaultValue="metrics" className="space-y-4">
          <TabsList className="grid grid-cols-3 w-full">
            <TabsTrigger value="metrics">Metrics</TabsTrigger>
            <TabsTrigger value="status">Status</TabsTrigger>
            <TabsTrigger value="notifications">Notifications</TabsTrigger>
          </TabsList>

          <TabsContent value="metrics" className="space-y-4">
            <MetricsClient />
          </TabsContent>

          <TabsContent value="status" className="space-y-4">
            <StatusClient />
          </TabsContent>

          <TabsContent value="notifications" className="space-y-4">
            <NotificationsClient />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
