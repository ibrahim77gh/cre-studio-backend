from rest_framework import serializers
from .models import Campaign


class CampaignSubmissionSerializer(serializers.ModelSerializer):
    """
    A serializer to handle the data submission for the PMCB form.
    It links the submitted data directly to the Campaign model.
    """
    class Meta:
        model = Campaign
        # Exclude `created_at` and `updated_at` as they are auto-generated.
        # Include all other fields from the Campaign model that a client will fill out.
        fields = [
            'property',
            'pmcb_form_data',
            'meta_campaign_dates',
            'meta_video_image',
            'meta_main_copy_options',
            'meta_headline',
            'meta_desktop_display_copy',
            'meta_website_url',
            'meta_call_to_action',
            'google_campaign_dates',
            'google_creative',
            'google_headlines',
            'google_long_headline',
            'google_descriptions',
            'google_website_url',
            'notes',
        ]
        # Make `dms_sync_ready` read-only, as the client should not set this.
        read_only_fields = ['dms_sync_ready']