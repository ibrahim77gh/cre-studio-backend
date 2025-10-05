from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.files.storage import default_storage
import os
from .models import Campaign, CreativeAsset, CampaignCommentAttachment
from .tasks import process_campaign_ai_content
from django.conf import settings

@receiver(post_save, sender=Campaign)
def auto_map_pmcb_data(sender, instance, created, **kwargs):
    """
    Automatically trigger AI processing for campaign content only when Campaign is created.
    Uses Celery background task to avoid blocking the API response.
    """
    if created and instance.pmcb_form_data:
        # Only process new campaigns with pmcb_form_data
        if not settings.DEBUG:
            process_campaign_ai_content.delay(instance.id)
        print(f"Processing campaign {instance.id} with pmcb_form_data")

@receiver(post_delete, sender=CreativeAsset)
def delete_creative_asset_file(sender, instance, **kwargs):
    """
    Delete the file associated with a CreativeAsset when the object is deleted.
    """
    if instance.file:
        try:
            if default_storage.exists(instance.file.name):
                default_storage.delete(instance.file.name)
                print(f"Deleted creative asset file: {instance.file.name}")
        except Exception as e:
            print(f"Error deleting creative asset file {instance.file.name}: {e}")

@receiver(post_delete, sender=CampaignCommentAttachment)
def delete_comment_attachment_file(sender, instance, **kwargs):
    """
    Delete the file associated with a CampaignCommentAttachment when the object is deleted.
    """
    if instance.file:
        try:
            if default_storage.exists(instance.file.name):
                default_storage.delete(instance.file.name)
                print(f"Deleted comment attachment file: {instance.file.name}")
        except Exception as e:
            print(f"Error deleting comment attachment file {instance.file.name}: {e}")
