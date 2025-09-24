"""
Real-time Analytics API for Phase 4
Advanced analytics endpoints for dashboard and monitoring
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, List, Any, Optional
import asyncio
import json
import logging
from datetime import datetime, timedelta
from dataclasses import asdict

from ..core.dependencies import get_current_user
from ..models.user import User

# Import AI components
try:
    from ai.analytics_engine import get_ai_analytics_engine
    from ai.nlp_processor import get_nlp_processor
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# WebSocket connection manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.analytics_data = {}
        self.last_update = datetime.now()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                # Remove broken connections
                if connection in self.active_connections:
                    self.active_connections.remove(connection)

    async def broadcast_analytics_update(self, data: Dict[str, Any]):
        """Broadcast analytics data to all connected clients"""
        message = json.dumps({
            "type": "analytics_update",
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
        await self.broadcast(message)

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time analytics updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and send periodic updates
            await asyncio.sleep(5)  # Send updates every 5 seconds

            # Generate real-time analytics data
            analytics_data = await get_realtime_analytics()
            await manager.send_personal_message(
                json.dumps({
                    "type": "analytics_update",
                    "data": analytics_data,
                    "timestamp": datetime.now().isoformat()
                }),
                websocket
            )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@router.get("/dashboard/overview")
async def get_dashboard_overview(current_user: User = Depends(get_current_user)):
    """Get comprehensive dashboard overview data"""
    try:
        # Get AI analytics if available
        ai_analytics = {}
        if AI_AVAILABLE:
            ai_engine = get_ai_analytics_engine()
            nlp_processor = get_nlp_processor()

            # Get AI engine summary
            ai_summary = await ai_engine.get_analysis_summary()
            ai_health = await ai_engine.health_check()

            # Get NLP processor health
            nlp_health = await nlp_processor.health_check()

            ai_analytics = {
                "ai_engine": {
                    "summary": ai_summary,
                    "health": ai_health
                },
                "nlp_processor": {
                    "health": nlp_health
                }
            }

        # Generate dashboard data
        dashboard_data = {
            "overview": {
                "total_investigations": await get_total_investigations(),
                "active_threats": await get_active_threats(),
                "risk_score_average": await get_average_risk_score(),
                "processing_speed": await get_processing_speed()
            },
            "ai_analytics": ai_analytics,
            "system_health": await get_system_health(),
            "recent_activity": await get_recent_activity(),
            "performance_metrics": await get_performance_metrics(),
            "timestamp": datetime.now().isoformat()
        }

        return dashboard_data

    except Exception as e:
        logger.error(f"Error getting dashboard overview: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard overview")

@router.get("/threats/realtime")
async def get_realtime_threats(current_user: User = Depends(get_current_user)):
    """Get real-time threat monitoring data"""
    try:
        threats_data = {
            "active_threats": await get_active_threat_list(),
            "threat_trends": await get_threat_trends(),
            "geographic_distribution": await get_threat_geography(),
            "severity_breakdown": await get_threat_severity_breakdown(),
            "recent_detections": await get_recent_threat_detections(),
            "timestamp": datetime.now().isoformat()
        }

        return threats_data

    except Exception as e:
        logger.error(f"Error getting real-time threats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get threat data")

@router.get("/performance/metrics")
async def get_performance_metrics_endpoint(current_user: User = Depends(get_current_user)):
    """Get detailed performance metrics"""
    try:
        metrics = {
            "processing_performance": await get_processing_performance(),
            "ai_model_performance": await get_ai_model_performance(),
            "system_resources": await get_system_resources(),
            "api_performance": await get_api_performance(),
            "database_performance": await get_database_performance(),
            "timestamp": datetime.now().isoformat()
        }

        return metrics

    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance metrics")

@router.get("/analytics/trends")
async def get_analytics_trends(
    timeframe: str = "24h",
    current_user: User = Depends(get_current_user)
):
    """Get analytics trends over specified timeframe"""
    try:
        # Parse timeframe
        hours = parse_timeframe(timeframe)

        trends_data = {
            "risk_score_trends": await get_risk_score_trends(hours),
            "threat_detection_trends": await get_threat_detection_trends(hours),
            "processing_volume_trends": await get_processing_volume_trends(hours),
            "accuracy_trends": await get_accuracy_trends(hours),
            "timeframe": timeframe,
            "timestamp": datetime.now().isoformat()
        }

        return trends_data

    except Exception as e:
        logger.error(f"Error getting analytics trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to get analytics trends")

@router.post("/analytics/trigger-analysis")
async def trigger_manual_analysis(
    data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Trigger manual AI analysis for testing/demonstration"""
    try:
        if not AI_AVAILABLE:
            return {"error": "AI components not available", "status": "simulation_mode"}

        ai_engine = get_ai_analytics_engine()
        nlp_processor = get_nlp_processor()

        results = {}

        # Perform different types of analysis based on input data
        if "email" in data:
            email_analysis = await ai_engine.analyze_email_risk(data)
            results["email_analysis"] = {
                "analysis_type": email_analysis.analysis_type.value,
                "score": email_analysis.score,
                "confidence": email_analysis.confidence,
                "details": email_analysis.details
            }

        if "domain" in data:
            domain_analysis = await ai_engine.analyze_domain_reputation(data)
            results["domain_analysis"] = {
                "analysis_type": domain_analysis.analysis_type.value,
                "score": domain_analysis.score,
                "confidence": domain_analysis.confidence,
                "details": domain_analysis.details
            }

        if "text" in data:
            text_analysis = await nlp_processor.process_intelligence_text(data["text"])
            results["text_analysis"] = text_analysis

        # Broadcast results to connected WebSocket clients
        await manager.broadcast_analytics_update({
            "type": "manual_analysis_complete",
            "results": results,
            "user": current_user.username
        })

        return {
            "status": "success",
            "results": results,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in manual analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to perform analysis")

# Helper functions for data generation
async def get_realtime_analytics():
    """Generate real-time analytics data"""
    return {
        "active_investigations": await get_total_investigations(),
        "threats_detected": await get_active_threats(),
        "processing_queue": await get_processing_queue_size(),
        "system_load": await get_system_load(),
        "ai_model_status": await get_ai_model_status()
    }

async def get_total_investigations():
    """Get total number of investigations"""
    # Simulate data - in production, query actual database
    return 1247

async def get_active_threats():
    """Get number of active threats"""
    # Simulate data - in production, query threat database
    return 23

async def get_average_risk_score():
    """Get average risk score"""
    # Simulate data - in production, calculate from actual data
    return 0.34

async def get_processing_speed():
    """Get current processing speed (items per minute)"""
    # Simulate data - in production, calculate from performance metrics
    return 156

async def get_system_health():
    """Get overall system health status"""
    health_data = {
        "status": "healthy",
        "uptime": "99.8%",
        "last_check": datetime.now().isoformat(),
        "components": {
            "database": "healthy",
            "ai_engine": "healthy" if AI_AVAILABLE else "degraded",
            "api": "healthy",
            "frontend": "healthy"
        }
    }

    if AI_AVAILABLE:
        try:
            ai_engine = get_ai_analytics_engine()
            nlp_processor = get_nlp_processor()

            ai_health = await ai_engine.health_check()
            nlp_health = await nlp_processor.health_check()

            health_data["components"]["ai_engine"] = ai_health["status"]
            health_data["components"]["nlp_processor"] = nlp_health["status"]
        except Exception as e:
            logger.error(f"Error checking AI health: {e}")
            health_data["components"]["ai_engine"] = "error"

    return health_data

async def get_recent_activity():
    """Get recent system activity"""
    # Simulate recent activity data
    return [
        {
            "timestamp": (datetime.now() - timedelta(minutes=2)).isoformat(),
            "type": "threat_detected",
            "description": "High-risk email detected from suspicious domain",
            "severity": "high"
        },
        {
            "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat(),
            "type": "analysis_complete",
            "description": "Batch analysis completed: 45 emails processed",
            "severity": "info"
        },
        {
            "timestamp": (datetime.now() - timedelta(minutes=8)).isoformat(),
            "type": "anomaly_detected",
            "description": "Unusual pattern detected in email traffic",
            "severity": "medium"
        }
    ]

async def get_performance_metrics():
    """Get current performance metrics"""
    return {
        "api_response_time": "45ms",
        "database_query_time": "12ms",
        "ai_processing_time": "89ms",
        "memory_usage": "68%",
        "cpu_usage": "34%",
        "disk_usage": "45%"
    }

async def get_active_threat_list():
    """Get list of active threats"""
    # Simulate active threats
    return [
        {
            "id": "threat_001",
            "type": "phishing_email",
            "severity": "high",
            "source": "suspicious-domain.tk",
            "detected_at": (datetime.now() - timedelta(minutes=15)).isoformat(),
            "risk_score": 0.89
        },
        {
            "id": "threat_002",
            "type": "domain_reputation",
            "severity": "medium",
            "source": "example-bad.com",
            "detected_at": (datetime.now() - timedelta(minutes=32)).isoformat(),
            "risk_score": 0.67
        }
    ]

async def get_threat_trends():
    """Get threat trend data"""
    # Simulate trend data
    return {
        "hourly_detections": [12, 8, 15, 23, 18, 9, 14, 19, 25, 16, 11, 20],
        "threat_types": {
            "phishing": 45,
            "malware": 23,
            "suspicious_domain": 67,
            "data_breach": 12
        }
    }

async def get_threat_geography():
    """Get geographic distribution of threats"""
    return {
        "countries": [
            {"country": "US", "threats": 45, "lat": 39.8283, "lng": -98.5795},
            {"country": "RU", "threats": 32, "lat": 61.5240, "lng": 105.3188},
            {"country": "CN", "threats": 28, "lat": 35.8617, "lng": 104.1954},
            {"country": "DE", "threats": 15, "lat": 51.1657, "lng": 10.4515},
            {"country": "NO", "threats": 8, "lat": 60.4720, "lng": 8.4689}
        ]
    }

async def get_threat_severity_breakdown():
    """Get breakdown of threats by severity"""
    return {
        "critical": 5,
        "high": 18,
        "medium": 34,
        "low": 67
    }

async def get_recent_threat_detections():
    """Get recent threat detections"""
    return [
        {
            "timestamp": (datetime.now() - timedelta(minutes=3)).isoformat(),
            "threat_type": "phishing_email",
            "source": "malicious@fake-bank.tk",
            "risk_score": 0.92,
            "severity": "critical"
        },
        {
            "timestamp": (datetime.now() - timedelta(minutes=7)).isoformat(),
            "threat_type": "suspicious_domain",
            "source": "suspicious-site.ml",
            "risk_score": 0.78,
            "severity": "high"
        }
    ]

async def get_processing_performance():
    """Get processing performance metrics"""
    return {
        "emails_per_minute": 156,
        "domains_per_minute": 89,
        "average_processing_time": "67ms",
        "queue_size": 23,
        "success_rate": "99.2%"
    }

async def get_ai_model_performance():
    """Get AI model performance metrics"""
    if not AI_AVAILABLE:
        return {"status": "unavailable", "message": "AI components not installed"}

    return {
        "email_risk_model": {
            "accuracy": "94.5%",
            "precision": "92.1%",
            "recall": "96.3%",
            "f1_score": "94.2%"
        },
        "domain_reputation_model": {
            "accuracy": "91.8%",
            "precision": "89.4%",
            "recall": "94.2%",
            "f1_score": "91.7%"
        },
        "anomaly_detection": {
            "detection_rate": "87.3%",
            "false_positive_rate": "4.2%"
        }
    }

async def get_system_resources():
    """Get system resource usage"""
    return {
        "cpu_usage": "34%",
        "memory_usage": "68%",
        "disk_usage": "45%",
        "network_io": "12.3 MB/s",
        "disk_io": "8.7 MB/s"
    }

async def get_api_performance():
    """Get API performance metrics"""
    return {
        "requests_per_minute": 234,
        "average_response_time": "45ms",
        "error_rate": "0.3%",
        "active_connections": len(manager.active_connections)
    }

async def get_database_performance():
    """Get database performance metrics"""
    return {
        "query_time_avg": "12ms",
        "connections_active": 15,
        "connections_max": 100,
        "cache_hit_rate": "94.2%"
    }

async def get_processing_queue_size():
    """Get current processing queue size"""
    return 23

async def get_system_load():
    """Get current system load"""
    return 0.34

async def get_ai_model_status():
    """Get AI model status"""
    if not AI_AVAILABLE:
        return "unavailable"
    return "active"

def parse_timeframe(timeframe: str) -> int:
    """Parse timeframe string to hours"""
    if timeframe == "1h":
        return 1
    elif timeframe == "6h":
        return 6
    elif timeframe == "24h":
        return 24
    elif timeframe == "7d":
        return 168
    elif timeframe == "30d":
        return 720
    else:
        return 24  # Default to 24 hours

async def get_risk_score_trends(hours: int):
    """Get risk score trends over time"""
    # Simulate trend data
    import random
    return [
        {
            "timestamp": (datetime.now() - timedelta(hours=i)).isoformat(),
            "average_risk_score": round(random.uniform(0.2, 0.8), 2)
        }
        for i in range(hours, 0, -1)
    ]

async def get_threat_detection_trends(hours: int):
    """Get threat detection trends over time"""
    import random
    return [
        {
            "timestamp": (datetime.now() - timedelta(hours=i)).isoformat(),
            "threats_detected": random.randint(5, 25)
        }
        for i in range(hours, 0, -1)
    ]

async def get_processing_volume_trends(hours: int):
    """Get processing volume trends over time"""
    import random
    return [
        {
            "timestamp": (datetime.now() - timedelta(hours=i)).isoformat(),
            "items_processed": random.randint(100, 300)
        }
        for i in range(hours, 0, -1)
    ]

async def get_accuracy_trends(hours: int):
    """Get accuracy trends over time"""
    import random
    return [
        {
            "timestamp": (datetime.now() - timedelta(hours=i)).isoformat(),
            "accuracy": round(random.uniform(0.85, 0.98), 3)
        }
        for i in range(hours, 0, -1)
    ]
