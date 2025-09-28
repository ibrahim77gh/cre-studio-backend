#!/bin/bash

# CRE Studio Backend Deployment Script
# This script sets up the production environment on Ubuntu server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="cre-studio-backend"
PROJECT_DIR="/var/www/$PROJECT_NAME"
DOMAIN_NAME="yourdomain.com"
DB_NAME="cre_studio_db"
DB_USER="cre_studio_user"
DB_PASSWORD=$(openssl rand -base64 32)

echo -e "${GREEN}Starting CRE Studio Backend deployment...${NC}"

# Update system packages
echo -e "${YELLOW}Updating system packages...${NC}"
sudo apt update && sudo apt upgrade -y

# Install required system packages
echo -e "${YELLOW}Installing system packages...${NC}"
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    postgresql \
    postgresql-contrib \
    nginx \
    redis-server \
    git \
    curl \
    wget \
    unzip \
    software-properties-common \
    certbot \
    python3-certbot-nginx \
    supervisor \
    htop \
    ufw \
    fail2ban

# Create project directory
echo -e "${YELLOW}Creating project directory...${NC}"
sudo mkdir -p $PROJECT_DIR
sudo chown -R $USER:$USER $PROJECT_DIR

# Project files already cloned
echo -e "${YELLOW}Project files found at $PROJECT_DIR${NC}"
echo -e "${YELLOW}Proceeding with setup...${NC}"

# Verify the project directory exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}Project directory not found at $PROJECT_DIR${NC}"
    echo -e "${YELLOW}Please clone the repository first:${NC}"
    echo -e "${YELLOW}git clone git@github.com:ibrahim77gh/cre-studio-backend.git $PROJECT_DIR${NC}"
    exit 1
fi

# Create virtual environment
echo -e "${YELLOW}Creating virtual environment...${NC}"
cd $PROJECT_DIR
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psycopg2-binary whitenoise

# Setup PostgreSQL database
echo -e "${YELLOW}Setting up PostgreSQL database...${NC}"
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;"
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
sudo -u postgres psql -c "ALTER USER $DB_USER CREATEDB;"

# Create environment file
echo -e "${YELLOW}Creating environment file...${NC}"
cat > $PROJECT_DIR/.env << EOF
DEBUG=False
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DATABASE_NAME=$DB_NAME
DATABASE_USER=$DB_USER
DATABASE_PASSWORD=$DB_PASSWORD
DATABASE_HOST=localhost
DATABASE_PORT=5432
REDIS_URL=redis://localhost:6379/0
APP_URL=https://$DOMAIN_NAME/
FRONTEND_URL=https://$DOMAIN_NAME
GOOGLE_REDIRECT_URI=https://$DOMAIN_NAME/api/oauth-callback
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
DOMAIN_NAME=$DOMAIN_NAME
EOF

# Set proper permissions
sudo chown -R www-data:www-data $PROJECT_DIR
sudo chmod -R 755 $PROJECT_DIR

# Create log directories
echo -e "${YELLOW}Creating log directories...${NC}"
sudo mkdir -p /var/log/django
sudo mkdir -p /var/log/gunicorn
sudo mkdir -p /var/log/celery
sudo chown -R www-data:www-data /var/log/django
sudo chown -R www-data:www-data /var/log/gunicorn
sudo chown -R www-data:www-data /var/log/celery

# Run Django migrations
echo -e "${YELLOW}Running Django migrations...${NC}"
cd $PROJECT_DIR
source venv/bin/activate
export DEBUG=False
python manage.py collectstatic --noinput
python manage.py migrate

# Copy systemd service files
echo -e "${YELLOW}Setting up systemd services...${NC}"
sudo cp $PROJECT_DIR/deployment/django.service /etc/systemd/system/
sudo cp $PROJECT_DIR/deployment/celery.service /etc/systemd/system/
sudo cp $PROJECT_DIR/deployment/celerybeat.service /etc/systemd/system/

# Reload systemd and enable services
sudo systemctl daemon-reload
sudo systemctl enable django
sudo systemctl enable celery
sudo systemctl enable celerybeat
sudo systemctl enable redis-server

# Configure Nginx
echo -e "${YELLOW}Configuring Nginx...${NC}"
sudo cp $PROJECT_DIR/deployment/nginx.conf /etc/nginx/sites-available/$PROJECT_NAME
sudo ln -sf /etc/nginx/sites-available/$PROJECT_NAME /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# Configure firewall
echo -e "${YELLOW}Configuring firewall...${NC}"
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw --force enable

# Start services
echo -e "${YELLOW}Starting services...${NC}"
sudo systemctl start redis-server
sudo systemctl start django
sudo systemctl start celery
sudo systemctl start celerybeat
sudo systemctl restart nginx

# Setup SSL certificate (will be done separately)
echo -e "${YELLOW}SSL certificate setup will be done in the next step...${NC}"

echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Update the .env file with your actual values"
echo "2. Run the SSL certificate setup script"
echo "3. Update your domain DNS to point to this server"
echo "4. Test your application"

echo -e "${GREEN}Database credentials saved to .env file${NC}"
echo -e "${GREEN}Services are running and enabled${NC}"
