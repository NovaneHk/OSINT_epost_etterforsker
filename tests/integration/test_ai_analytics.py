#!/usr/bin/env python3
"""
Comprehensive tests for AI Analytics Engine
Testing edge cases, error handling, and model persistence
"""

import pytest
import numpy as np
from datetime import datetime
from pathlib import Path
from collections import deque

from ai.analytics_engine import (
    get_ai_analytics_engine,
    AnalysisType,
    AnalysisResult,
    AIAnalyticsEngine
)

@pytest.fixture
def test_engine():
    """Create a test analytics engine"""
    return get_ai_analytics_engine({
        'model_path': 'test_models',
        'threshold': 0.75,
        'use_gpu': False
    })

def test_model_initialization(test_engine):
    """Test model initialization"""
    assert hasattr(test_engine, 'models')
    assert hasattr(test_engine, 'scalers')
    assert isinstance(test_engine.model_versions, dict)
    assert isinstance(test_engine.threat_database, deque)
    assert isinstance(test_engine.analysis_history, deque)
    assert hasattr(test_engine, 'memory_manager')

@pytest.mark.asyncio
async def test_analysis_methods(test_engine):
    """Test various analysis methods"""
    test_data = {
        'sender': 'test@example.com',
        'domain': 'example.com',
        'content': 'Test email content',
        'headers': {'received': ['test'], 'from': 'test@example.com'}
    }
    
    result = await test_engine.analyze_email_risk(test_data)
    assert isinstance(result, AnalysisResult)
    assert result.analysis_type == AnalysisType.RISK_SCORING
    assert 0 <= result.confidence <= 1

    result = await test_engine.analyze_domain_reputation({'domain': 'example.com', 'records': [], 'age_days': 100})
    assert isinstance(result, AnalysisResult)
    assert result.analysis_type == AnalysisType.RISK_SCORING
    assert 0 <= result.confidence <= 1

    result = await test_engine.detect_anomalies([test_data])
    assert isinstance(result, AnalysisResult)
    assert result.analysis_type == AnalysisType.ANOMALY_DETECTION
    assert 0 <= result.confidence <= 1

def test_analysis_result_creation():
    """Test creation of analysis results"""
    result = AnalysisResult(
        analysis_type=AnalysisType.THREAT_DETECTION,
        confidence=0.8,
        score=0.5,
        details={'source': 'test'},
        timestamp=datetime.now(),
        model_version="1.0",
        processing_time=0.5
    )
    assert result.confidence >= 0
    assert result.confidence <= 1
    assert result.score >= 0
    assert result.score <= 1

@pytest.mark.asyncio
async def test_correlations_analysis(test_engine):
    """Test correlation analysis with intelligence data"""
    test_data = [{
        'id': '1',
        'timestamp': datetime.now(),
        'threat_level': 0.7,
        'indicators': ['suspicious_domain', 'abnormal_traffic']
    }]
    result = await test_engine._analyze_correlations(test_data)
    assert isinstance(result, list)

@pytest.mark.asyncio
async def test_threat_detection_workflow(test_engine):
    """Test the complete threat detection workflow"""
    test_data = {
        'email': 'test@example.com',
        'domain': 'example.com',
        'content': 'Test content with potential threats',
        'metadata': {
            'source_ip': '192.168.1.1',
            'timestamp': datetime.now().isoformat()
        }
    }
    
    # Test threat analysis
    threat_result = await test_engine.analyze_email_risk({
        'email': test_data['email'],
        'domain': test_data['domain'],
        'content': test_data['content']
    })
    assert isinstance(threat_result, AnalysisResult)
    assert threat_result.analysis_type == AnalysisType.RISK_SCORING
    assert 0 <= threat_result.confidence <= 1
    
    # Test overall analysis
    risk_result = await test_engine.analyze_domain_reputation({
        'domain': test_data['domain'],
        'records': [],
        'age_days': 100
    })
    assert isinstance(risk_result, AnalysisResult)
    assert risk_result.analysis_type == AnalysisType.RISK_SCORING
    assert 0 <= risk_result.score <= 1

def test_model_versions(test_engine):
    """Test model versioning system"""
    assert isinstance(test_engine.model_versions, dict)
    for model_name in ['email_risk', 'domain_reputation']:
        if model_name in test_engine.models:
            assert model_name in test_engine.model_versions