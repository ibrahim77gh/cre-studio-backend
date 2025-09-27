from celery import shared_task
from django.utils import timezone
import logging
from .models import Campaign
from .utils import map_pmcb_to_campaign_fields

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_campaign_ai_content(self, campaign_id):
    """
    Background task to process AI content generation for a campaign.
    
    Args:
        campaign_id (int): The ID of the campaign to process
        
    Returns:
        dict: Task result with status and details
    """
    try:
        # Get the campaign instance
        campaign = Campaign.objects.get(id=campaign_id)
        
        # Update status to processing
        campaign.ai_processing_status = Campaign.AIProcessingStatus.PROCESSING
        campaign.ai_processing_error = None
        campaign.save(update_fields=['ai_processing_status', 'ai_processing_error'])
        
        logger.info(f"Starting AI processing for campaign {campaign_id}")
        
        # Process the AI content generation
        if campaign.pmcb_form_data:
            map_pmcb_to_campaign_fields(campaign, campaign.pmcb_form_data)
            
        # Mark as completed
        campaign.ai_processing_status = Campaign.AIProcessingStatus.COMPLETED
        campaign.ai_processed_at = timezone.now()
        campaign.save(update_fields=['ai_processing_status', 'ai_processed_at'])
        
        logger.info(f"Completed AI processing for campaign {campaign_id}")
        
        return {
            'status': 'completed',
            'campaign_id': campaign_id,
            'processed_at': timezone.now().isoformat(),
            'message': 'AI content generation completed successfully'
        }
        
    except Campaign.DoesNotExist:
        logger.error(f"Campaign {campaign_id} not found")
        return {
            'status': 'failed',
            'campaign_id': campaign_id,
            'error': f'Campaign {campaign_id} not found'
        }
        
    except Exception as exc:
        logger.error(f"Error processing campaign {campaign_id}: {str(exc)}")
        
        # Update campaign with error status
        try:
            campaign = Campaign.objects.get(id=campaign_id)
            campaign.ai_processing_status = Campaign.AIProcessingStatus.FAILED
            campaign.ai_processing_error = str(exc)
            campaign.save(update_fields=['ai_processing_status', 'ai_processing_error'])
        except Campaign.DoesNotExist:
            pass
        
        # Retry the task if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task for campaign {campaign_id}, attempt {self.request.retries + 1}")
            raise self.retry(exc=exc)
        
        # If max retries exceeded, mark as failed
        return {
            'status': 'failed',
            'campaign_id': campaign_id,
            'error': str(exc),
            'retries': self.request.retries
        }


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_comment_email_notifications_task(self, comment_id, notification_user_ids):
    """
    Celery task wrapper for sending comment email notifications.
    
    Args:
        comment_id (int): The ID of the comment
        notification_user_ids (list): List of user IDs to notify
        
    Returns:
        dict: Task result with status and details
    """
    try:
        from .utils import send_comment_email_notifications
        send_comment_email_notifications(comment_id, notification_user_ids)
        
        logger.info(f"Successfully sent comment email notifications for comment {comment_id}")
        
        return {
            'status': 'completed',
            'comment_id': comment_id,
            'notified_users': len(notification_user_ids),
            'message': 'Comment email notifications sent successfully'
        }
        
    except Exception as exc:
        logger.error(f"Error sending comment email notifications for comment {comment_id}: {str(exc)}")
        
        # Retry the task if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying comment email task for comment {comment_id}, attempt {self.request.retries + 1}")
            raise self.retry(exc=exc)
        
        return {
            'status': 'failed',
            'comment_id': comment_id,
            'error': str(exc),
            'retries': self.request.retries
        }


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_campaign_update_email_notifications_task(self, campaign_id, updated_by_id, update_type):
    """
    Celery task wrapper for sending campaign update email notifications.
    
    Args:
        campaign_id (int): The ID of the campaign
        updated_by_id (int): The ID of the user who updated the campaign
        update_type (str): The type of update
        
    Returns:
        dict: Task result with status and details
    """
    try:
        from .utils import send_campaign_update_email_notifications
        send_campaign_update_email_notifications(campaign_id, updated_by_id, update_type)
        
        logger.info(f"Successfully sent campaign update email notifications for campaign {campaign_id}")
        
        return {
            'status': 'completed',
            'campaign_id': campaign_id,
            'updated_by_id': updated_by_id,
            'update_type': update_type,
            'message': 'Campaign update email notifications sent successfully'
        }
        
    except Exception as exc:
        logger.error(f"Error sending campaign update email notifications for campaign {campaign_id}: {str(exc)}")
        
        # Retry the task if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying campaign update email task for campaign {campaign_id}, attempt {self.request.retries + 1}")
            raise self.retry(exc=exc)
        
        return {
            'status': 'failed',
            'campaign_id': campaign_id,
            'error': str(exc),
            'retries': self.request.retries
        }