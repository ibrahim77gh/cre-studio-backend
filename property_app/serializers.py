from rest_framework import serializers
from .models import CampaignBudget,CreativeAsset, Property, PropertyGroup, Campaign
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
        fields = [
            'id', 'name', 'slug', 'property_group', 'property_group_id', 'created_at', 'updated_at'
        ]


class CreativeAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreativeAsset
        fields = ["id", "file", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]



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
            'meta_campaign_dates',
            'meta_assets',
            'meta_main_copy_options',
            'meta_headline',
            'meta_desktop_display_copy',
            'meta_website_url',
            'meta_call_to_action',
            'meta_notes',
            'meta_ready',
            'google_campaign_dates',
            'google_assets',
            'google_headlines',
            'google_long_headline',
            'google_descriptions',
            'google_website_url',
            'google_notes',
            'google_ready',
            'dms_sync_ready',
            'created_at',
            'updated_at',
            'creative_assets',
            'creative_assets_list',
            'budget',
        ]
        read_only_fields = [
            'id',
            'dms_sync_ready',
            'created_at',
            'updated_at',
            'creative_assets_list',
        ]

    def create(self, validated_data):
        print(validated_data)

        creative_assets = validated_data.pop('creative_assets', [])
        pmcb_data = validated_data.pop('pmcb_form_data', {})
        budget_data = pmcb_data.pop('budget', None)

        # Store pmcb_form_data JSON in campaign
        validated_data['pmcb_form_data'] = pmcb_data

        # Create campaign
        campaign = super().create(validated_data)

        # Handle creative assets
        for asset_file in creative_assets:
            CreativeAsset.objects.create(campaign=campaign, file=asset_file)

        # Handle budget safely
        if budget_data:
            cleaned_budget = {}
            for k, v in budget_data.items():
                if v in ["", None]:   # convert "" to None
                    cleaned_budget[k] = None
                else:
                    cleaned_budget[k] = v
            CampaignBudget.objects.create(campaign=campaign, **cleaned_budget)
        else:
            CampaignBudget.objects.create(campaign=campaign)

        return campaign

    def update(self, instance, validated_data):
        creative_assets = validated_data.pop("creative_assets", [])
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

        # Handle budget
        if budget_data is not None:
            budget, _ = CampaignBudget.objects.get_or_create(campaign=campaign)

            for attr, value in budget_data.items():
                if hasattr(budget, attr):
                    setattr(budget, attr, value)

            budget.save()
        return campaign
