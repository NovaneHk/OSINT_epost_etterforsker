# Production Deployment Guide

This directory contains all the necessary files and configurations for deploying the OSINT B2B Email System in production.

## Quick Start

1. **Clone the repository and navigate to the project root**
   ```bash
   git clone <repository-url>
   cd OSINT_epost_etterforsker
   ```

2. **Configure environment variables**
   ```bash
   cp deploy/.env.production deploy/.env
   # Edit deploy/.env with your actual production values
   ```

3. **Deploy with Docker Compose**
   ```bash
   cd deploy
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. **Verify deployment**
   ```bash
   docker-compose -f docker-compose.prod.yml ps
   curl http://localhost/health
   ```

## File Overview

### Core Deployment Files

- **`docker-compose.prod.yml`** - Complete production stack with PostgreSQL, Redis, Nginx
- **`Dockerfile`** - Multi-stage Docker build configuration
- **`production.yml`** - Production-specific application configuration
- **`.env.production`** - Environment variables template
- **`start.sh`** - Production startup script with health checks
- **`health_check.py`** - Application health monitoring script

### Configuration Files

- **`nginx.conf`** - Nginx reverse proxy configuration (create if needed)
- **`prometheus.yml`** - Prometheus monitoring configuration (optional)
- **`logstash.conf`** - Log aggregation configuration (optional)

## Prerequisites

### System Requirements

- **OS**: Linux (Ubuntu 20.04+ recommended)
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Memory**: 4GB+ RAM
- **Storage**: 20GB+ available space
- **Network**: Internet access for web scraping

### Required Environment Variables

Critical variables that MUST be set:

```bash
SECRET_KEY=your-super-secret-key-change-this
DB_PASSWORD=your-secure-database-password
REDIS_PASSWORD=your-secure-redis-password
PRODUCTION_DOMAIN=your-domain.com
```

## Deployment Steps

### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create application user
sudo useradd -m -s /bin/bash osint
sudo usermod -aG docker osint
```

### 2. Application Deployment

```bash
# Switch to application user
sudo su - osint

# Clone repository
git clone <repository-url> osint-b2b
cd osint-b2b

# Configure environment
cp deploy/.env.production deploy/.env
nano deploy/.env  # Edit with your values

# Deploy application
cd deploy
docker-compose -f docker-compose.prod.yml up -d
```

### 3. SSL Configuration (Recommended)

```bash
# Install Certbot for Let's Encrypt
sudo apt install certbot

# Generate SSL certificate
sudo certbot certonly --standalone -d your-domain.com

# Copy certificates to deployment directory
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem deploy/ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem deploy/ssl/key.pem
sudo chown osint:osint deploy/ssl/*

# Restart nginx to load SSL
docker-compose -f docker-compose.prod.yml restart nginx
```

## Monitoring and Maintenance

### Health Checks

The system includes comprehensive health monitoring:

```bash
# Check application health
curl http://localhost/health

# Check individual service health
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs app

# Run manual health check
docker exec osint-app python health_check.py
```

### Log Management

Application logs are available in multiple locations:

```bash
# Application logs
docker-compose -f docker-compose.prod.yml logs -f app

# Database logs
docker-compose -f docker-compose.prod.yml logs -f postgres

# Nginx access logs
docker exec osint-nginx tail -f /var/log/nginx/access.log
```

### Database Backup

```bash
# Manual backup
docker exec osint-postgres pg_dump -U osint_user osint_b2b > backup_$(date +%Y%m%d).sql

# Automated backup (runs daily)
docker-compose -f docker-compose.prod.yml --profile backup up -d backup
```

### Performance Monitoring

Optional monitoring stack (Prometheus + Grafana):

```bash
# Deploy monitoring stack
docker-compose -f docker-compose.prod.yml --profile monitoring up -d

# Access Grafana dashboard
# http://localhost:3000 (admin/admin)
```

## Scaling and Performance

### Horizontal Scaling

Scale application instances:

```bash
# Scale to 3 application instances
docker-compose -f docker-compose.prod.yml up -d --scale app=3
```

### Resource Optimization

Monitor and adjust resource limits in `docker-compose.prod.yml`:

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
```

### Database Performance

Optimize PostgreSQL settings:

```bash
# Edit PostgreSQL configuration
docker exec -it osint-postgres psql -U osint_user -d osint_b2b
# Run ANALYZE and optimization queries
```

## Security Considerations

### Network Security

- Use firewall to restrict access to necessary ports only
- Configure rate limiting in nginx
- Enable SSL/TLS encryption
- Use strong passwords and secrets

### Data Security

- Enable database encryption at rest
- Regular security updates
- Audit logging enabled
- GDPR compliance features active

### Access Control

```bash
# Create nginx basic auth (optional)
sudo apt install apache2-utils
htpasswd -c deploy/.htpasswd admin

# Add to nginx configuration:
# auth_basic "Restricted Content";
# auth_basic_user_file /etc/nginx/.htpasswd;
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check database status
   docker-compose -f docker-compose.prod.yml logs postgres

   # Reset database
   docker-compose -f docker-compose.prod.yml down -v
   docker-compose -f docker-compose.prod.yml up -d
   ```

2. **High Memory Usage**
   ```bash
   # Check resource usage
   docker stats

   # Restart services
   docker-compose -f docker-compose.prod.yml restart
   ```

3. **Web Scraping Issues**
   ```bash
   # Check network connectivity
   docker exec osint-app curl -I https://httpbin.org/status/200

   # Review rate limiting logs
   docker-compose -f docker-compose.prod.yml logs app | grep -i rate
   ```

### Log Analysis

```bash
# Application errors
docker-compose -f docker-compose.prod.yml logs app | grep -i error

# Performance metrics
docker-compose -f docker-compose.prod.yml logs app | grep -i "processing time"

# Security events
docker-compose -f docker-compose.prod.yml logs nginx | grep -E "(40[0-9]|50[0-9])"
```

## Backup and Recovery

### Automated Backups

The system includes automated backup capabilities:

```bash
# Configure backup environment variables
export BACKUP_BUCKET=your-s3-bucket
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key

# Run backup service
docker-compose -f docker-compose.prod.yml --profile backup up -d
```

### Manual Recovery

```bash
# Stop application
docker-compose -f docker-compose.prod.yml down

# Restore database
docker run --rm -v postgres_data:/var/lib/postgresql/data postgres:15-alpine \
  psql -U osint_user -d osint_b2b < backup.sql

# Restart application
docker-compose -f docker-compose.prod.yml up -d
```

## Updates and Maintenance

### Application Updates

```bash
# Pull latest code
git pull origin main

# Rebuild and deploy
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

### System Maintenance

```bash
# Clean up old containers and images
docker system prune -f

# Update base images
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

## Support and Documentation

- **Application Documentation**: `../OSINT_B2B_Email_System_Documentation.md`
- **API Documentation**: Available at `/docs` when application is running
- **Configuration Reference**: `production.yml`
- **Troubleshooting**: Check logs and health endpoints

For issues and support, check the application logs and health status first, then consult the main documentation.