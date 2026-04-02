"""Performance testing suite for the API"""
import pytest
import asyncio
import aiohttp
import time
from typing import List
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://localhost:8000/api"
TEST_TOKEN = None  # Will be set during setup

async def setup_test_token():
    """Get authentication token for performance tests"""
    async with aiohttp.ClientSession() as session:
        response = await session.post(
            f"{BASE_URL}/auth/token",
            json={"username": "admin@example.com", "password": "Admin1234"}
        )
        data = await response.json()
        return data["access_token"]

async def make_request(session: aiohttp.ClientSession, endpoint: str):
    """Make a single request to the API"""
    headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
    async with session.get(f"{BASE_URL}/{endpoint}", headers=headers) as response:
        return await response.json()

async def concurrent_requests(endpoint: str, num_requests: int):
    """Make multiple concurrent requests"""
    async with aiohttp.ClientSession() as session:
        tasks = [make_request(session, endpoint) for _ in range(num_requests)]
        return await asyncio.gather(*tasks)

@pytest.mark.asyncio
async def test_api_response_time():
    """Test API endpoint response times"""
    global TEST_TOKEN
    TEST_TOKEN = await setup_test_token()
    
    endpoints = ["leads/", "sources", "exports", "runs"]
    results = {}
    
    for endpoint in endpoints:
        start_time = time.time()
        async with aiohttp.ClientSession() as session:
            await make_request(session, endpoint)
        end_time = time.time()
        
        response_time = end_time - start_time
        results[endpoint] = response_time
        assert response_time < 1.0, f"{endpoint} response time exceeded 1 second"

@pytest.mark.asyncio
async def test_api_concurrent_load():
    """Test API under concurrent load"""
    global TEST_TOKEN
    if not TEST_TOKEN:
        TEST_TOKEN = await setup_test_token()
    
    num_concurrent = 50
    start_time = time.time()
    
    responses = await concurrent_requests("leads/", num_concurrent)
    end_time = time.time()
    
    total_time = end_time - start_time
    avg_time = total_time / num_concurrent
    
    assert avg_time < 2.0, f"Average response time under load exceeded 2 seconds"
    assert all(isinstance(r, dict) and "data" in r and "meta" in r for r in responses), "Some requests failed"

@pytest.mark.asyncio
async def test_memory_usage():
    """Test memory usage under load"""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    # Generate load
    await concurrent_requests("leads/", 100)
    
    final_memory = process.memory_info().rss
    memory_increase = (final_memory - initial_memory) / 1024 / 1024  # Convert to MB
    
    assert memory_increase < 50, f"Memory usage increased by {memory_increase}MB"