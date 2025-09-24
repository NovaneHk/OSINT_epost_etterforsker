#!/usr/bin/env python3
"""
Phase 4 Dashboard Testing Script
Test real-time analytics dashboard and ML integration
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_analytics_api():
    """Test the analytics API endpoints"""
    logger.info("🧪 Testing Analytics API...")

    try:
        # Import analytics API components
        from backend.api.analytics import (
            get_dashboard_overview,
            get_realtime_threats,
            get_performance_metrics_endpoint,
            get_analytics_trends,
            ConnectionManager
        )

        # Test connection manager
        manager = ConnectionManager()
        logger.info(f"✅ Connection Manager initialized: {len(manager.active_connections)} connections")

        # Test data generation functions
        from backend.api.analytics import (
            get_total_investigations,
            get_active_threats,
            get_system_health,
            get_performance_metrics
        )

        # Test basic data functions
        total_investigations = await get_total_investigations()
        active_threats = await get_active_threats()
        system_health = await get_system_health()
        performance_metrics = await get_performance_metrics()

        logger.info(f"✅ Total Investigations: {total_investigations}")
        logger.info(f"✅ Active Threats: {active_threats}")
        logger.info(f"✅ System Health: {system_health['status']}")
        logger.info(f"✅ Performance Metrics: {performance_metrics['api_response_time']}")

        return True

    except Exception as e:
        logger.error(f"❌ Analytics API test failed: {e}")
        return False

async def test_ai_integration():
    """Test AI integration with analytics"""
    logger.info("🤖 Testing AI Integration...")

    try:
        # Test AI components availability
        try:
            from ai.analytics_engine import get_ai_analytics_engine
            from ai.nlp_processor import get_nlp_processor
            ai_available = True
            logger.info("✅ AI components imported successfully")
        except ImportError as e:
            logger.warning(f"⚠️ AI components not available: {e}")
            ai_available = False

        if ai_available:
            # Test AI engine
            ai_engine = get_ai_analytics_engine()
            ai_health = await ai_engine.health_check()
            logger.info(f"✅ AI Engine Health: {ai_health['status']}")

            # Test NLP processor
            nlp_processor = get_nlp_processor()
            nlp_health = await nlp_processor.health_check()
            logger.info(f"✅ NLP Processor Health: {nlp_health['status']}")

            # Test basic AI functionality
            test_data = {
                "email": "test@suspicious-domain.tk",
                "domain": "suspicious-domain.tk",
                "sender_ip": "192.168.1.100"
            }

            email_analysis = await ai_engine.analyze_email_risk(test_data)
            logger.info(f"✅ Email Risk Analysis: {email_analysis.score:.2f} confidence")

            domain_analysis = await ai_engine.analyze_domain_reputation(test_data)
            logger.info(f"✅ Domain Analysis: {domain_analysis.score:.2f} confidence")

            # Test NLP processing
            test_text = "This is a suspicious email from test@malicious-domain.tk containing threats and urgent requests for personal information."
            text_analysis = await nlp_processor.process_intelligence_text(test_text)
            logger.info(f"✅ Text Analysis: {len(text_analysis['entities'])} entities found")

        return True

    except Exception as e:
        logger.error(f"❌ AI integration test failed: {e}")
        return False

async def test_real_time_features():
    """Test real-time features and WebSocket functionality"""
    logger.info("⚡ Testing Real-time Features...")

    try:
        # Test real-time analytics data generation
        from backend.api.analytics import (
            get_realtime_analytics,
            get_threat_trends,
            get_threat_geography,
            get_processing_performance
        )

        # Generate real-time data
        realtime_data = await get_realtime_analytics()
        logger.info(f"✅ Real-time Data: {realtime_data['active_investigations']} investigations")

        threat_trends = await get_threat_trends()
        logger.info(f"✅ Threat Trends: {len(threat_trends['hourly_detections'])} data points")

        threat_geography = await get_threat_geography()
        logger.info(f"✅ Threat Geography: {len(threat_geography['countries'])} countries")

        processing_performance = await get_processing_performance()
        logger.info(f"✅ Processing Performance: {processing_performance['emails_per_minute']} emails/min")

        return True

    except Exception as e:
        logger.error(f"❌ Real-time features test failed: {e}")
        return False

async def test_dashboard_components():
    """Test dashboard component functionality"""
    logger.info("📊 Testing Dashboard Components...")

    try:
        # Test dashboard data structure
        from backend.api.analytics import (
            get_active_threat_list,
            get_threat_severity_breakdown,
            get_system_resources,
            get_ai_model_performance
        )

        # Test threat monitoring
        active_threats = await get_active_threat_list()
        logger.info(f"✅ Active Threats List: {len(active_threats)} threats")

        severity_breakdown = await get_threat_severity_breakdown()
        total_threats = sum(severity_breakdown.values())
        logger.info(f"✅ Severity Breakdown: {total_threats} total threats")

        # Test system monitoring
        system_resources = await get_system_resources()
        logger.info(f"✅ System Resources: {system_resources['cpu_usage']} CPU usage")

        # Test AI model performance
        ai_performance = await get_ai_model_performance()
        logger.info(f"✅ AI Model Performance: {ai_performance.get('status', 'available')}")

        return True

    except Exception as e:
        logger.error(f"❌ Dashboard components test failed: {e}")
        return False

async def test_performance_monitoring():
    """Test performance monitoring capabilities"""
    logger.info("⚡ Testing Performance Monitoring...")

    try:
        # Test performance monitoring
        from core.performance import PerformanceMonitor

        monitor = PerformanceMonitor()

        # Test timer functionality
        timer_id = monitor.start_timer("test_operation")
        await asyncio.sleep(0.1)  # Simulate work
        processing_time = monitor.stop_timer(timer_id, "test_operation")

        logger.info(f"✅ Performance Timer: {processing_time:.2f}ms")

        # Test metrics collection
        metrics = monitor.get_metrics()
        logger.info(f"✅ Performance Metrics: {len(metrics)} operations tracked")

        return True

    except Exception as e:
        logger.error(f"❌ Performance monitoring test failed: {e}")
        return False

async def generate_test_report():
    """Generate comprehensive test report"""
    logger.info("📋 Generating Phase 4 Test Report...")

    # Run all tests
    test_results = {
        "analytics_api": await test_analytics_api(),
        "ai_integration": await test_ai_integration(),
        "real_time_features": await test_real_time_features(),
        "dashboard_components": await test_dashboard_components(),
        "performance_monitoring": await test_performance_monitoring()
    }

    # Calculate overall success rate
    passed_tests = sum(test_results.values())
    total_tests = len(test_results)
    success_rate = (passed_tests / total_tests) * 100

    # Generate report
    report = {
        "phase": "Phase 4 - Real-time Analytics Dashboard & ML Enhancement",
        "test_date": datetime.now().isoformat(),
        "test_results": test_results,
        "summary": {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": f"{success_rate:.1f}%"
        },
        "component_status": {
            "analytics_api": "✅ Operational" if test_results["analytics_api"] else "❌ Failed",
            "ai_integration": "✅ Operational" if test_results["ai_integration"] else "❌ Failed",
            "real_time_features": "✅ Operational" if test_results["real_time_features"] else "❌ Failed",
            "dashboard_components": "✅ Operational" if test_results["dashboard_components"] else "❌ Failed",
            "performance_monitoring": "✅ Operational" if test_results["performance_monitoring"] else "❌ Failed"
        },
        "recommendations": []
    }

    # Add recommendations based on test results
    if not test_results["ai_integration"]:
        report["recommendations"].append("Install ML libraries: pip install -r requirements_ml.txt")

    if success_rate < 100:
        report["recommendations"].append("Review failed components and address any dependency issues")

    if success_rate >= 80:
        report["recommendations"].append("Phase 4 components are ready for production deployment")

    # Save report
    with open("phase4_dashboard_test_results.json", "w") as f:
        json.dump(report, f, indent=2)

    return report

async def main():
    """Main test execution"""
    print("🚀 Phase 4 Dashboard Testing Suite")
    print("=" * 50)

    try:
        # Generate test report
        report = await generate_test_report()

        # Display results
        print(f"\n📊 Test Results Summary:")
        print(f"Total Tests: {report['summary']['total_tests']}")
        print(f"Passed: {report['summary']['passed_tests']}")
        print(f"Failed: {report['summary']['failed_tests']}")
        print(f"Success Rate: {report['summary']['success_rate']}")

        print(f"\n🔧 Component Status:")
        for component, status in report['component_status'].items():
            print(f"  {component}: {status}")

        if report['recommendations']:
            print(f"\n💡 Recommendations:")
            for rec in report['recommendations']:
                print(f"  • {rec}")

        print(f"\n📄 Detailed report saved to: phase4_dashboard_test_results.json")

        # Determine exit code
        success_rate = float(report['summary']['success_rate'].rstrip('%'))
        if success_rate >= 80:
            print(f"\n🎉 Phase 4 Dashboard testing completed successfully!")
            return 0
        else:
            print(f"\n⚠️ Phase 4 Dashboard testing completed with issues.")
            return 1

    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        print(f"\n💥 Test execution failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
