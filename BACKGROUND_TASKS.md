# Background Task Processing Setup

This project now uses Celery for background processing of AI content generation for campaigns.

## Requirements

- Redis server (for message broker and result backend)
- Celery worker processes

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install and start Redis server:
   - **Windows**: Download and install Redis from https://github.com/MicrosoftArchive/redis/releases
   - **Linux/macOS**: `brew install redis` or `sudo apt-get install redis-server`

## Running the System

### 1. Start Redis Server
```bash
# Windows (if installed as service)
# Redis should start automatically

# Linux/macOS
redis-server
```

### 2. Start Django Development Server
```bash
python manage.py runserver
```

### 3. Start Celery Worker (in a separate terminal)
```bash
# Windows
C:/Work/retail_studio/cre-studio/cre_studio_backend/venv/Scripts/python.exe -m celery -A cre_studio_backend worker --loglevel=info --pool=solo

# Linux/macOS
celery -A cre_studio_backend worker --loglevel=info
```

### 4. (Optional) Start Celery Beat for Scheduled Tasks
```bash
# Windows
C:/Work/retail_studio/cre-studio/cre_studio_backend/venv/Scripts/python.exe -m celery -A cre_studio_backend beat --loglevel=info

# Linux/macOS
celery -A cre_studio_backend beat --loglevel=info
```

## How It Works

1. **Campaign Creation**: When a campaign is created via POST `/api/campaigns/`, it returns immediately with a 201 status
2. **Background Processing**: A Celery task is automatically triggered to process AI content generation
3. **Status Tracking**: The campaign has an `ai_processing_status` field that shows:
   - `pending`: AI processing has not started yet
   - `processing`: AI content generation is in progress
   - `completed`: AI processing finished successfully
   - `failed`: AI processing encountered an error

## API Changes

### New Fields in Campaign Response
```json
{
  "id": 1,
  "ai_processing_status": "pending",
  "ai_processing_error": null,
  "ai_processed_at": null,
  // ... other campaign fields
}
```

### Monitoring AI Processing
Clients can poll the campaign endpoint to check the `ai_processing_status`:

```bash
GET /api/campaigns/1/
```

## Production Deployment

For production, consider:
1. Using a process manager like systemd or supervisor for Celery workers
2. Setting up Redis clustering for high availability
3. Configuring proper logging and monitoring
4. Using a proper message broker like RabbitMQ instead of Redis for very high-throughput scenarios

## Troubleshooting

### Common Issues

1. **"No module named 'celery'"**: Make sure Celery is installed in your virtual environment
2. **Connection refused to Redis**: Ensure Redis server is running
3. **Tasks not processing**: Check that Celery worker is running and connected to Redis
4. **Import errors**: Make sure Django settings are properly configured

### Debugging Commands

```bash
# Check Celery worker status
celery -A cre_studio_backend status

# Monitor tasks in real-time
celery -A cre_studio_backend events

# Purge all pending tasks
celery -A cre_studio_backend purge
```