#!/bin/bash

# SSL Certificate Setup Script for CRE Studio Backend
# This script sets up SSL certificates using Let's Encrypt

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="cre_studio_backend"
DOMAIN_NAME="yourdomain.com"
EMAIL="your-email@example.com"

echo -e "${GREEN}Starting SSL certificate setup...${NC}"

# Check if domain is provided
if [ "$1" ]; then
    DOMAIN_NAME=$1
    echo -e "${YELLOW}Using domain: $DOMAIN_NAME${NC}"
else
    echo -e "${RED}Please provide a domain name as the first argument${NC}"
    echo "Usage: ./ssl_setup.sh yourdomain.com"
    exit 1
fi

# Check if email is provided
if [ "$2" ]; then
    EMAIL=$2
    echo -e "${YELLOW}Using email: $EMAIL${NC}"
else
    echo -e "${RED}Please provide an email address as the second argument${NC}"
    echo "Usage: ./ssl_setup.sh yourdomain.com your-email@example.com"
    exit 1
fi

# Update Nginx configuration with actual domain
echo -e "${YELLOW}Updating Nginx configuration with domain...${NC}"
sudo sed -i "s/yourdomain.com/$DOMAIN_NAME/g" /etc/nginx/sites-available/$PROJECT_NAME

# Test Nginx configuration
echo -e "${YELLOW}Testing Nginx configuration...${NC}"
sudo nginx -t

# Restart Nginx
echo -e "${YELLOW}Restarting Nginx...${NC}"
sudo systemctl restart nginx

# Install SSL certificate
echo -e "${YELLOW}Installing SSL certificate...${NC}"
sudo certbot --nginx -d $DOMAIN_NAME -d www.$DOMAIN_NAME --email $EMAIL --agree-tos --non-interactive

# Setup automatic renewal
echo -e "${YELLOW}Setting up automatic certificate renewal...${NC}"
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# Test certificate renewal
echo -e "${YELLOW}Testing certificate renewal...${NC}"
sudo certbot renew --dry-run

# Update environment file with HTTPS URLs
echo -e "${YELLOW}Updating environment file with HTTPS URLs...${NC}"
PROJECT_DIR="/var/www/$PROJECT_NAME"
sudo sed -i "s|APP_URL=.*|APP_URL=https://$DOMAIN_NAME/|g" $PROJECT_DIR/.env
sudo sed -i "s|FRONTEND_URL=.*|FRONTEND_URL=https://$DOMAIN_NAME|g" $PROJECT_DIR/.env
sudo sed -i "s|GOOGLE_REDIRECT_URI=.*|GOOGLE_REDIRECT_URI=https://$DOMAIN_NAME/api/oauth-callback|g" $PROJECT_DIR/.env

# Restart Django application to pick up new environment variables
echo -e "${YELLOW}Restarting Django application...${NC}"
sudo systemctl restart django

# Setup log rotation for SSL certificates
echo -e "${YELLOW}Setting up log rotation...${NC}"
sudo tee /etc/logrotate.d/certbot > /dev/null <<EOF
/var/log/letsencrypt/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 root root
}
EOF

# Test SSL configuration
echo -e "${YELLOW}Testing SSL configuration...${NC}"
echo "Testing SSL certificate..."
curl -I https://$DOMAIN_NAME

echo -e "${GREEN}SSL certificate setup completed successfully!${NC}"
echo -e "${YELLOW}Your application is now available at: https://$DOMAIN_NAME${NC}"
echo -e "${YELLOW}Certificate will auto-renew every 90 days${NC}"

# Display certificate information
echo -e "${YELLOW}Certificate information:${NC}"
sudo certbot certificates
