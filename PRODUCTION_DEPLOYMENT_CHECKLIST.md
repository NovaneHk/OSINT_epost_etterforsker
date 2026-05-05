# Production Readiness Checklist

## ✅ Kritiske Fikser Implementert

### Frontend
- [x] TypeScript type-feil fikset
- [x] "use client" direktiver lagt til for React hooks
- [x] Date-fns locale-import fikset
- [x] API type-definisjoner oppdatert
- [x] Deprecated baseUrl warning fikset

### Backend  
- [x] Database migrations klar
- [x] Production config manager implementert
- [x] GDPR compliance konfigurert
- [x] Security settings validert

## ⚠️ Gjenstående Utfordringer

### 1. Environment Variables (KRITISK)
**Problem**: Manglende produksjonsmiljøvariabler
**Løsning**: Opprett `.env.production`:

```bash
# Security
SECRET_KEY=<generert-sikker-nøkkel-her>
JWT_SECRET_KEY=<generert-jwt-nøkkel-her>

# Database
DATABASE_URL=postgresql://osint_user:<password>@localhost:5432/osint_db
DB_HOST=localhost
DB_PASSWORD=<secure-password>

# API
API_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws

# CORS
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
PRODUCTION_DOMAIN=yourdomain.com

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=<secure-password>

# GDPR
GDPR_REQUIRE_CONSENT=true
GDPR_RETENTION_DAYS=365

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=60

# Environment
ENVIRONMENT=production
DEBUG=false
```

### 2. Database Setup (KRITISK)
**Problem**: PostgreSQL må konfigureres for produksjon
**Løsning**:

```bash
# Kjør database setup script
psql -U postgres -f database/postgresql-setup.sql

# Kjør migrations
cd backend
alembic upgrade head
```

### 3. DNS Resolver Dependency (MIDDELS)
**Problem**: `dns.resolver` mangler i Python environment
**Løsning**:

```bash
pip install dnspython
```

### 4. API Method Registrering (HØY)
**Problem**: Investigation API metoder ikke registrert i hovedAPI
**Løsning**: Se frontend/src/lib/investigations-api.ts

### 5. Security Tokens (KRITISK)
**Problem**: Default secrets må endres
**Generering**:

```bash
# Generer SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generer JWT_SECRET_KEY  
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 6. CORS Configuration (HØY)
**Problem**: CORS må konfigureres for produksjonsdomenet
**Løsning**: Oppdater backend/core/config.py med riktig domene

### 7. Rate Limiting (MIDDELS)
**Problem**: API rate limiting må aktiveres
**Status**: Konfigurert i settings men må testes

### 8. Logging (MIDDELS)
**Problem**: Production logging må konfigureres
**Løsning**: Bruk logging.conf og roter logs

### 9. Backup Strategy (HØY)
**Problem**: Ingen automatisk backup
**Løsning**: Implementer database/backup-restore.sh som cron job

### 10. Monitoring (MIDDELS)
**Problem**: Ingen helsesjekk-endpoint monitoring
**Løsning**: Sett opp ekstern overvåking av /health endpoint

## 🔧 Pre-Deployment Kommandoer

### 1. Installer Dependencies
```bash
# Python backend
pip install -r requirements.txt
pip install dnspython  # For DNS validation

# Frontend
cd frontend
npm install --production
```

### 2. Build Frontend
```bash
cd frontend
npm run build
```

### 3. Database Setup
```bash
# Opprett database
psql -U postgres -c "CREATE DATABASE osint_db;"

# Kjør setup script
psql -U postgres -d osint_db -f database/postgresql-setup.sql

# Kjør migrations
cd backend
alembic upgrade head
```

### 4. Test Configuration
```bash
# Valider production config
python -c "from core.production_config import production_config; production_config.validate_config()"

# Test database connection
python -c "from core.database import DatabaseManager; db = DatabaseManager(); print(db.get_contact_stats())"
```

### 5. Security Checks
```bash
# Sjekk at secrets er endret
python -c "from backend.core.config import get_settings; s = get_settings(); assert s.SECRET_KEY != 'your-secret-key-change-in-production'"

# Valider HTTPS (i produksjon)
# curl https://yourdomain.com/health
```

## 🚀 Deployment Sequence

1. **Pre-deployment**:
   - Sett alle environment variables
   - Generer nye security tokens
   - Konfigurer database

2. **Deployment**:
   ```bash
   # Start backend
   cd backend
   uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
   
   # Start frontend (separat terminal)
   cd frontend
   npm run start
   ```

3. **Post-deployment**:
   - Verifiser health check: `curl http://localhost:8000/health`
   - Sjekk frontend: `curl http://localhost:3000`
   - Test WebSocket connections
   - Verifiser GDPR compliance endpoints

## 📊 Monitoring Checklist

- [ ] Sett opp log rotation
- [ ] Konfigurer error tracking (f.eks. Sentry)
- [ ] Overvåk database ytelse
- [ ] Sett opp uptime monitoring
- [ ] Konfigurer backup alerts
- [ ] Sjekk disk space regularly

## 🔒 Security Checklist

- [ ] Alle default passwords endret
- [ ] HTTPS aktivert (med gyldig sertifikat)
- [ ] CORS konfigurert for spesifikke domener
- [ ] Rate limiting aktivert
- [ ] SQL injection beskyttelse testet
- [ ] XSS beskyttelse testet
- [ ] CSRF tokens implementert
- [ ] Audit logging aktivert

## 🎯 Performance Checklist

- [ ] Database indexer optimalisert
- [ ] API response caching konfigurert
- [ ] Frontend assets minifisert
- [ ] Gzip compression aktivert
- [ ] CDN vurdert for statiske filer
- [ ] Connection pooling konfigurert

## 📝 Compliance Checklist

- [ ] GDPR consent mekanisme implementert
- [ ] Data retention policy konfigurert
- [ ] Privacy policy tilgjengelig
- [ ] Data subject rights implementert
- [ ] Audit trail aktivert
- [ ] Data encryption at rest aktivert

## ✅ Ready for Production Criteria

Systemet er klart for livekjøring når:

1. Alle KRITISKE fikser er implementert
2. Environment variables er satt
3. Database er konfigurert og testet
4. Security tokens er generert og unike
5. Health checks returnerer "healthy"
6. Frontend bygger uten feil
7. Backend starter uten feil
8. GDPR compliance er verifisert
9. Backup strategi er på plass
10. Monitoring er konfigurert

## 🆘 Troubleshooting

### Frontend ikke tilgjengelig
```bash
# Sjekk Next.js server
cd frontend
npm run build
npm start

# Sjekk logs
tail -f frontend/.next/server/error.log
```

### Backend API feil
```bash
# Sjekk uvicorn logs
journalctl -u osint-backend -f

# Test health endpoint
curl http://localhost:8000/health
```

### Database connection feil
```bash
# Test PostgreSQL connection
psql -U osint_user -d osint_db -c "SELECT 1;"

# Sjekk database status
systemctl status postgresql
```

### WebSocket connection feil
```bash
# Test WebSocket endpoint
wscat -c ws://localhost:8000/ws/notifications

# Sjekk CORS settings
curl -H "Origin: http://localhost:3000" http://localhost:8000/health -v
```

---

**Sist oppdatert**: 2025-11-17
**Versjon**: 1.0
**Status**: Klar for pre-production testing
