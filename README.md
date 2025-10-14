# CRE Studio Backend

A comprehensive Django REST API backend for Commercial Real Estate (CRE) studio management, featuring property management, marketing campaign creation with AI-powered content generation, user authentication, and real-time collaboration tools.

## 🌟 Features

### Core Functionality
- **User Authentication & Authorization**
  - JWT-based authentication with refresh tokens
  - Email verification and password reset
  - Google OAuth integration
  - Role-based permissions (Admin, Manager, Viewer)
  - Custom user profiles with avatar support

- **Property Management**
  - CRUD operations for commercial properties
  - Property image galleries
  - Property search and filtering
  - Custom property attributes

- **Marketing Campaign Management**
  - AI-powered campaign content generation using OpenAI
  - Google Ads integration (headlines, descriptions)
  - Campaign budget tracking (daily, weekly, monthly, quarterly, annual)
  - Campaign asset management
  - Real-time campaign status tracking
  - Background task processing for AI content generation

- **Collaboration & Communication**
  - Threaded comment system for campaigns
  - File attachments in comments
  - Email notifications for comments and replies
  - Campaign update notifications
  - Real-time collaboration features

- **Background Task Processing**
  - Celery-based asynchronous task queue
  - Redis message broker
  - Scheduled tasks with Celery Beat
  - AI content generation in background
  - Email sending via tasks

## 🛠 Technology Stack

### Backend Framework
- **Django 5.2.5** - High-level Python web framework
- **Django REST Framework 3.16.1** - Powerful toolkit for building Web APIs
- **Djoser 2.3.3** - REST implementation of Django authentication

### Authentication & Security
- **Simple JWT 5.5.1** - JSON Web Token authentication
- **Django CORS Headers 4.7.0** - Cross-Origin Resource Sharing support
- **Cryptography 45.0.6** - Cryptographic recipes and primitives

### AI & Integrations
- **OpenAI 1.108.1** - GPT-powered content generation
- **Google OAuth** - Social authentication

### Task Queue & Caching
- **Celery 5.3.4** - Distributed task queue
- **Redis 5.0.1** - In-memory data structure store

### Database
- **SQLite** (Development) - Lightweight database
- **PostgreSQL** (Production) - Production-grade database

### Additional Tools
- **Pillow 11.3.0** - Image processing
- **Python-dotenv 1.1.1** - Environment variable management
- **Pydantic 2.9.2** - Data validation

## 📋 Prerequisites

- Python 3.10 or higher
- Redis server
- PostgreSQL (for production)
- Git
- Virtual environment (recommended)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd cre_studio_backend
```

### 2. Set Up Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file in the project root:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True

# Database (Production)
DATABASE_NAME=cre_studio_db
DATABASE_USER=cre_studio_user
DATABASE_PASSWORD=your-db-password
DATABASE_HOST=localhost
DATABASE_PORT=5432

# Email Configuration
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/api/oauth-callback

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Redis
REDIS_URL=redis://localhost:6379/0

# Site Configuration
SITE_URL=http://localhost:3000/
DOMAIN_NAME=localhost
APP_URL=http://localhost:3000/
FRONTEND_URL=http://localhost:3000
```

### 5. Database Setup

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# (Optional) Load sample data
python manage.py loaddata initial_data.json
```

### 6. Install and Start Redis

**Windows:**
- Download from [Microsoft Archive Redis](https://github.com/MicrosoftArchive/redis/releases)
- Install and start as a service

**Linux:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis-server
```

**macOS:**
```bash
brew install redis
redis-server
```

### 7. Start the Development Server

**Terminal 1: Django Server**
```bash
python manage.py runserver
```

**Terminal 2: Celery Worker**
```bash
# Windows
python -m celery -A cre_studio_backend worker --loglevel=info --pool=solo

# Linux/macOS
celery -A cre_studio_backend worker --loglevel=info
```

**Terminal 3: Celery Beat (Optional - for scheduled tasks)**
```bash
# Windows
python -m celery -A cre_studio_backend beat --loglevel=info

# Linux/macOS
celery -A cre_studio_backend beat --loglevel=info
```

The API will be available at `http://localhost:8000/`

## 📁 Project Structure

```
cre_studio_backend/
├── authentication/              # User authentication & management
│   ├── models.py               # Custom user model
│   ├── serializers.py          # User serializers
│   ├── views.py                # Authentication views
│   ├── permissions.py          # Custom permissions
│   └── email.py                # Email templates
├── property_app/               # Property & campaign management
│   ├── models.py               # Property, Campaign, Comment models
│   ├── serializers.py          # API serializers
│   ├── views.py                # API views
│   ├── tasks.py                # Celery background tasks
│   ├── utils.py                # Utility functions (AI, email)
│   └── signals.py              # Django signals
├── cre_studio_backend/         # Project configuration
│   ├── settings.py             # Django settings
│   ├── urls.py                 # URL routing
│   ├── celery.py               # Celery configuration
│   └── wsgi.py                 # WSGI configuration
├── deployment/                 # Deployment scripts & configs
│   ├── setup.sh                # Server setup script
│   ├── deploy.sh               # Deployment script
│   ├── ssl_setup.sh            # SSL certificate setup
│   ├── nginx.conf              # Nginx configuration
│   ├── gunicorn.conf.py        # Gunicorn configuration
│   └── *.service               # Systemd service files
├── docs/                       # Documentation
│   ├── DEPLOYMENT_GUIDE.md     # Deployment instructions
│   ├── BACKGROUND_TASKS.md     # Celery tasks guide
│   ├── USER_MANAGEMENT_API.md  # User API documentation
│   ├── USER_PROFILE_API.md     # Profile API documentation
│   ├── CAMPAIGN_BUDGET_API_GUIDE.md
│   └── COMMENT_SYSTEM_API.md   # Comment system guide
├── templates/                  # Email templates
│   └── email/
├── static/                     # Static files
├── media/                      # User uploaded files
│   ├── campaign_assets/
│   ├── property_images/
│   └── comment_attachments/
├── manage.py                   # Django management script
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 📚 API Documentation

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/users/` | Register new user |
| POST | `/api/auth/jwt/create/` | Login (get JWT tokens) |
| POST | `/api/auth/jwt/refresh/` | Refresh access token |
| POST | `/api/auth/jwt/verify/` | Verify token |
| GET | `/api/auth/users/me/` | Get current user |
| PUT | `/api/auth/users/me/` | Update current user |
| POST | `/api/auth/users/activation/` | Activate user account |
| POST | `/api/auth/users/reset_password/` | Request password reset |
| POST | `/api/auth/users/reset_password_confirm/` | Confirm password reset |

### User Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users/` | List all users (Admin only) |
| GET | `/api/users/{id}/` | Get user details |
| PUT/PATCH | `/api/users/{id}/` | Update user |
| DELETE | `/api/users/{id}/` | Delete user (Admin only) |
| GET | `/api/profile/` | Get current user profile |
| PUT/PATCH | `/api/profile/` | Update current user profile |

### Properties

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/properties/` | List all properties |
| POST | `/api/properties/` | Create property |
| GET | `/api/properties/{id}/` | Get property details |
| PUT/PATCH | `/api/properties/{id}/` | Update property |
| DELETE | `/api/properties/{id}/` | Delete property |

### Campaigns

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/campaigns/` | List all campaigns |
| POST | `/api/campaigns/` | Create campaign (triggers AI generation) |
| GET | `/api/campaigns/{id}/` | Get campaign details |
| PUT/PATCH | `/api/campaigns/{id}/` | Update campaign |
| DELETE | `/api/campaigns/{id}/` | Delete campaign |
| POST | `/api/campaigns/{id}/process_ai_content/` | Manually trigger AI processing |

### Comments

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/campaigns/{id}/comments/` | List campaign comments |
| POST | `/api/campaigns/{id}/comments/` | Create comment |
| PUT/PATCH | `/api/comments/{id}/` | Update comment |
| DELETE | `/api/comments/{id}/` | Delete comment |

For detailed API documentation, see the `/docs` directory:
- [User Management API](docs/USER_MANAGEMENT_API.md)
- [User Profile API](docs/USER_PROFILE_API.md)
- [Comment System API](docs/COMMENT_SYSTEM_API.md)
- [Campaign Budget API](docs/CAMPAIGN_BUDGET_API_GUIDE.md)

## 🔄 Background Tasks

The application uses Celery for asynchronous task processing:

### AI Content Generation
When a campaign is created, AI content generation runs in the background:
1. Campaign is created with `ai_processing_status: "pending"`
2. Celery task generates Google Ads content (headlines, descriptions)
3. Status updates to `"processing"`, then `"completed"` or `"failed"`

### Email Notifications
- User activation emails
- Password reset emails
- Campaign update notifications
- Comment and reply notifications

For more details, see [Background Tasks Documentation](docs/BACKGROUND_TASKS.md)

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test authentication
python manage.py test property_app

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

## 🚀 Deployment

### Production Deployment (Ubuntu Server)

For detailed deployment instructions, see [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)

**Quick deployment:**

```bash
# 1. Clone repository on server
git clone <repository-url> /var/www/cre_studio_backend
cd /var/www/cre_studio_backend

# 2. Run setup script
chmod +x deployment/setup.sh
./deployment/setup.sh

# 3. Configure environment variables
nano .env

# 4. Set up SSL certificate
chmod +x deployment/ssl_setup.sh
./deployment/ssl_setup.sh yourdomain.com your-email@example.com

# 5. Start services
sudo systemctl start django celery celerybeat redis-server
```

### Required Services
- **Django** (Gunicorn) - Main application
- **Celery Worker** - Background task processing
- **Celery Beat** - Scheduled tasks
- **Redis** - Message broker and cache
- **Nginx** - Reverse proxy and static files
- **PostgreSQL** - Production database

## 🔐 Security

- JWT-based authentication with HTTP-only cookies
- CORS configuration for frontend integration
- CSRF protection enabled
- SQL injection protection via Django ORM
- XSS protection with Django templates
- HTTPS enforced in production
- Secure password hashing (PBKDF2)
- Rate limiting on authentication endpoints

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is proprietary and confidential.

## 👥 Authors

CRE Studio Development Team

## 📞 Support

For support and questions:
- Check the documentation in `/docs`
- Review the troubleshooting section in the deployment guide
- Contact the development team

## 🗺 Roadmap

- [ ] WebSocket support for real-time updates
- [ ] Advanced analytics dashboard
- [ ] Mobile app API enhancements
- [ ] Multi-language support
- [ ] Enhanced AI features
- [ ] Integration with more marketing platforms

## 🙏 Acknowledgments

- Django REST Framework team
- Celery project
- OpenAI for GPT integration
- All contributors and testers

---

**Version:** 1.0.0  
**Last Updated:** October 2025

