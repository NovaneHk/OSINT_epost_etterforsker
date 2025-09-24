#!/usr/bin/env python3
"""
Quick test script to generate sample email data for testing the OSINT system
"""

import sqlite3
import os
from datetime import datetime, timedelta
import random

def create_sample_data():
    """Create sample data for testing email extraction and export"""

    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)

    # Connect to database
    db_path = 'data/osint_cache.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables if they don't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            domain TEXT,
            sector TEXT,
            location TEXT,
            size_estimate INTEGER,
            technology_stack TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            company_id INTEGER,
            name TEXT,
            title TEXT,
            confidence_score REAL,
            source TEXT,
            persona_match TEXT,
            validation_status TEXT DEFAULT 'pending',
            risk_score INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_seeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            persona TEXT,
            sector TEXT,
            geography TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Sample companies data
    companies = [
        ("TechNorway AS", "technorway.no", "technology", "Oslo, Norway", 50, "React,Python,AWS"),
        ("Nordic Software Solutions", "nordicsoftware.se", "technology", "Stockholm, Sweden", 120, "Angular,Java,Azure"),
        ("Danish Digital Agency", "danishdigital.dk", "technology", "Copenhagen, Denmark", 80, "Vue.js,Node.js,GCP"),
        ("Finnish Fintech Oy", "finnishfintech.fi", "technology", "Helsinki, Finland", 200, "React,Python,Kubernetes"),
        ("Icelandic Innovation", "icelandicinnovation.is", "technology", "Reykjavik, Iceland", 30, "JavaScript,Docker,MongoDB"),
        ("Bergen Tech Hub", "bergentechhub.no", "technology", "Bergen, Norway", 75, "TypeScript,PostgreSQL,Redis"),
        ("Gothenburg Software", "gothenburgsoftware.se", "technology", "Gothenburg, Sweden", 95, "Python,Django,Celery"),
        ("Aarhus Analytics", "aarhusanalytics.dk", "technology", "Aarhus, Denmark", 60, "R,Python,Spark"),
        ("Tampere Tech", "tamperetech.fi", "technology", "Tampere, Finland", 110, "Scala,Kafka,Elasticsearch"),
        ("Malmö Mobile", "malmomobile.se", "technology", "Malmö, Sweden", 40, "React Native,Swift,Kotlin")
    ]

    # Insert companies
    company_ids = []
    for company in companies:
        cursor.execute('''
            INSERT OR IGNORE INTO companies (name, domain, sector, location, size_estimate, technology_stack)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', company)

        # Get the company ID
        cursor.execute('SELECT id FROM companies WHERE name = ?', (company[0],))
        result = cursor.fetchone()
        if result:
            company_ids.append(result[0])

    # Sample email data with realistic Nordic names and titles
    email_templates = [
        # Technical leaders
        ("Lars", "Andersen", "CTO", "technical_leaders", 0.85),
        ("Erik", "Johansson", "Tech Lead", "technical_leaders", 0.80),
        ("Astrid", "Nielsen", "VP Engineering", "technical_leaders", 0.90),
        ("Magnus", "Lindqvist", "Head of Technology", "technical_leaders", 0.88),
        ("Ingrid", "Hansen", "Technical Director", "technical_leaders", 0.87),
        ("Olaf", "Svensson", "Engineering Manager", "technical_leaders", 0.82),
        ("Freya", "Larsen", "Software Architect", "technical_leaders", 0.84),
        ("Bjorn", "Karlsson", "Dev Lead", "technical_leaders", 0.79),

        # Procurement specialists
        ("Gunnar", "Petersen", "Procurement Manager", "procurement_specialists", 0.75),
        ("Sigrid", "Olsen", "Purchasing Director", "procurement_specialists", 0.83),
        ("Nils", "Eriksson", "Supply Chain Manager", "procurement_specialists", 0.78),
        ("Maja", "Andersson", "Sourcing Manager", "procurement_specialists", 0.76),

        # Operations leaders
        ("Tor", "Nilsson", "COO", "operations_leaders", 0.92),
        ("Liv", "Jorgensen", "Operations Manager", "operations_leaders", 0.81),
        ("Sten", "Gustafsson", "Head of Operations", "operations_leaders", 0.85),
        ("Kari", "Virtanen", "VP Operations", "operations_leaders", 0.87)
    ]

    # Generate emails for each company
    emails_created = 0
    for i, company_id in enumerate(company_ids):
        # Get company info
        cursor.execute('SELECT name, domain FROM companies WHERE id = ?', (company_id,))
        company_name, domain = cursor.fetchone()

        # Create 2-4 emails per company
        num_emails = random.randint(2, 4)
        used_templates = random.sample(email_templates, min(num_emails, len(email_templates)))

        for first_name, last_name, title, persona, confidence in used_templates:
            # Generate email variations
            email_formats = [
                f"{first_name.lower()}.{last_name.lower()}@{domain}",
                f"{first_name.lower()}{last_name.lower()[0]}@{domain}",
                f"{first_name.lower()[0]}.{last_name.lower()}@{domain}",
                f"{title.lower().replace(' ', '.')}@{domain}",
                f"{title.lower().replace(' ', '')}@{domain}"
            ]

            email = random.choice(email_formats)
            full_name = f"{first_name} {last_name}"

            # Add some randomness to confidence
            final_confidence = confidence + random.uniform(-0.1, 0.1)
            final_confidence = max(0.5, min(0.95, final_confidence))

            # Random validation status
            validation_statuses = ['valid', 'valid', 'valid', 'risky', 'invalid']
            validation_status = random.choice(validation_statuses)

            risk_score = random.randint(0, 30) if validation_status == 'valid' else random.randint(40, 80)

            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO emails
                    (email, company_id, name, title, confidence_score, source, persona_match, validation_status, risk_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (email, company_id, full_name, title, final_confidence, 'test_generation', persona, validation_status, risk_score))

                if cursor.rowcount > 0:
                    emails_created += 1

            except sqlite3.IntegrityError:
                # Email already exists, skip
                pass

    # Add some search seeds
    search_queries = [
        ("technical_leaders AND technology AND nordics contact", "technical_leaders", "technology", "nordics"),
        ("CTO OR 'Tech Lead' site:linkedin.com/company nordics", "technical_leaders", "technology", "nordics"),
        ("procurement manager technology companies norway", "procurement_specialists", "technology", "nordics"),
        ("software architect scandinavia contact", "technical_leaders", "technology", "nordics"),
        ("VP engineering nordic countries", "technical_leaders", "technology", "nordics")
    ]

    for query, persona, sector, geo in search_queries:
        cursor.execute('''
            INSERT OR IGNORE INTO search_seeds (query, persona, sector, geography)
            VALUES (?, ?, ?, ?)
        ''', (query, persona, sector, geo))

    conn.commit()
    conn.close()

    print(f"✅ Sample data created successfully!")
    print(f"📊 Created {len(companies)} companies")
    print(f"📧 Created {emails_created} unique emails")
    print(f"🔍 Created {len(search_queries)} search seeds")
    print(f"💾 Database: {db_path}")

if __name__ == "__main__":
    create_sample_data()
