from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Campaign
from .tasks import process_campaign_ai_content

@receiver(post_save, sender=Campaign)
def auto_map_pmcb_data(sender, instance, created, **kwargs):
    """
    Automatically trigger AI processing for campaign content only when Campaign is created.
    Uses Celery background task to avoid blocking the API response.
    """
    if created and instance.pmcb_form_data:
        # Only process new campaigns with pmcb_form_data
        # process_campaign_ai_content.delay(instance.id)
        print(f"Processing campaign {instance.id} with pmcb_form_data")
