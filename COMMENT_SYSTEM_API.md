# Campaign Commenting and Notification System

## Overview

I've successfully built a comprehensive commenting and notification system around Campaigns that allows tenant and admin users to comment, ask questions, and reply to comments. All relevant users attached to the campaign receive both app and email notifications.

## Features Implemented

### 1. CampaignComment Model
- **Threaded Comments**: Support for replies to comments with `parent_comment` field
- **User Attribution**: Each comment is linked to the user who created it
- **Resolution Status**: Comments can be marked as resolved
- **Timestamps**: Created and updated timestamps for tracking

### 2. Enhanced ClientNotification Model
- **Notification Types**: Support for different notification types (comment, comment_reply, campaign_update, approval)
- **Comment Linking**: Direct link to the comment that triggered the notification
- **Rich Content**: Title and message fields for better notification display

### 3. Permission System
- **Tenant Users**: Can comment on campaigns for their assigned properties
- **Property Admins**: Can comment and manage comments for their properties
- **Group Admins**: Can comment and manage comments for all properties in their group
- **Superusers**: Full access to all comments

### 4. Notification Logic
- **Automatic Notifications**: Sent to all relevant users when comments are created
- **Smart Filtering**: Comment authors don't receive notifications for their own comments
- **Email Integration**: HTML email notifications with comment previews

### 5. API Endpoints

#### Comments API
- `GET /api/comments/` - List all comments user has access to
- `POST /api/comments/` - Create a new comment (with optional file attachments)
- `GET /api/comments/{id}/` - Get specific comment details
- `PUT/PATCH /api/comments/{id}/` - Update comment
- `DELETE /api/comments/{id}/` - Delete comment
- `POST /api/comments/{id}/mark_resolved/` - Mark comment as resolved
- `GET /api/comments/by_campaign/?campaign_id={id}` - Get all comments for a campaign

#### Comment Attachments API
- `GET /api/comment-attachments/` - List all attachments user has access to
- `POST /api/comment-attachments/` - Upload a new attachment
- `GET /api/comment-attachments/{id}/` - Get specific attachment details
- `PUT/PATCH /api/comment-attachments/{id}/` - Update attachment
- `DELETE /api/comment-attachments/{id}/` - Delete attachment
- `GET /api/comment-attachments/by_comment/?comment_id={id}` - Get all attachments for a comment

#### Notifications API
- `GET /api/notifications/` - List user's notifications
- `POST /api/notifications/{id}/mark_as_read/` - Mark notification as read

## Usage Examples

### Creating a Comment

```javascript
// Create a new comment (without attachments)
POST /api/comments/
{
    "campaign": 123,
    "content": "This campaign looks great! When will it go live?",
    "parent_comment": null  // null for root comment
}

// Create a comment with file attachments
POST /api/comments/
Content-Type: multipart/form-data

{
    "campaign": 123,
    "content": "Here's the updated design with some reference images",
    "parent_comment": null,
    "attachment_files": [file1, file2, file3]  // File uploads
}

// Reply to an existing comment with attachments
POST /api/comments/
Content-Type: multipart/form-data

{
    "campaign": 123,
    "content": "Thanks! Here are the requested changes.",
    "parent_comment": 456,
    "attachment_files": [file1, file2]
}
```

### Getting Comments for a Campaign

```javascript
// Get all comments for a specific campaign
GET /api/comments/by_campaign/?campaign_id=123

// Response includes threaded structure
{
    "campaign_id": 123,
    "campaign_name": "Campaign for Property Name - 123",
    "comments": [
        {
            "id": 1,
            "campaign": 123,
            "user": 5,
            "user_name": "John Doe",
            "user_email": "john@example.com",
            "parent_comment": null,
            "content": "This campaign looks great!",
            "is_resolved": false,
            "is_reply": false,
            "reply_count": 2,
            "replies": [
                {
                    "id": 2,
                    "parent_comment": 1,
                    "content": "Thanks!",
                    "is_reply": true,
                    "replies": null
                }
            ],
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z"
        }
    ]
}
```

### Managing Notifications

```javascript
// Get user's notifications
GET /api/notifications/

// Mark notification as read
POST /api/notifications/123/mark_as_read/

// Mark comment as resolved
POST /api/comments/456/mark_resolved/
```

## Email Notifications (Background Processing)

### Comment Notification Email
- **Subject**: "New Comment on Campaign {campaign_name}"
- **Content**: Includes campaign details, comment content, and author information
- **Template**: `templates/email/comment_notification.html`
- **Processing**: Sent asynchronously via Celery task

### Comment Reply Notification Email
- **Subject**: "New Reply on Campaign {campaign_name}"
- **Content**: Shows both original comment and reply with threading context
- **Template**: `templates/email/comment_reply_notification.html`
- **Processing**: Sent asynchronously via Celery task

### Campaign Update Notification Email
- **Subject**: "Campaign {campaign_name} Updated"
- **Content**: Includes campaign details, update information, and who made the update
- **Template**: `templates/email/campaign_update_notification.html`
- **Processing**: Sent asynchronously via Celery task

## Database Schema

### CampaignComment
```sql
- id (Primary Key)
- campaign (ForeignKey to Campaign)
- user (ForeignKey to User)
- parent_comment (ForeignKey to CampaignComment, nullable)
- content (TextField)
- is_resolved (BooleanField, default=False)
- created_at (DateTimeField)
- updated_at (DateTimeField)
```

### CampaignCommentAttachment
```sql
- id (Primary Key)
- comment (ForeignKey to CampaignComment)
- file (FileField, upload_to='comment_attachments/')
- original_filename (CharField, max_length=255)
- file_size (PositiveIntegerField)
- file_type (CharField, max_length=100)
- uploaded_at (DateTimeField)
```

### ClientNotification (Enhanced)
```sql
- id (Primary Key)
- user (ForeignKey to User)
- campaign (ForeignKey to Campaign)
- comment (ForeignKey to CampaignComment, nullable)
- notification_type (CharField with choices)
- title (CharField)
- message (TextField)
- is_read (BooleanField, default=False)
- created_at (DateTimeField)
```

## Security Features

1. **Permission Validation**: Users can only comment on campaigns they have access to
2. **Comment Resolution**: Only comment authors and admins can mark comments as resolved
3. **Notification Privacy**: Users only receive notifications for campaigns they're involved in
4. **Email Security**: Email notifications include proper authentication context

## Integration Points

1. **Campaign Updates**: The system can be extended to send notifications when campaigns are updated
2. **Approval Workflow**: Notifications can be sent when campaigns are approved/rejected
3. **File Attachments**: Comments can be extended to support file attachments
4. **Mention System**: Users can be mentioned in comments for targeted notifications

## Celery Background Tasks

### Available Tasks

1. **`send_comment_email_notifications_task`**
   - Sends email notifications for new comments and replies
   - Retries up to 3 times with 30-second delays
   - Parameters: `comment_id`, `notification_user_ids`

2. **`send_campaign_update_email_notifications_task`**
   - Sends email notifications for campaign updates
   - Retries up to 3 times with 30-second delays
   - Parameters: `campaign_id`, `updated_by_id`, `update_type`

3. **`process_campaign_ai_content`**
   - Processes AI content generation for campaigns
   - Retries up to 3 times with 60-second delays
   - Parameters: `campaign_id`

### Running Celery

To process background tasks, run Celery worker:

```bash
# Activate virtual environment
venv\Scripts\activate

# Start Celery worker
celery -A cre_studio_backend worker --loglevel=info
```

### Task Monitoring

Monitor task execution and results:

```bash
# Start Celery Flower (web-based monitoring)
celery -A cre_studio_backend flower
```

## Next Steps

1. **Frontend Integration**: Build React/Vue components to display comments and notifications
2. **Real-time Updates**: Add WebSocket support for real-time comment updates
3. **Email Preferences**: Allow users to configure notification preferences
4. **Comment Moderation**: Add admin tools for moderating comments
5. **Search and Filtering**: Add search functionality for comments and notifications
6. **Task Monitoring**: Set up proper logging and monitoring for background tasks

This system provides a solid foundation for campaign collaboration and communication, with proper permission controls, notification mechanisms, and background processing for optimal performance.
