"""
Comprehensive Database Operations Functional Testing
Tests CRUD operations, data integrity, performance, and backup/recovery
"""

import time
import json
import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import pymongo
from pymongo import MongoClient
import redis
from typing import Dict, List, Any, Optional
import concurrent.futures
import hashlib
import random
import string

class DatabaseOperationsTester:
    def __init__(self):
        self.test_results = []
        self.performance_metrics = []
        self.connections = {}
        self.test_data = {}

        # Database configurations
        self.db_configs = {
            "postgres": {
                "host": os.getenv("POSTGRES_HOST", "localhost"),
                "port": int(os.getenv("POSTGRES_PORT", 5432)),
                "database": os.getenv("POSTGRES_DB", "osint_db"),
                "user": os.getenv("POSTGRES_USER", "osint_user"),
                "password": os.getenv("POSTGRES_PASSWORD", "osint_password")
            },
            "mongodb": {
                "host": os.getenv("MONGODB_HOST", "localhost"),
                "port": int(os.getenv("MONGODB_PORT", 27017)),
                "database": os.getenv("MONGODB_DB", "osint_db")
            },
            "redis": {
                "host": os.getenv("REDIS_HOST", "localhost"),
                "port": int(os.getenv("REDIS_PORT", 6379)),
                "password": os.getenv("REDIS_PASSWORD", None)
            }
        }

    def record_test_result(self, test_name: str, success: bool, duration: float, details: str = ""):
        """Record test results"""
        self.test_results.append({
            "test": test_name,
            "success": success,
            "duration": duration,
            "details": details,
            "timestamp": time.time()
        })

    def measure_performance(self, operation: str, duration: float, records_processed: int = 1):
        """Record performance metrics"""
        self.performance_metrics.append({
            "operation": operation,
            "duration": duration,
            "records_processed": records_processed,
            "records_per_second": records_processed / duration if duration > 0 else 0,
            "timestamp": time.time()
        })

    def setup_database_connections(self):
        """Setup connections to all database systems"""
        print("🔧 Setting up database connections...")

        # PostgreSQL connection
        try:
            postgres_config = self.db_configs["postgres"]
            self.connections["postgres"] = psycopg2.connect(
                host=postgres_config["host"],
                port=postgres_config["port"],
                database=postgres_config["database"],
                user=postgres_config["user"],
                password=postgres_config["password"]
            )
            print("  ✅ PostgreSQL connection established")
        except Exception as e:
            print(f"  ⚠️  PostgreSQL connection failed: {str(e)}")
            self.connections["postgres"] = None

        # MongoDB connection
        try:
            mongodb_config = self.db_configs["mongodb"]
            mongo_client = MongoClient(
                host=mongodb_config["host"],
                port=mongodb_config["port"]
            )
            self.connections["mongodb"] = mongo_client[mongodb_config["database"]]
            # Test connection
            mongo_client.admin.command('ping')
            print("  ✅ MongoDB connection established")
        except Exception as e:
            print(f"  ⚠️  MongoDB connection failed: {str(e)}")
            self.connections["mongodb"] = None

        # Redis connection
        try:
            redis_config = self.db_configs["redis"]
            self.connections["redis"] = redis.Redis(
                host=redis_config["host"],
                port=redis_config["port"],
                password=redis_config["password"],
                decode_responses=True
            )
            # Test connection
            self.connections["redis"].ping()
            print("  ✅ Redis connection established")
        except Exception as e:
            print(f"  ⚠️  Redis connection failed: {str(e)}")
            self.connections["redis"] = None

    def cleanup_connections(self):
        """Clean up database connections"""
        print("🧹 Cleaning up database connections...")

        if self.connections.get("postgres"):
            try:
                self.connections["postgres"].close()
                print("  ✅ PostgreSQL connection closed")
            except Exception as e:
                print(f"  ⚠️  PostgreSQL cleanup error: {str(e)}")

        if self.connections.get("mongodb"):
            try:
                # MongoDB connection cleanup is handled by client
                print("  ✅ MongoDB connection cleaned up")
            except Exception as e:
                print(f"  ⚠️  MongoDB cleanup error: {str(e)}")

        if self.connections.get("redis"):
            try:
                self.connections["redis"].close()
                print("  ✅ Redis connection closed")
            except Exception as e:
                print(f"  ⚠️  Redis cleanup error: {str(e)}")

    def generate_test_data(self, count: int = 100) -> List[Dict[str, Any]]:
        """Generate test data for database operations"""
        print(f"📊 Generating {count} test records...")

        test_leads = []
        for i in range(count):
            test_leads.append({
                "id": f"test_lead_{i:04d}",
                "email": f"testuser{i:04d}@example.com",
                "name": f"Test User {i:04d}",
                "company": f"Test Company {i % 10}",
                "job_title": random.choice([
                    "Marketing Manager", "Sales Director", "Product Manager",
                    "Software Engineer", "Data Analyst", "Business Developer"
                ]),
                "source": random.choice(["linkedin", "website", "email", "referral"]),
                "score": random.randint(1, 100),
                "status": random.choice(["new", "contacted", "qualified", "converted"]),
                "created_at": time.time() - random.randint(0, 86400 * 30),  # Last 30 days
                "metadata": {
                    "location": random.choice(["Oslo", "Bergen", "Trondheim", "Stavanger"]),
                    "industry": random.choice(["tech", "finance", "healthcare", "retail"]),
                    "company_size": random.choice(["1-10", "11-50", "51-200", "201-1000", "1000+"])
                }
            })

        self.test_data["leads"] = test_leads
        print(f"✅ Generated {count} test leads")
        return test_leads

    def test_postgresql_operations(self):
        """Test PostgreSQL CRUD operations"""
        print("\n🐘 Testing PostgreSQL Operations...")

        if not self.connections.get("postgres"):
            print("  ⚠️  PostgreSQL not available, skipping tests")
            return

        conn = self.connections["postgres"]
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Create test table
            start_time = time.time()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_leads (
                    id VARCHAR(50) PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    company VARCHAR(255),
                    job_title VARCHAR(255),
                    source VARCHAR(50),
                    score INTEGER,
                    status VARCHAR(50),
                    created_at TIMESTAMP,
                    metadata JSONB
                )
            """)
            conn.commit()

            duration = time.time() - start_time
            self.record_test_result("postgres_table_creation", True, duration, "Test table created")
            print(f"  ✅ Table creation ({duration:.3f}s)")

            # Test INSERT operations
            test_leads = self.test_data.get("leads", [])[:50]  # Use first 50 for PostgreSQL

            start_time = time.time()
            for lead in test_leads:
                cursor.execute("""
                    INSERT INTO test_leads (id, email, name, company, job_title, source, score, status, created_at, metadata)
                    VALUES (%(id)s, %(email)s, %(name)s, %(company)s, %(job_title)s, %(source)s, %(score)s, %(status)s,
                           TO_TIMESTAMP(%(created_at)s), %(metadata)s)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        company = EXCLUDED.company,
                        job_title = EXCLUDED.job_title
                """, {
                    **lead,
                    "metadata": json.dumps(lead["metadata"])
                })

            conn.commit()
            duration = time.time() - start_time

            self.record_test_result("postgres_bulk_insert", True, duration, f"Inserted {len(test_leads)} records")
            self.measure_performance("postgres_insert", duration, len(test_leads))
            print(f"  ✅ Bulk insert: {len(test_leads)} records ({duration:.3f}s, {len(test_leads)/duration:.1f} records/sec)")

            # Test SELECT operations
            start_time = time.time()
            cursor.execute("SELECT COUNT(*) as count FROM test_leads")
            count_result = cursor.fetchone()
            duration = time.time() - start_time

            expected_count = len(test_leads)
            actual_count = count_result["count"]
            success = actual_count >= expected_count

            self.record_test_result("postgres_count_query", success, duration, f"Count: {actual_count}")
            print(f"  {'✅' if success else '❌'} Count query: {actual_count} records ({duration:.3f}s)")

            # Test complex SELECT with filtering
            start_time = time.time()
            cursor.execute("""
                SELECT * FROM test_leads
                WHERE score > 70 AND status = 'qualified'
                ORDER BY created_at DESC
                LIMIT 10
            """)
            filtered_results = cursor.fetchall()
            duration = time.time() - start_time

            self.record_test_result("postgres_filtered_query", True, duration, f"Filtered results: {len(filtered_results)}")
            self.measure_performance("postgres_filtered_select", duration, len(filtered_results))
            print(f"  ✅ Filtered query: {len(filtered_results)} results ({duration:.3f}s)")

            # Test UPDATE operations
            start_time = time.time()
            cursor.execute("""
                UPDATE test_leads
                SET status = 'updated', score = score + 10
                WHERE company LIKE 'Test Company%'
            """)
            updated_count = cursor.rowcount
            conn.commit()
            duration = time.time() - start_time

            self.record_test_result("postgres_bulk_update", True, duration, f"Updated {updated_count} records")
            self.measure_performance("postgres_update", duration, updated_count)
            print(f"  ✅ Bulk update: {updated_count} records ({duration:.3f}s)")

            # Test DELETE operations
            start_time = time.time()
            cursor.execute("DELETE FROM test_leads WHERE status = 'updated'")
            deleted_count = cursor.rowcount
            conn.commit()
            duration = time.time() - start_time

            self.record_test_result("postgres_bulk_delete", True, duration, f"Deleted {deleted_count} records")
            self.measure_performance("postgres_delete", duration, deleted_count)
            print(f"  ✅ Bulk delete: {deleted_count} records ({duration:.3f}s)")

        except Exception as e:
            self.record_test_result("postgres_operations", False, 0, f"Error: {str(e)}")
            print(f"  ❌ PostgreSQL operations failed: {str(e)}")

        finally:
            cursor.close()

    def test_mongodb_operations(self):
        """Test MongoDB CRUD operations"""
        print("\n🍃 Testing MongoDB Operations...")

        if not self.connections.get("mongodb"):
            print("  ⚠️  MongoDB not available, skipping tests")
            return

        db = self.connections["mongodb"]
        collection = db.test_leads

        try:
            # Clear existing test data
            collection.delete_many({"id": {"$regex": "^test_lead_"}})

            # Test INSERT operations
            test_leads = self.test_data.get("leads", [])

            start_time = time.time()
            result = collection.insert_many(test_leads)
            duration = time.time() - start_time

            inserted_count = len(result.inserted_ids)
            success = inserted_count == len(test_leads)

            self.record_test_result("mongodb_bulk_insert", success, duration, f"Inserted {inserted_count} documents")
            self.measure_performance("mongodb_insert", duration, inserted_count)
            print(f"  {'✅' if success else '❌'} Bulk insert: {inserted_count} documents ({duration:.3f}s, {inserted_count/duration:.1f} docs/sec)")

            # Test COUNT operations
            start_time = time.time()
            count = collection.count_documents({})
            duration = time.time() - start_time

            self.record_test_result("mongodb_count_query", True, duration, f"Count: {count}")
            print(f"  ✅ Count query: {count} documents ({duration:.3f}s)")

            # Test complex aggregation query
            start_time = time.time()
            pipeline = [
                {"$match": {"score": {"$gt": 70}}},
                {"$group": {
                    "_id": "$company",
                    "avg_score": {"$avg": "$score"},
                    "count": {"$sum": 1}
                }},
                {"$sort": {"avg_score": -1}},
                {"$limit": 5}
            ]

            aggregation_results = list(collection.aggregate(pipeline))
            duration = time.time() - start_time

            self.record_test_result("mongodb_aggregation", True, duration, f"Aggregation results: {len(aggregation_results)}")
            self.measure_performance("mongodb_aggregation", duration, len(aggregation_results))
            print(f"  ✅ Aggregation query: {len(aggregation_results)} groups ({duration:.3f}s)")

            # Test UPDATE operations
            start_time = time.time()
            update_result = collection.update_many(
                {"company": {"$regex": "Test Company"}},
                {"$set": {"status": "updated"}, "$inc": {"score": 5}}
            )
            duration = time.time() - start_time

            updated_count = update_result.modified_count
            self.record_test_result("mongodb_bulk_update", True, duration, f"Updated {updated_count} documents")
            self.measure_performance("mongodb_update", duration, updated_count)
            print(f"  ✅ Bulk update: {updated_count} documents ({duration:.3f}s)")

            # Test INDEX creation and query performance
            start_time = time.time()
            collection.create_index([("email", 1), ("company", 1)])
            duration = time.time() - start_time

            self.record_test_result("mongodb_index_creation", True, duration, "Email+Company index created")
            print(f"  ✅ Index creation ({duration:.3f}s)")

            # Test indexed query
            start_time = time.time()
            indexed_results = list(collection.find({"company": "Test Company 1"}).limit(10))
            duration = time.time() - start_time

            self.record_test_result("mongodb_indexed_query", True, duration, f"Indexed results: {len(indexed_results)}")
            print(f"  ✅ Indexed query: {len(indexed_results)} results ({duration:.3f}s)")

            # Test DELETE operations
            start_time = time.time()
            delete_result = collection.delete_many({"status": "updated"})
            duration = time.time() - start_time

            deleted_count = delete_result.deleted_count
            self.record_test_result("mongodb_bulk_delete", True, duration, f"Deleted {deleted_count} documents")
            self.measure_performance("mongodb_delete", duration, deleted_count)
            print(f"  ✅ Bulk delete: {deleted_count} documents ({duration:.3f}s)")

        except Exception as e:
            self.record_test_result("mongodb_operations", False, 0, f"Error: {str(e)}")
            print(f"  ❌ MongoDB operations failed: {str(e)}")

    def test_redis_operations(self):
        """Test Redis cache operations"""
        print("\n🔴 Testing Redis Operations...")

        if not self.connections.get("redis"):
            print("  ⚠️  Redis not available, skipping tests")
            return

        redis_client = self.connections["redis"]

        try:
            # Test basic SET/GET operations
            test_data = {"key": "value", "number": 42, "list": [1, 2, 3]}

            start_time = time.time()
            redis_client.set("test:data", json.dumps(test_data))
            duration = time.time() - start_time

            self.record_test_result("redis_set_operation", True, duration, "JSON data stored")
            print(f"  ✅ SET operation ({duration:.3f}s)")

            start_time = time.time()
            retrieved_data = json.loads(redis_client.get("test:data"))
            duration = time.time() - start_time

            success = retrieved_data == test_data
            self.record_test_result("redis_get_operation", success, duration, "JSON data retrieved")
            print(f"  {'✅' if success else '❌'} GET operation ({duration:.3f}s)")

            # Test bulk operations
            test_keys = {}
            for i in range(100):
                key = f"test:lead:{i:04d}"
                value = json.dumps({"id": i, "score": random.randint(1, 100)})
                test_keys[key] = value

            start_time = time.time()
            redis_client.mset(test_keys)
            duration = time.time() - start_time

            self.record_test_result("redis_bulk_set", True, duration, f"Set {len(test_keys)} keys")
            self.measure_performance("redis_mset", duration, len(test_keys))
            print(f"  ✅ Bulk SET: {len(test_keys)} keys ({duration:.3f}s, {len(test_keys)/duration:.1f} ops/sec)")

            # Test batch retrieval
            start_time = time.time()
            retrieved_values = redis_client.mget(list(test_keys.keys()))
            duration = time.time() - start_time

            success = len([v for v in retrieved_values if v is not None]) == len(test_keys)
            self.record_test_result("redis_bulk_get", success, duration, f"Retrieved {len(retrieved_values)} values")
            self.measure_performance("redis_mget", duration, len(retrieved_values))
            print(f"  {'✅' if success else '❌'} Bulk GET: {len(retrieved_values)} values ({duration:.3f}s, {len(retrieved_values)/duration:.1f} ops/sec)")

            # Test LIST operations
            list_key = "test:list"
            start_time = time.time()

            # Add items to list
            for i in range(50):
                redis_client.lpush(list_key, f"item_{i}")

            duration = time.time() - start_time

            self.record_test_result("redis_list_operations", True, duration, "List operations completed")
            print(f"  ✅ List PUSH operations: 50 items ({duration:.3f}s)")

            # Get list length and items
            start_time = time.time()
            list_length = redis_client.llen(list_key)
            list_items = redis_client.lrange(list_key, 0, 9)  # Get first 10 items
            duration = time.time() - start_time

            success = list_length == 50 and len(list_items) == 10
            self.record_test_result("redis_list_retrieval", success, duration, f"List length: {list_length}")
            print(f"  {'✅' if success else '❌'} List retrieval: length={list_length}, items={len(list_items)} ({duration:.3f}s)")

            # Test SET (collection) operations
            set_key = "test:set"
            start_time = time.time()

            for i in range(30):
                redis_client.sadd(set_key, f"member_{i}")

            duration = time.time() - start_time

            set_size = redis_client.scard(set_key)
            success = set_size == 30

            self.record_test_result("redis_set_operations", success, duration, f"Set size: {set_size}")
            print(f"  {'✅' if success else '❌'} SET operations: {set_size} members ({duration:.3f}s)")

            # Test expiration
            start_time = time.time()
            redis_client.setex("test:expire", 2, "expiring_value")  # 2 seconds TTL
            time.sleep(1)
            value_before = redis_client.get("test:expire")
            time.sleep(2)
            value_after = redis_client.get("test:expire")
            duration = time.time() - start_time

            success = value_before is not None and value_after is None
            self.record_test_result("redis_expiration", success, duration, "TTL functionality tested")
            print(f"  {'✅' if success else '❌'} Expiration test ({duration:.3f}s)")

            # Cleanup test keys
            start_time = time.time()
            keys_to_delete = redis_client.keys("test:*")
            if keys_to_delete:
                redis_client.delete(*keys_to_delete)
            duration = time.time() - start_time

            print(f"  ✅ Cleanup: {len(keys_to_delete)} keys deleted ({duration:.3f}s)")

        except Exception as e:
            self.record_test_result("redis_operations", False, 0, f"Error: {str(e)}")
            print(f"  ❌ Redis operations failed: {str(e)}")

    def test_concurrent_operations(self):
        """Test database performance under concurrent load"""
        print("\n⚡ Testing Concurrent Database Operations...")

        def postgres_concurrent_test():
            if not self.connections.get("postgres"):
                return {"postgres": None}

            try:
                # Create separate connection for concurrent test
                config = self.db_configs["postgres"]
                conn = psycopg2.connect(
                    host=config["host"],
                    port=config["port"],
                    database=config["database"],
                    user=config["user"],
                    password=config["password"]
                )

                cursor = conn.cursor()

                # Perform multiple operations
                operations = 0
                start_time = time.time()

                for i in range(10):
                    cursor.execute("SELECT COUNT(*) FROM test_leads WHERE score > %s", (random.randint(1, 100),))
                    cursor.fetchone()
                    operations += 1

                duration = time.time() - start_time
                cursor.close()
                conn.close()

                return {
                    "postgres": {
                        "operations": operations,
                        "duration": duration,
                        "ops_per_second": operations / duration
                    }
                }

            except Exception as e:
                return {"postgres": {"error": str(e)}}

        def mongodb_concurrent_test():
            if not self.connections.get("mongodb"):
                return {"mongodb": None}

            try:
                # Use existing connection for concurrent test
                db = self.connections["mongodb"]
                collection = db.test_leads

                operations = 0
                start_time = time.time()

                for i in range(10):
                    list(collection.find({"score": {"$gt": random.randint(1, 100)}}).limit(5))
                    operations += 1

                duration = time.time() - start_time

                return {
                    "mongodb": {
                        "operations": operations,
                        "duration": duration,
                        "ops_per_second": operations / duration
                    }
                }

            except Exception as e:
                return {"mongodb": {"error": str(e)}}

        def redis_concurrent_test():
            if not self.connections.get("redis"):
                return {"redis": None}

            try:
                redis_client = self.connections["redis"]

                operations = 0
                start_time = time.time()

                for i in range(100):  # Redis can handle more ops
                    redis_client.set(f"concurrent:test:{i}", f"value_{i}")
                    redis_client.get(f"concurrent:test:{i}")
                    operations += 2

                duration = time.time() - start_time

                return {
                    "redis": {
                        "operations": operations,
                        "duration": duration,
                        "ops_per_second": operations / duration
                    }
                }

            except Exception as e:
                return {"redis": {"error": str(e)}}

        # Run concurrent tests
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            # Submit multiple concurrent tasks for each database
            futures = []

            # 2 threads for each database type
            for _ in range(2):
                futures.append(executor.submit(postgres_concurrent_test))
                futures.append(executor.submit(mongodb_concurrent_test))
                futures.append(executor.submit(redis_concurrent_test))

            # Collect results
            results = []
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())

        total_duration = time.time() - start_time

        # Aggregate results
        aggregated = {"postgres": [], "mongodb": [], "redis": []}

        for result in results:
            for db_type, data in result.items():
                if data and "error" not in data:
                    aggregated[db_type].append(data)

        # Calculate averages and report
        for db_type, data_list in aggregated.items():
            if data_list:
                avg_ops_per_sec = sum(d["ops_per_second"] for d in data_list) / len(data_list)
                total_ops = sum(d["operations"] for d in data_list)

                success = avg_ops_per_sec > 0
                details = f"Avg: {avg_ops_per_sec:.1f} ops/sec, Total ops: {total_ops}"

                self.record_test_result(f"concurrent_{db_type}", success, total_duration, details)
                print(f"  {'✅' if success else '❌'} {db_type.capitalize()}: {details}")
            else:
                print(f"  ⚠️  {db_type.capitalize()}: No concurrent test data")

    def test_data_integrity(self):
        """Test data consistency and integrity constraints"""
        print("\n🔍 Testing Data Integrity...")

        # Test PostgreSQL constraints
        if self.connections.get("postgres"):
            conn = self.connections["postgres"]
            cursor = conn.cursor()

            try:
                start_time = time.time()

                # Test unique constraint
                try:
                    cursor.execute("""
                        INSERT INTO test_leads (id, email, name, company, job_title, source, score, status, created_at)
                        VALUES ('duplicate_test', 'duplicate@test.com', 'Test', 'Test Co', 'Manager', 'test', 50, 'new', NOW())
                    """)
                    conn.commit()

                    # Try to insert duplicate
                    cursor.execute("""
                        INSERT INTO test_leads (id, email, name, company, job_title, source, score, status, created_at)
                        VALUES ('duplicate_test_2', 'duplicate@test.com', 'Test 2', 'Test Co', 'Manager', 'test', 60, 'new', NOW())
                    """)
                    conn.commit()

                    # Should not reach here
                    duplicate_constraint_working = False

                except psycopg2.IntegrityError:
                    conn.rollback()
                    duplicate_constraint_working = True

                duration = time.time() - start_time

                self.record_test_result("postgres_unique_constraint", duplicate_constraint_working, duration, "Email uniqueness tested")
                print(f"  {'✅' if duplicate_constraint_working else '❌'} PostgreSQL unique constraint ({duration:.3f}s)")

            except Exception as e:
                self.record_test_result("postgres_integrity", False, 0, f"Error: {str(e)}")
                print(f"  ❌ PostgreSQL integrity test failed: {str(e)}")

            finally:
                cursor.close()

        # Test MongoDB data consistency
        if self.connections.get("mongodb"):
            db = self.connections["mongodb"]
            collection = db.test_leads

            try:
                start_time = time.time()

                # Insert test document
                test_doc = {
                    "id": "integrity_test",
                    "email": "integrity@test.com",
                    "name": "Integrity Test",
                    "score": 75
                }

                collection.insert_one(test_doc)

                # Read it back
                retrieved_doc = collection.find_one({"id": "integrity_test"})

                # Verify data matches
                data_matches = (
                    retrieved_doc["email"] == test_doc["email"] and
                    retrieved_doc["name"] == test_doc["name"] and
                    retrieved_doc["score"] == test_doc["score"]
                )

                duration = time.time() - start_time

                self.record_test_result("mongodb_data_consistency", data_matches, duration, "Data consistency verified")
                print(f"  {'✅' if data_matches else '❌'} MongoDB data consistency ({duration:.3f}s)")

                # Cleanup
                collection.delete_one({"id": "integrity_test"})

            except Exception as e:
                self.record_test_result("mongodb_integrity", False, 0, f"Error: {str(e)}")
                print(f"  ❌ MongoDB integrity test failed: {str(e)}")

    def test_backup_recovery(self):
        """Test backup and recovery procedures"""
        print("\n💾 Testing Backup & Recovery...")

        # Test PostgreSQL backup simulation
        if self.connections.get("postgres"):
            try:
                start_time = time.time()

                # Simulate backup by counting records before
                conn = self.connections["postgres"]
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM test_leads")
                records_before = cursor.fetchone()[0]

                # Simulate data loss scenario
                cursor.execute("DELETE FROM test_leads WHERE id LIKE 'test_lead_%'")
                conn.commit()

                # Simulate recovery by re-inserting data
                test_leads = self.test_data.get("leads", [])[:10]  # Use subset for recovery test
                for lead in test_leads:
                    cursor.execute("""
                        INSERT INTO test_leads (id, email, name, company, job_title, source, score, status, created_at, metadata)
                        VALUES (%(id)s, %(email)s, %(name)s, %(company)s, %(job_title)s, %(source)s, %(score)s, %(status)s,
                               TO_TIMESTAMP(%(created_at)s), %(metadata)s)
                    """, {
                        **lead,
                        "metadata": json.dumps(lead["metadata"])
                    })
                conn.commit()

                # Verify recovery
                cursor.execute("SELECT COUNT(*) FROM test_leads WHERE id LIKE 'test_lead_%'")
                records_after = cursor.fetchone()[0]

                duration = time.time() - start_time
                recovery_success = records_after == len(test_leads)

                self.record_test_result("postgres_backup_recovery", recovery_success, duration,
                                       f"Recovered {records_after}/{len(test_leads)} records")
                print(f"  {'✅' if recovery_success else '❌'} PostgreSQL backup/recovery simulation ({duration:.3f}s)")

                cursor.close()

            except Exception as e:
                self.record_test_result("postgres_backup_recovery", False, 0, f"Error: {str(e)}")
                print(f"  ❌ PostgreSQL backup/recovery test failed: {str(e)}")

        # Test MongoDB backup simulation
        if self.connections.get("mongodb"):
            try:
                start_time = time.time()

                db = self.connections["mongodb"]
                collection = db.test_leads

                # Get current document count
                docs_before = collection.count_documents({})

                # Simulate backup by exporting data
                backup_data = list(collection.find({"id": {"$regex": "^test_lead_"}}))

                # Simulate data loss
                collection.delete_many({"id": {"$regex": "^test_lead_"}})

                # Simulate recovery
                if backup_data:
                    collection.insert_many(backup_data)

                # Verify recovery
                docs_after = collection.count_documents({"id": {"$regex": "^test_lead_"}})

                duration = time.time() - start_time
                recovery_success = docs_after == len(backup_data)

                self.record_test_result("mongodb_backup_recovery", recovery_success, duration,
                                       f"Recovered {docs_after}/{len(backup_data)} documents")
                print(f"  {'✅' if recovery_success else '❌'} MongoDB backup/recovery simulation ({duration:.3f}s)")

            except Exception as e:
                self.record_test_result("mongodb_backup_recovery", False, 0, f"Error: {str(e)}")
                print(f"  ❌ MongoDB backup/recovery test failed: {str(e)}")

    def generate_performance_report(self):
        """Generate database performance report"""
        print("\n📈 Database Performance Report:")
        print("=" * 50)

        if not self.performance_metrics:
            print("No performance metrics collected")
            return

        # Group by database type and operation
        db_metrics = {}
        for metric in self.performance_metrics:
            parts = metric["operation"].split("_")
            db_type = parts[0]
            operation = "_".join(parts[1:])

            if db_type not in db_metrics:
                db_metrics[db_type] = {}
            if operation not in db_metrics[db_type]:
                db_metrics[db_type][operation] = []

            db_metrics[db_type][operation].append(metric)

        # Generate report for each database
        for db_type, operations in db_metrics.items():
            print(f"\n{db_type.upper()} Performance:")

            for operation, metrics_list in operations.items():
                if not metrics_list:
                    continue

                avg_duration = sum(m["duration"] for m in metrics_list) / len(metrics_list)
                avg_records_per_sec = sum(m["records_per_second"] for m in metrics_list) / len(metrics_list)
                total_records = sum(m["records_processed"] for m in metrics_list)

                print(f"  {operation.replace('_', ' ').title()}:")
                print(f"    Operations: {len(metrics_list)}")
                print(f"    Avg duration: {avg_duration:.3f}s")
                print(f"    Total records: {total_records}")
                print(f"    Avg throughput: {avg_records_per_sec:.1f} records/sec")

        return db_metrics

    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n📋 Database Operations Test Report:")
        print("=" * 60)

        if not self.test_results:
            print("No test results to report")
            return

        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r["success"]])
        success_rate = (successful_tests / total_tests) * 100

        print(f"\nOverall Results:")
        print(f"  Total tests: {total_tests}")
        print(f"  Successful: {successful_tests}")
        print(f"  Success rate: {success_rate:.1f}%")

        # Group results by database type
        db_results = {}
        for result in self.test_results:
            parts = result["test"].split("_")
            db_type = parts[0] if parts[0] in ["postgres", "mongodb", "redis", "concurrent"] else "general"

            if db_type not in db_results:
                db_results[db_type] = []
            db_results[db_type].append(result)

        print(f"\nResults by Database:")
        for db_type, results in db_results.items():
            successful = len([r for r in results if r["success"]])
            total = len(results)
            rate = (successful / total) * 100 if total > 0 else 0
            print(f"  {db_type.capitalize()}: {successful}/{total} ({rate:.1f}%)")

        # Show failed tests
        failed_tests = [r for r in self.test_results if not r["success"]]
        if failed_tests:
            print(f"\nFailed Tests:")
            for test in failed_tests:
                print(f"  ❌ {test['test']}: {test['details']}")

        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": success_rate,
            "database_results": db_results,
            "failed_tests": failed_tests
        }

    def run_all_tests(self):
        """Run all database operation tests"""
        print("🚀 Starting Comprehensive Database Operations Testing")
        print("=" * 70)

        try:
            self.setup_database_connections()
            self.generate_test_data(100)

            # Run all database tests
            self.test_postgresql_operations()
            self.test_mongodb_operations()
            self.test_redis_operations()
            self.test_concurrent_operations()
            self.test_data_integrity()
            self.test_backup_recovery()

            print("\n✅ All database operation tests completed!")

            # Generate reports
            performance_report = self.generate_performance_report()
            test_report = self.generate_test_report()

            return {
                "test_report": test_report,
                "performance_report": performance_report
            }

        except Exception as e:
            print(f"\n❌ Database testing failed: {str(e)}")
            raise

        finally:
            self.cleanup_connections()


if __name__ == "__main__":
    # Run the tests
    tester = DatabaseOperationsTester()
    reports = tester.run_all_tests()

    # Save reports to files
    with open("database_test_report.json", "w") as f:
        json.dump(reports["test_report"], f, indent=2)

    with open("database_performance_report.json", "w") as f:
        json.dump(reports["performance_report"], f, indent=2, default=str)

    print(f"\n📄 Reports saved to database_test_report.json and database_performance_report.json")
