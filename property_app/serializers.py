from rest_framework import serializers
from .models import CampaignBudget, CreativeAsset, Property, PropertyGroup, Campaign, ClientNotification, CampaignDate
import json

class PropertyGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyGroup
        fields = ['id', 'name', 'created_at', 'updated_at']

class PropertySerializer(serializers.ModelSerializer):
    property_group = PropertyGroupSerializer(read_only=True)
    property_group_id = serializers.PrimaryKeyRelatedField(
        queryset=PropertyGroup.objects.all(), source='property_group', write_only=True
    )

    class Meta:
        model = Property
        fields = "__all__"


class CreativeAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreativeAsset
        fields = ["id", "file", "uploaded_at", "asset_type", "platform_type"]
        read_only_fields = ["id", "uploaded_at"]


class CampaignDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignDate
        fields = [
            "id", "campaign", "date", "date_type", "title", "description",
            "is_all_day", "start_time", "end_time", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]



class CampaignBudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignBudget
        fields = "__all__"
        read_only_fields = ["id", "campaign"]

    def validate(self, data):
        for field, value in data.items():
            if value == "":
                data[field] = None
        return data


class CampaignSubmissionSerializer(serializers.ModelSerializer):
    """
    A serializer to handle the data submission for the PMCB form.
    It links the submitted data directly to the Campaign model.
    """

    creative_assets = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
        help_text="List of creative asset files to upload."
    )
    creative_assets_list = CreativeAssetSerializer(
        source="creative_assets",  # campaign.creative_assets (related_name)
        many=True,
        read_only=True
    )

    # Campaign dates
    campaign_dates = CampaignDateSerializer(many=True, required=False)
    event_dates = CampaignDateSerializer(many=True, read_only=True)

    # 🔥 budget is writable now
    budget = CampaignBudgetSerializer(required=False)

    class Meta:
        model = Campaign
        fields = [
            'id',
            'property',
            'user',
            'pmcb_form_data',
            'center',
            'start_date',
            'end_date',
            'meta_main_copy_options',
            'meta_headline',
            'meta_desktop_display_copy',
            'meta_website_url',
            'meta_call_to_action',
            'meta_notes',
            'meta_ready',
            'google_headlines',
            'google_long_headline',
            'google_descriptions',
            'google_website_url',
            'google_notes',
            'google_ready',
            'dms_sync_ready',
            'ai_processing_status',
            'ai_processing_error',
            'ai_processed_at',
            'approved_by_admin',
            'approved_by_client',
            'created_at',
            'updated_at',
            'creative_assets',
            'creative_assets_list',
            'campaign_dates',
            'event_dates',
            'budget',
        ]
        read_only_fields = [
            'id',
            'dms_sync_ready',
            'ai_processing_status',
            'ai_processing_error',
            'ai_processed_at',
            'created_at',
            'updated_at',
            'creative_assets_list',
            'event_dates',
        ]

    def create(self, validated_data):
        from .models import CampaignDate
        print(validated_data)

        creative_assets = validated_data.pop('creative_assets', [])
        campaign_dates_data = validated_data.pop('campaign_dates', [])
        pmcb_data = validated_data.pop('pmcb_form_data', {})

        # Store pmcb_form_data JSON in campaign
        validated_data['pmcb_form_data'] = pmcb_data

        # Create campaign
        campaign = super().create(validated_data)

        # Handle creative assets
        for asset_file in creative_assets:
            CreativeAsset.objects.create(campaign=campaign, file=asset_file)

        # Handle campaign dates
        for date_data in campaign_dates_data:
            CampaignDate.objects.create(campaign=campaign, **date_data)

        return campaign

    def update(self, instance, validated_data):
        creative_assets = validated_data.pop("creative_assets", [])
        campaign_dates_data = validated_data.pop("campaign_dates", [])
        request = self.context.get("request")

        # Extract raw budget JSON from request.data if present
        raw_budget = request.data.get("budget") if request else None
        budget_data = None
        if raw_budget:
            try:
                budget_data = json.loads(raw_budget)
            except Exception:
                budget_data = None

        # Update campaign fields
        campaign = super().update(instance, validated_data)

        # Handle creative assets
        if creative_assets:
            campaign.creative_assets.all().delete()
            for asset_file in creative_assets:
                CreativeAsset.objects.create(campaign=campaign, file=asset_file)

        # Handle campaign dates
        if campaign_dates_data:
            # Remove existing dates and create new ones
            campaign.campaign_dates.all().delete()
            for date_data in campaign_dates_data:
                CampaignDate.objects.create(campaign=campaign, **date_data)

        # Handle budget
        if budget_data is not None:
            budget, _ = CampaignBudget.objects.get_or_create(campaign=campaign)

            for attr, value in budget_data.items():
                if hasattr(budget, attr):
                    setattr(budget, attr, value)

            budget.save()
        return campaign


class ClientNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientNotification
        fields = ['id', 'user', 'campaign', 'message', 'is_read', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']
