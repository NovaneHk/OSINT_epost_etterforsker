#!/usr/bin/env python3
"""
Quick script to check database schema
"""

import sqlite3

def check_schema():
    conn = sqlite3.connect('data/osint_cache.db')
    cursor = conn.cursor()

    print("=== COMPANIES TABLE SCHEMA ===")
    cursor.execute("PRAGMA table_info(companies)")
    companies_columns = cursor.fetchall()
    for col in companies_columns:
        print(f"  {col[1]} ({col[2]})")

    print("\n=== EMAILS TABLE SCHEMA ===")
    cursor.execute("PRAGMA table_info(emails)")
    emails_columns = cursor.fetchall()
    for col in emails_columns:
        print(f"  {col[1]} ({col[2]})")

    print("\n=== SAMPLE DATA ===")
    cursor.execute("SELECT * FROM companies LIMIT 1")
    company = cursor.fetchone()
    if company:
        print("Sample company:", company)

    cursor.execute("SELECT * FROM emails LIMIT 1")
    email = cursor.fetchone()
    if email:
        print("Sample email:", email)

    conn.close()

if __name__ == "__main__":
    check_schema()
