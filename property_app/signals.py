from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Campaign
from .utils import map_pmcb_to_campaign_fields

@receiver(post_save, sender=Campaign)
def auto_map_pmcb_data(sender, instance, created, **kwargs):
    """
    Automatically map pmcb_form_data to Meta and Google fields when Campaign is saved.
    Only trigger if pmcb_form_data has changed or is newly set.
    """
    if instance.pmcb_form_data:
        # Check if pmcb_form_data was updated (for existing instances)
        if not created:
            # Get the previous instance from database
            try:
                previous = Campaign.objects.get(pk=instance.pk)
                if previous.pmcb_form_data != instance.pmcb_form_data:
                    map_pmcb_to_campaign_fields(instance, instance.pmcb_form_data)
            except Campaign.DoesNotExist:
                pass
        else:
            # For new instances, always map if pmcb_form_data is present
            map_pmcb_to_campaign_fields(instance, instance.pmcb_form_data)