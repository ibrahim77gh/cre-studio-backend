#!/bin/bash

# Monitoring script for CRE Studio Backend
# This script provides system and application monitoring

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== CRE Studio Backend System Monitor ===${NC}"
echo

# System information
echo -e "${YELLOW}System Information:${NC}"
echo "Hostname: $(hostname)"
echo "Uptime: $(uptime -p)"
echo "Load Average: $(cat /proc/loadavg | awk '{print $1, $2, $3}')"
echo "Memory Usage: $(free -h | grep '^Mem:' | awk '{print $3 "/" $2 " (" $3/$2*100 "%)"}')"
echo "Disk Usage: $(df -h / | tail -1 | awk '{print $3 "/" $2 " (" $5 ")"}')"
echo

# Service status
echo -e "${YELLOW}Service Status:${NC}"
services=("nginx" "postgresql" "redis-server" "django" "celery" "celerybeat")
for service in "${services[@]}"; do
    if systemctl is-active --quiet $service; then
        echo -e "$service: ${GREEN}Running${NC}"
    else
        echo -e "$service: ${RED}Stopped${NC}"
    fi
done
echo

# Application health check
echo -e "${YELLOW}Application Health Check:${NC}"
if curl -s -f http://localhost/health/ > /dev/null; then
    echo -e "Django App: ${GREEN}Healthy${NC}"
else
    echo -e "Django App: ${RED}Unhealthy${NC}"
fi

# Database connection
echo -e "${YELLOW}Database Status:${NC}"
PROJECT_DIR="/var/www/cre-studio-backend"
cd $PROJECT_DIR
source venv/bin/activate
export DEBUG=False
if python manage.py check --database default > /dev/null 2>&1; then
    echo -e "Database: ${GREEN}Connected${NC}"
else
    echo -e "Database: ${RED}Connection Failed${NC}"
fi

# Redis connection
echo -e "${YELLOW}Redis Status:${NC}"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "Redis: ${GREEN}Connected${NC}"
else
    echo -e "Redis: ${RED}Connection Failed${NC}"
fi

# Log file sizes
echo -e "${YELLOW}Log File Sizes:${NC}"
if [ -f "/var/log/django/cre_studio_backend.log" ]; then
    echo "Django Log: $(du -h /var/log/django/cre_studio_backend.log | cut -f1)"
fi
if [ -f "/var/log/gunicorn/error.log" ]; then
    echo "Gunicorn Error Log: $(du -h /var/log/gunicorn/error.log | cut -f1)"
fi
if [ -f "/var/log/gunicorn/access.log" ]; then
    echo "Gunicorn Access Log: $(du -h /var/log/gunicorn/access.log | cut -f1)"
fi

# Recent errors
echo -e "${YELLOW}Recent Errors (last 10):${NC}"
if [ -f "/var/log/django/cre_studio_backend.log" ]; then
    grep -i error /var/log/django/cre_studio_backend.log | tail -10
fi

echo
echo -e "${BLUE}=== End of System Monitor ===${NC}"
