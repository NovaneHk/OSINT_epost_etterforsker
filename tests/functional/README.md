# OSINT E-post Etterforsker - Comprehensive Functional Testing

Dette er det omfattende funksjonelle testing systemet for OSINT e-post etterforsker applikasjonen. Systemet tester alle kritiske aspekter av applikasjonen inkludert API endepunkter, frontend komponenter, database operasjoner, autentisering, OSINT søkefunksjonalitet og data visualisering.

## 📋 Test Suites Oversikt

### 🔴 Høy Prioritet Test Suites

#### 1. API Endpoints Testing (`test_api_endpoints.py`)
- **Beskrivelse**: Tester alle API endepunkter, autentisering, CRUD operasjoner, ytelse og sikkerhet
- **Estimert tid**: 5 minutter
- **Dekker**:
  - Health check endepunkter
  - Autentisering og autorisasjon
  - Leads CRUD operasjoner
  - Sources konfigurasjon
  - Campaigns management
  - Data eksport funksjonalitet
  - OSINT søkefunksjonalitet
  - Performance under concurrent load
  - Security vulnerability scanning (SQL injection, XSS)

#### 2. Database Operations Testing (`test_database_operations.py`)
- **Beskrivelse**: Tester PostgreSQL, MongoDB, Redis operasjoner, ytelse og data integritet
- **Estimert tid**: 3 minutter
- **Dekker**:
  - PostgreSQL CRUD operasjoner
  - MongoDB CRUD og aggregation
  - Redis cache operasjoner
  - Concurrent database testing
  - Data integritet validering
  - Backup og recovery prosedyrer

#### 3. Authentication & Authorization Testing (`test_authentication_authorization.py`)
- **Beskrivelse**: Tester bruker management, JWT tokens, RBAC og sikkerhetstiltak
- **Estimert tid**: 2 minutter
- **Dekker**:
  - Bruker registrering og validering
  - Login og token generering
  - JWT token validering og sikkerhet
  - Role-based access control (RBAC)
  - Session management
  - Passord sikkerhet og brute force beskyttelse
  - Concurrent autentisering testing

### 🟡 Medium Prioritet Test Suites

#### 4. Frontend Components Testing (`test_frontend_components.py`)
- **Beskrivelse**: Tester React komponenter, responsivitet, tilgjengelighet og bruker interaksjoner
- **Estimert tid**: 4 minutter
- **Dekker**:
  - Responsiv design på forskjellige skjermstørrelser
  - Tilgjengelighets compliance (ARIA, alt tekst)
  - Navigasjonskomponenter funksjonalitet
  - Form validering og bruker input
  - Dashboard komponenter og data visning
  - Leads management interface
  - Performance metrics for frontend
  - Error handling og edge cases

#### 5. OSINT Search Functionality Testing (`test_osint_search.py`)
- **Beskrivelse**: Tester LinkedIn, sosiale medier, domain intelligence og data korrelasjon
- **Estimert tid**: 6 minutter
- **Dekker**:
  - LinkedIn search integrasjon
  - Company website analyse og kontakt ekstraksjon
  - Email validering og verifikasjon
  - Social media platform search (Twitter, Facebook, Instagram)
  - Domain intelligence og WHOIS lookups
  - Cross-source data korrelasjon
  - Search performance under load

### 🟢 Lav Prioritet Test Suites

#### 6. Data Visualization Testing (`test_data_visualization.py`)
- **Beskrivelse**: Tester dashboard KPIs, chart rendering, real-time oppdateringer og mobile responsivitet
- **Estimert tid**: 2.5 minutter
- **Dekker**:
  - Dashboard KPI nøyaktighet mot faktiske data
  - Chart rendering og interaktivitet
  - Data filtering og visualisering oppdateringer
  - Real-time data oppdateringer
  - Mobile responsivitet for visualiseringer
  - Data eksport fra dashboards

## 🚀 Hvordan Kjøre Testene

### Forutsetninger

1. **Python Dependencies**:
```bash
pip install requests selenium webdriver-manager
pip install psycopg2-binary pymongo redis
pip install dnspython python-whois email-validator
pip install PyJWT
```

2. **Chrome Browser**: For Selenium testing
3. **Database Tilgang**: PostgreSQL, MongoDB, Redis instanser
4. **Kjørende Applikasjon**: API server på port 8000, Frontend på port 3000

### Kjøre Alle Tester

```bash
# Kjør alle test suites
python run_all_tests.py

# Kjør med custom URLs
python run_all_tests.py --api-url http://localhost:8000 --frontend-url http://localhost:3000

# Kjør spesifikke test suites
python run_all_tests.py --suites api_endpoints database_operations

# Skip slow tests
python run_all_tests.py --skip-slow

# Ikke generer rapporter
python run_all_tests.py --no-reports
```

### Kjøre Individuelle Test Suites

```bash
# API testing
python test_api_endpoints.py

# Frontend testing
python test_frontend_components.py

# Database testing
python test_database_operations.py

# Authentication testing
python test_authentication_authorization.py

# OSINT search testing
python test_osint_search.py

# Data visualization testing
python test_data_visualization.py
```

## 📊 Test Rapporter

Systemet genererer detaljerte JSON rapporter:

- **Master Rapport**: `comprehensive_test_report_YYYYMMDD_HHMMSS.json`
- **Suite Rapporter**: `{suite_name}_test_report_YYYYMMDD_HHMMSS.json`

### Rapport Innhold

- **Execution Summary**: Start/end tid, total varighet, overall success rate
- **Statistics**: Totale tester, vellykkede tester, feilede test suites
- **Suite Results**: Detaljerte resultater for hver test suite
- **Performance Metrics**: Response tider, throughput, ytelse data
- **Security Issues**: Oppdagede sikkerhetsproblemer
- **Recommendations**: Anbefalinger basert på test resultater

## 🔧 Konfigurasjon

### Environment Variables

```bash
# Database konfigurering
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=osint_db
POSTGRES_USER=osint_user
POSTGRES_PASSWORD=osint_password

MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_DB=osint_db

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Test konfigurering
API_BASE_URL=http://localhost:8000
FRONTEND_BASE_URL=http://localhost:3000
```

### Test Data

Testene bruker automatisk genererte test data:
- **Test Users**: Automatisk opprettede brukere med forskjellige roller
- **Test Leads**: Sample lead data for CRUD testing
- **Test Companies**: Kjente selskaper for OSINT testing
- **Test Domains**: Offentlige domener for intelligence testing

## 📈 Performance Benchmarks

### Ytelse Terskler

- **API Response Time**: < 2 sekunder per request
- **Database Operations**: < 1 sekund per operasjon
- **Frontend Page Load**: < 3 sekunder for DOM ready
- **Chart Rendering**: < 1 sekund for initial render
- **Search Operations**: < 10 sekunder per søk
- **Concurrent Load**: > 95% success rate med 10 samtidige requests

### Success Rate Kriterier

- **Excellent**: ≥ 95% success rate
- **Good**: 85-94% success rate
- **Moderate**: 70-84% success rate
- **Poor**: < 70% success rate

## 🔍 Feilsøking

### Vanlige Problemer

1. **Chrome Driver Issues**:
   - Installer ChromeDriver: `pip install webdriver-manager`
   - Sjekk Chrome versjon kompatibilitet

2. **Database Connection Failures**:
   - Verifiser database instanser kjører
   - Sjekk connection strings og credentials

3. **API Connection Issues**:
   - Verifiser API server kjører på spesifisert port
   - Sjekk firewall og nettverks konfigurering

4. **Timeout Errors**:
   - Øk timeout verdier for langsomme miljøer
   - Sjekk system ressurser og performance

### Debug Mode

Kjør tester med verbose output:
```bash
python -v test_api_endpoints.py
```

## 🛡️ Sikkerhet

### Security Testing

Systemet inkluderer omfattende sikkerhetstesting:
- **SQL Injection** attempts
- **XSS** payload testing
- **Authentication** bypass attempts
- **Authorization** privilege escalation testing
- **Brute Force** protection validation
- **Data Validation** og input sanitization

### Sensitive Data

- Test credentials er hardkodet og kun for testing
- Ingen produksjonsdata brukes i testene
- Automatisk cleanup av test data

## 📞 Support

For spørsmål eller problemer med testing systemet:
- Sjekk denne README filen først
- Review test rapport for detaljerte feilmeldinger
- Kjør individuelle test suites for isolering av problemer
- Sjekk logs for applikasjon og database instanser

## 🔄 Vedlikehold

### Oppdatering av Tester

- Legg til nye test cases når nye features implementeres
- Oppdater performance benchmarks basert på system kapasitet
- Review og oppdater sikkerhetstester regelmessig
- Maintainer test data og cleanup rutiner

### Kontinuerlig Forbedring

- Monitor test execution tider
- Review failed test patterns
- Optimize test coverage
- Update dependencies regelmessig