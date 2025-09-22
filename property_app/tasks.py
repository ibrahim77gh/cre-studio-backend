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