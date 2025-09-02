from rest_framework import serializers
from .models import CreativeAsset, Property, PropertyGroup, Campaign

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
        ]
        read_only_fields = ['id', 'dms_sync_ready', 'created_at', 'updated_at', 'creative_assets_list']

    def create(self, validated_data):
        creative_assets = validated_data.pop('creative_assets', [])
        campaign = super().create(validated_data)
        for asset_file in creative_assets:
            CreativeAsset.objects.create(campaign=campaign, file=asset_file)
        return campaign
    
    def update(self, instance, validated_data):
        creative_assets = validated_data.pop('creative_assets', [])
        campaign = super().update(instance, validated_data)
        if creative_assets is not None:
            campaign.creative_assets.all().delete()
            for asset_file in creative_assets:
                CreativeAsset.objects.create(campaign=campaign, file=asset_file)
        return campaign
