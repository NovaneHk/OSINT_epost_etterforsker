import os
import sys
import logging
from datetime import datetime, timedelta
import random
from sqlalchemy import create_engine, text, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import ProgrammingError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://osint_user:secure_osint_pass@osint-db:5432/osint_db")

Base = declarative_base()

class Contact(Base):
    __tablename__ = 'contacts'
    
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    domain = Column(String, nullable=False)
    name = Column(String)
    role = Column(String)
    company = Column(String)
    status = Column(String, default='unvalidated')
    confidence_score = Column(Float, default=0.0)
    overall_score = Column(Float, default=0.0)
    persona_match = Column(String)
    source = Column(String)
    source_url = Column(String)
    extracted_at = Column(DateTime, default=datetime.now)
    validated_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class AuditLog(Base):
    __tablename__ = 'audit_log'
    
    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False)
    action = Column(String, nullable=False)
    source_url = Column(String)
    source_type = Column(String)
    legal_basis = Column(String, default='legitimate_interest')
    purpose = Column(String, default='b2b_marketing')
    timestamp = Column(DateTime, default=datetime.now)
    proof_note = Column(String)

def init_db(engine):
    """Initialize database schema"""
    logger.info("Creating database tables...")
    Base.metadata.create_all(engine)
    logger.info("Tables created successfully.")

def seed_data(session):
    """Seed database with sample data"""
    logger.info("Seeding sample data...")
    
    # Check if data already exists
    if session.query(Contact).count() > 0:
        logger.info("Data already exists. Skipping seed.")
        return

    # Sample Data Generators
    companies = [
        ("TechCorp", "techcorp.com", "Technology"),
        ("NordicSolutions", "nordicsolutions.no", "Consulting"),
        ("OceanSystems", "oceansystems.io", "Maritime"),
        ("GreenEnergy", "greenenergy.no", "Energy"),
        ("FinTech_X", "fintechx.com", "Finance")
    ]
    
    roles = ["CTO", "CEO", "VP Engineering", "Product Manager", "Head of Sales"]
    sources = ["LinkedIn", "Company Website", "Conference List", "News Article"]
    
    # Generate 50 sample contacts
    contacts = []
    for i in range(50):
        company_name, domain, sector = random.choice(companies)
        first_name = f"User{i}"
        last_name = f"Name{i}"
        email = f"{first_name.lower()}.{last_name.lower()}@{domain}"
        
        extracted_date = datetime.now() - timedelta(days=random.randint(0, 10))
        
        contact = Contact(
            email=email,
            domain=domain,
            name=f"{first_name} {last_name}",
            role=random.choice(roles),
            company=company_name,
            status=random.choice(['validated', 'unvalidated', 'contacted']),
            confidence_score=random.uniform(0.7, 0.99),
            overall_score=random.uniform(0.6, 0.95),
            persona_match="Decision Maker",
            source=random.choice(sources),
            source_url=f"https://{domain}/about",
            extracted_at=extracted_date,
            validated_at=extracted_date if random.choice([True, False]) else None
        )
        contacts.append(contact)
        
        # Add corresponding audit log
        audit = AuditLog(
            email=email,
            action="contact_discovered",
            source_url=f"https://{domain}/about",
            source_type="web_scrape",
            timestamp=extracted_date,
            proof_note=f"Found on company team page"
        )
        session.add(audit)

    session.add_all(contacts)
    
    # Add some "Export" audit logs to populate that KPI
    for i in range(5):
        audit = AuditLog(
            email="system",
            action="export",
            source_type="system",
            timestamp=datetime.now() - timedelta(days=random.randint(0, 7)),
            proof_note=f"Exported batch {i}"
        )
        session.add(audit)

    session.commit()
    logger.info(f"Successfully seeded {len(contacts)} contacts and audit logs.")

def main():
    try:
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        init_db(engine)
        seed_data(session)
        
        session.close()
        print("✅ Database setup and seeding complete!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
