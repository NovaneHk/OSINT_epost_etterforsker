# Deployment Guide

## Innholdsfortegnelse
1. [Forutsetninger](#forutsetninger)
2. [Lokal Utvikling](#lokal-utvikling)
3. [Staging Miljø](#staging-miljø)
4. [Produksjonsmiljø](#produksjonsmiljø)
5. [Backup og Vedlikehold](#backup-og-vedlikehold)
6. [Monitoring](#monitoring)
7. [Feilsøking](#feilsøking)

## Forutsetninger

### Systemkrav
- Docker og Docker Compose
- AWS CLI
- Node.js 18+
- Python 3.12+
- PostgreSQL 14
- Redis

### AWS Oppsett
1. Opprett ECR repositories:
```bash
aws ecr create-repository --repository-name osint-backend
aws ecr create-repository --repository-name osint-frontend
```

2. Opprett ECS cluster:
```bash
aws ecs create-cluster --cluster-name osint-cluster
```

3. Konfigurer IAM roller og policies

## Lokal Utvikling

1. Klon repositoriet:
```bash
git clone https://github.com/NovaneHk/OSINT_epost_etterforsker.git
cd OSINT_epost_etterforsker
```

2. Installer dependencies:
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # eller .\venv\Scripts\activate på Windows
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

3. Start utviklingsmiljø:
```bash
docker-compose up --build
```

## Staging Miljø

1. Opprett .env.staging:
```bash
cp .env.example .env.staging
# Rediger miljøvariabler for staging
```

2. Deploy til staging:
```bash
docker-compose -f docker-compose.staging.yml up -d
```

## Produksjonsmiljø

### Initial Setup

1. Konfigurer miljøvariabler:
```bash
cp .env.example .env.production
# Rediger miljøvariabler for produksjon
```

2. Build og push Docker images:
```bash
# Login til ECR
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin $ECR_REGISTRY

# Build og push
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml push
```

3. Deploy til ECS:
```bash
aws ecs update-service --cluster osint-cluster --service backend-service --force-new-deployment
aws ecs update-service --cluster osint-cluster --service frontend-service --force-new-deployment
```

### SSL/TLS Konfigurasjon

1. Generer sertifikater:
```bash
certbot certonly --dns-route53 -d api.yourdomain.com
certbot certonly --dns-route53 -d app.yourdomain.com
```

2. Konfigurer Nginx:
```nginx
server {
    listen 443 ssl;
    server_name api.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    
    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Backup og Vedlikehold

### Database Backup

1. Automatiske backups:
```bash
# Kjør backup script
./database/backup-restore.sh

# Legg til i crontab
0 2 * * * /path/to/backup-restore.sh
```

2. Manuell backup:
```bash
docker exec osint-db pg_dump -U postgres osint_db > backup.sql
```

### System Vedlikehold

1. Logg rotasjon:
```bash
# Konfigurer logrotate
/var/log/osint/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data www-data
}
```

2. Disk cleanup:
```bash
# Rydd gamle backups
find /backups -type f -mtime +30 -delete

# Rydd Docker
docker system prune -af --volumes
```

## Monitoring

### Prometheus/Grafana Setup

1. Konfigurer Prometheus targets:
```yaml
scrape_configs:
  - job_name: 'backend'
    static_configs:
      - targets: ['backend:8000']
```

2. Import Grafana dashboards:
- System metrics dashboard
- API performance dashboard
- Business metrics dashboard

### Alerts

1. Konfigurer alerting rules:
```yaml
groups:
  - name: osint
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
```

2. Sett opp alert notifications:
- Email
- Slack
- PagerDuty

## Feilsøking

### Vanlige Problemer

1. Database tilkoblingsfeil:
```bash
# Sjekk database status
docker-compose ps db
docker-compose logs db

# Verifiser tilkobling
psql -h localhost -U postgres -d osint_db
```

2. Redis problemer:
```bash
# Test Redis tilkobling
redis-cli ping
redis-cli monitor
```

3. Container issues:
```bash
# Sjekk container status
docker-compose ps
docker-compose logs --tail=100 service_name

# Restart services
docker-compose restart service_name
```

### Performance Troubleshooting

1. API performance:
```bash
# Sjekk API response tider
curl -w "@curl-format.txt" -o /dev/null -s "http://localhost:8000/api/health"
```

2. Database performance:
```sql
-- Sjekk slow queries
SELECT * FROM pg_stat_activity WHERE state = 'active';
```

3. Memory issues:
```bash
# Sjekk memory usage
docker stats
```

### Security Issues

1. Sjekk access logs:
```bash
tail -f /var/log/nginx/access.log | grep 404
```

2. Audit autentisering:
```bash
grep "Failed login" /var/log/auth.log
```

3. Sjekk SSL/TLS:
```bash
openssl s_client -connect api.yourdomain.com:443 -tls1_2
```