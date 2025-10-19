from rest_framework import serializers
from .models import (
    CampaignBudget, CreativeAsset, Property, PropertyGroup, Campaign, Platform, PlatformBudget,
    ClientNotification, CampaignDate, CampaignComment, CampaignCommentAttachment
)
import json
import os

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
    campaign_id = serializers.IntegerField(write_only=True, required=False)
    file_url = serializers.SerializerMethodField(read_only=True)
    file_name = serializers.SerializerMethodField(read_only=True)
    file_size = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CreativeAsset
        fields = [
            "id", "campaign", "campaign_id", "file", "file_url", "file_name", 
            "file_size", "uploaded_at", "asset_type", "platform_type"
        ]
        read_only_fields = ["id", "uploaded_at", "file_url", "file_name", "file_size"]
        extra_kwargs = {
            'file': {'required': False},  # Allow updates without file replacement
        }

    def get_file_url(self, obj):
        """Return the URL of the uploaded file."""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None

    def get_file_name(self, obj):
        """Return the original filename."""
        if obj.file:
            return os.path.basename(obj.file.name)
        return None

    def get_file_size(self, obj):
        """Return the file size in bytes."""
        if obj.file:
            try:
                return obj.file.size
            except (OSError, ValueError):
                return None
        return None

    def validate_file(self, value):
        """Validate file type and size."""
        if value:
            # Check file size (max 50MB)
            max_size = 50 * 1024 * 1024  # 50MB in bytes
            if value.size > max_size:
                raise serializers.ValidationError(
                    f"File size cannot exceed 50MB. Current size: {value.size / (1024*1024):.1f}MB"
                )
            
            # Check file extension
            allowed_extensions = [
                '.jpg', '.jpeg', '.png', '.gif', '.webp',  # Images
                '.mp4', '.mov', '.avi', '.webm',  # Videos
                '.pdf', '.doc', '.docx',  # Documents
            ]
            
            file_ext = os.path.splitext(value.name)[1].lower()
            if file_ext not in allowed_extensions:
                raise serializers.ValidationError(
                    f"File type '{file_ext}' is not allowed. "
                    f"Allowed types: {', '.join(allowed_extensions)}"
                )
        
        return value

    def create(self, validated_data):
        # Handle campaign_id if provided
        campaign_id = validated_data.pop('campaign_id', None)
        if campaign_id:
            try:
                campaign = Campaign.objects.get(id=campaign_id)
                validated_data['campaign'] = campaign
            except Campaign.DoesNotExist:
                raise serializers.ValidationError({'campaign_id': 'Invalid campaign ID.'})
        
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Custom update method to handle file replacement properly.
        When a new file is uploaded, the old file is deleted from storage.
        """
        new_file = validated_data.get('file')
        
        # If a new file is being uploaded, clean up the old one
        if new_file and instance.file:
            old_file = instance.file
            # Django will handle the file deletion automatically when we save the new file
            # But we can add custom logic here if needed
            
        # Handle campaign_id if provided (in case user wants to move asset to different campaign)
        campaign_id = validated_data.pop('campaign_id', None)
        if campaign_id:
            try:
                campaign = Campaign.objects.get(id=campaign_id)
                validated_data['campaign'] = campaign
            except Campaign.DoesNotExist:
                raise serializers.ValidationError({'campaign_id': 'Invalid campaign ID.'})
        
        return super().update(instance, validated_data)


class CampaignDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignDate
        fields = [
            "id", "campaign", "date", "date_type", "title", "description",
            "is_all_day", "start_time", "end_time", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]



class PlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = Platform
        fields = ["id", "name", "display_name", "net_rate", "is_active"]
        read_only_fields = ["id"]


class PlatformBudgetSerializer(serializers.ModelSerializer):
    platform = PlatformSerializer(read_only=True)
    platform_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = PlatformBudget
        fields = ["id", "platform", "platform_id", "gross_amount", "net_amount"]
        read_only_fields = ["id", "net_amount"]

    def validate(self, data):
        for field, value in data.items():
            if value == "":
                data[field] = None
        return data


class CampaignBudgetSerializer(serializers.ModelSerializer):
    platform_budgets = PlatformBudgetSerializer(many=True, required=False)
    
    # Backward compatibility properties
    meta_gross = serializers.SerializerMethodField(read_only=True)
    meta_net = serializers.SerializerMethodField(read_only=True)
    display_gross = serializers.SerializerMethodField(read_only=True)
    display_net = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = CampaignBudget
        fields = [
            "id", "campaign", "creative_charges_deductions", "total_gross", "total_net",
            "platform_budgets",
            "meta_gross", "meta_net", "display_gross", "display_net"
        ]
        read_only_fields = ["id", "campaign", "total_net"]

    def get_meta_gross(self, obj):
        """Get Meta platform gross amount for backward compatibility"""
        meta_budget = obj.get_platform_budget('meta')
        return meta_budget.gross_amount if meta_budget else None

    def get_meta_net(self, obj):
        """Get Meta platform net amount for backward compatibility"""
        meta_budget = obj.get_platform_budget('meta')
        return meta_budget.net_amount if meta_budget else None

    def get_display_gross(self, obj):
        """Get Google Display platform gross amount for backward compatibility"""
        display_budget = obj.get_platform_budget('google_display')
        return display_budget.gross_amount if display_budget else None

    def get_display_net(self, obj):
        """Get Google Display platform net amount for backward compatibility"""
        display_budget = obj.get_platform_budget('google_display')
        return display_budget.net_amount if display_budget else None

    def validate(self, data):
        for field, value in data.items():
            if value == "":
                data[field] = None
        return data

    def update(self, instance, validated_data):
        platform_budgets_data = validated_data.pop('platform_budgets', [])
        
        # Update main budget fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Handle platform budgets - if platform_budgets is provided, replace all existing ones
        if 'platform_budgets' in self.initial_data:
            # Get list of platform IDs from the request
            requested_platform_ids = set()
            
            # Update/create platform budgets from request
            for platform_budget_data in platform_budgets_data:
                platform_id = platform_budget_data.pop('platform_id')
                requested_platform_ids.add(platform_id)
                platform = Platform.objects.get(id=platform_id)
                
                platform_budget, created = PlatformBudget.objects.get_or_create(
                    campaign_budget=instance,
                    platform=platform
                )
                
                for attr, value in platform_budget_data.items():
                    setattr(platform_budget, attr, value)
                platform_budget.save()
            
            # Remove platform budgets that are not in the request
            existing_platform_budgets = PlatformBudget.objects.filter(campaign_budget=instance)
            for existing_budget in existing_platform_budgets:
                if existing_budget.platform.id not in requested_platform_ids:
                    existing_budget.delete()
        
        instance.save()
        return instance


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
            'approval_status',
            'ai_processing_status',
            'ai_processing_error',
            'ai_processed_at',
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
        print(validated_data)

        creative_assets = validated_data.pop('creative_assets', [])
        campaign_dates_data = validated_data.pop('campaign_dates', [])
        pmcb_data = validated_data.pop('pmcb_form_data', {})
        request = self.context.get("request")

        # Extract raw budget JSON from request.data if present
        raw_budget = request.data.get("budget") if request else None
        budget_data = None
        if raw_budget:
            try:
                budget_data = json.loads(raw_budget)
            except Exception:
                budget_data = None

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

        # Handle budget
        if budget_data is not None:
            budget = CampaignBudget.objects.create(campaign=campaign)
            for attr, value in budget_data.items():
                if hasattr(budget, attr):
                    setattr(budget, attr, value)
            budget.save()

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

        # Check for approval status change before updating
        old_approval_status = instance.approval_status
        new_approval_status = validated_data.get('approval_status', old_approval_status)
        approval_status_changed = old_approval_status != new_approval_status

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

        # Send approval status change notification if status changed
        if approval_status_changed and request and request.user:
            from .utils import send_approval_status_notification
            send_approval_status_notification(campaign, old_approval_status, new_approval_status, request.user)

        return campaign


class CampaignCommentAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField(read_only=True)
    file_name = serializers.SerializerMethodField(read_only=True)
    file_size_mb = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CampaignCommentAttachment
        fields = [
            'id', 'file', 'file_url', 'file_name', 'original_filename',
            'file_size', 'file_size_mb', 'file_type', 'uploaded_at'
        ]
        read_only_fields = ['id', 'file_url', 'file_name', 'file_size_mb', 'uploaded_at']

    def get_file_url(self, obj):
        """Return the URL of the uploaded file."""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None

    def get_file_name(self, obj):
        """Return the original filename."""
        return obj.original_filename

    def get_file_size_mb(self, obj):
        """Return the file size in MB."""
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return None

    def validate_file(self, value):
        """Validate file type and size."""
        if value:
            # Check file size (max 25MB)
            max_size = 25 * 1024 * 1024  # 25MB in bytes
            if value.size > max_size:
                raise serializers.ValidationError(
                    f"File size cannot exceed 25MB. Current size: {value.size / (1024*1024):.1f}MB"
                )
            
            # Check file extension
            allowed_extensions = [
                '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp',  # Images
                '.mp4', '.mov', '.avi', '.webm', '.mkv',  # Videos
                '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',  # Documents
                '.txt', '.csv', '.zip', '.rar', '.7z',  # Other files
            ]
            
            file_ext = os.path.splitext(value.name)[1].lower()
            if file_ext not in allowed_extensions:
                raise serializers.ValidationError(
                    f"File type '{file_ext}' is not allowed. "
                    f"Allowed types: {', '.join(allowed_extensions)}"
                )
            
            # Set file type based on extension
            if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
                self.file_type = 'image'
            elif file_ext in ['.mp4', '.mov', '.avi', '.webm', '.mkv']:
                self.file_type = 'video'
            elif file_ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']:
                self.file_type = 'document'
            else:
                self.file_type = 'other'
        
        return value

    def create(self, validated_data):
        """Create attachment with proper file handling."""
        if 'file' in validated_data:
            file = validated_data['file']
            validated_data['original_filename'] = file.name
            validated_data['file_size'] = file.size
            
            # Set file type
            file_ext = os.path.splitext(file.name)[1].lower()
            if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
                validated_data['file_type'] = 'image'
            elif file_ext in ['.mp4', '.mov', '.avi', '.webm', '.mkv']:
                validated_data['file_type'] = 'video'
            elif file_ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']:
                validated_data['file_type'] = 'document'
            else:
                validated_data['file_type'] = 'other'
        
        return super().create(validated_data)


class CampaignCommentSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField(read_only=True)
    user_email = serializers.SerializerMethodField(read_only=True)
    replies = serializers.SerializerMethodField(read_only=True)
    is_reply = serializers.SerializerMethodField(read_only=True)
    reply_count = serializers.SerializerMethodField(read_only=True)
    attachments = CampaignCommentAttachmentSerializer(many=True, read_only=True)
    attachment_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
        help_text="List of files to attach to the comment."
    )

    class Meta:
        model = CampaignComment
        fields = [
            'id', 'campaign', 'user', 'user_name', 'user_email', 'parent_comment',
            'content', 'is_resolved', 'is_reply', 'reply_count', 'replies',
            'attachments', 'attachment_files', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_user_name(self, obj):
        """Get the user's full name"""
        if obj.user.first_name and obj.user.last_name:
            return f"{obj.user.first_name} {obj.user.last_name}"
        return obj.user.email

    def get_user_email(self, obj):
        """Get the user's email"""
        return obj.user.email

    def get_is_reply(self, obj):
        """Check if this comment is a reply"""
        return obj.is_reply

    def get_reply_count(self, obj):
        """Get the number of replies to this comment"""
        return obj.replies.count()

    def get_replies(self, obj):
        """Get all replies to this comment"""
        if obj.is_reply:
            return None  # Don't show replies for reply comments to avoid infinite nesting
        replies = obj.replies.all().order_by('created_at')
        return CampaignCommentSerializer(replies, many=True, context=self.context).data

    def create(self, validated_data):
        """Create a new comment with attachments"""
        attachment_files = validated_data.pop('attachment_files', [])
        validated_data['user'] = self.context['request'].user
        
        # Create the comment
        comment = super().create(validated_data)
        
        # Create attachments
        for file in attachment_files:
            CampaignCommentAttachment.objects.create(
                comment=comment,
                file=file
            )
        
        return comment

    def validate(self, data):
        """Validate comment data"""
        # Check if user has permission to comment on this campaign
        campaign = data.get('campaign')
        user = self.context['request'].user
        
        if campaign:
            # Check if user is associated with this campaign's property
            from .models import PropertyUserRole
            has_permission = (
                user.is_superuser or
                user.property_memberships.filter(
                    property=campaign.property,
                    role__in=[
                        PropertyUserRole.TENANT, 
                        PropertyUserRole.PROPERTY_ADMIN, 
                        PropertyUserRole.GROUP_ADMIN
                    ]
                ).exists() or
                user.property_memberships.filter(
                    property_group=campaign.property.property_group,
                    role=PropertyUserRole.GROUP_ADMIN
                ).exists()
            )
            
            if not has_permission:
                raise serializers.ValidationError(
                    "You don't have permission to comment on this campaign."
                )
        
        return data


class ClientNotificationSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField(read_only=True)
    user_email = serializers.SerializerMethodField(read_only=True)
    campaign_name = serializers.SerializerMethodField(read_only=True)
    comment_preview = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ClientNotification
        fields = [
            'id', 'user', 'user_name', 'user_email', 'campaign', 'campaign_name',
            'comment', 'notification_type', 'title', 'message', 'comment_preview',
            'is_read', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']

    def get_user_name(self, obj):
        """Get the user's full name"""
        if obj.user.first_name and obj.user.last_name:
            return f"{obj.user.first_name} {obj.user.last_name}"
        return obj.user.email

    def get_user_email(self, obj):
        """Get the user's email"""
        return obj.user.email

    def get_campaign_name(self, obj):
        """Get the campaign name"""
        return str(obj.campaign)

    def get_comment_preview(self, obj):
        """Get a preview of the comment if this is a comment notification"""
        if obj.comment and obj.notification_type in ['comment', 'comment_reply']:
            content = obj.comment.content
            return content[:100] + '...' if len(content) > 100 else content
        return None


class CampaignStatsSerializer(serializers.Serializer):
    """
    Serializer for campaign statistics by status.
    """
    property_id = serializers.IntegerField()
    property_name = serializers.CharField()
    total_campaigns = serializers.IntegerField()
    pending_count = serializers.IntegerField()
    admin_approved_count = serializers.IntegerField()
    client_approved_count = serializers.IntegerField()
    fully_approved_count = serializers.IntegerField()
