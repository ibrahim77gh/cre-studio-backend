#!/bin/bash

# Deployment script for updates
# This script handles code updates and service restarts

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="cre_studio_backend"
PROJECT_DIR="/var/www/$PROJECT_NAME"

echo -e "${GREEN}Starting deployment update...${NC}"

# Navigate to project directory
cd $PROJECT_DIR

# Activate virtual environment
source venv/bin/activate

# Pull latest changes from private repository
echo -e "${YELLOW}Pulling latest changes...${NC}"
git pull origin main

# Install/update dependencies
echo -e "${YELLOW}Installing/updating dependencies...${NC}"
pip install -r requirements.txt

# Run database migrations
echo -e "${YELLOW}Running database migrations...${NC}"
export DEBUG=False
python manage.py migrate

# Collect static files
echo -e "${YELLOW}Collecting static files...${NC}"
python manage.py collectstatic --noinput

# Clear cache (if using Redis for caching)
echo -e "${YELLOW}Clearing cache...${NC}"
python manage.py shell -c "from django.core.cache import cache; cache.clear()"

# Restart services
echo -e "${YELLOW}Restarting services...${NC}"
sudo systemctl restart django
sudo systemctl restart celery
sudo systemctl restart celerybeat
sudo systemctl reload nginx

# Check service status
echo -e "${YELLOW}Checking service status...${NC}"
sudo systemctl status django --no-pager
sudo systemctl status celery --no-pager
sudo systemctl status celerybeat --no-pager

echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${YELLOW}All services have been restarted and are running${NC}"
