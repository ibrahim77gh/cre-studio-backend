# models.py
from django.db import models
from django.forms import ValidationError
from django.utils import timezone
from django.conf import settings
from django.core.validators import RegexValidator


class PropertyGroup(models.Model):
    """
    Represents a logical grouping of properties.
    For example, 'Shopping Centers' or 'Apartment Complexes'.
    """
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Property(models.Model):
    """
    Represents an individual property linked to a PropertyGroup.
    This model acts as a primary identifier for the DMS sheets.
    """
    property_group = models.ForeignKey(
        PropertyGroup,
        on_delete=models.CASCADE,
        related_name='properties'
    )
    name = models.CharField(max_length=255, unique=True)
    subdomain = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        validators=[RegexValidator(
            regex=r'^[a-z0-9-]+$',
            message="Only lowercase letters, numbers, and hyphens are allowed."
        )]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    theme = models.JSONField(null=True, blank=True)
    primary_image = models.ImageField(upload_to='property_images/', null=True, blank=True)
    logo = models.ImageField(upload_to='property_logos/', null=True, blank=True)

    def __str__(self):
        return self.name
    
class PropertyUserRole(models.TextChoices):
    TENANT = "tenant", "Tenant"
    PROPERTY_ADMIN = "property_admin", "Property Admin"
    GROUP_ADMIN = "group_admin", "Group Admin"

class UserPropertyMembership(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="property_memberships"
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="memberships",
        null=True, blank=True
    )
    property_group = models.ForeignKey(
        PropertyGroup,
        on_delete=models.CASCADE,
        related_name="memberships",
        null=True, blank=True
    )
    role = models.CharField(
        max_length=20,
        choices=PropertyUserRole.choices,
        default=PropertyUserRole.TENANT
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "property", "property_group"], 
                name="unique_user_property_group_membership"
            )
        ]

    def __str__(self):
        if self.property:
            return f"{self.user.email} - {self.property.name} ({self.role})"
        if self.property_group:
            return f"{self.user.email} - {self.property_group.name} ({self.role})"
        return f"{self.user.email} ({self.role})"

    def clean(self):
        if not self.property and not self.property_group:
            raise ValidationError("A membership must be linked to either a property or a property group.")
        if self.property and self.property_group:
            raise ValidationError("A membership cannot be linked to both a property and a property group.")


class Campaign(models.Model):
    """
    Represents a marketing campaign, with fields for Meta Ads and Google Display
    that are designed to map directly to the DMS Google Sheet.
    """
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='campaigns'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='campaigns'
    )
    pmcb_form_data = models.JSONField(null=True, blank=True)
    center = models.CharField(max_length=255, blank=True, null=True)
    
    # Campaign timeline
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    # Fields for Meta Ads Tab
    meta_main_copy_options = models.JSONField(null=True, blank=True) # Stores a list of texts
    meta_headline = models.TextField(blank=True, null=True) # Using TextField to avoid limits
    meta_desktop_display_copy = models.TextField(blank=True, null=True)
    meta_website_url = models.URLField(max_length=500, blank=True, null=True)
    meta_call_to_action = models.CharField(max_length=255, blank=True, null=True)
    meta_notes = models.TextField(blank=True, null=True)
    meta_ready = models.TextField(blank=True, null=True)

    # Fields for Google Display Tab
    google_headlines = models.JSONField(null=True, blank=True) # Using JSONField to store multiple headlines as a list
    google_long_headline = models.TextField(blank=True, null=True)
    google_descriptions = models.JSONField(null=True, blank=True) # Using JSONField to store multiple descriptions as a list
    google_website_url = models.URLField(max_length=500, blank=True, null=True)
    google_notes = models.TextField(blank=True, null=True)
    google_ready = models.TextField(blank=True, null=True)

    # General fields for all campaigns
    dms_sync_ready = models.BooleanField(default=False)
    approved_by_admin = models.BooleanField(default=False)
    approved_by_client = models.BooleanField(default=False)
    
    # AI Processing Status
    class AIProcessingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
    
    ai_processing_status = models.CharField(
        max_length=20,
        choices=AIProcessingStatus.choices,
        default=AIProcessingStatus.PENDING,
        help_text="Status of AI content generation for this campaign"
    )
    ai_processing_error = models.TextField(blank=True, null=True, help_text="Error message if AI processing failed")
    ai_processed_at = models.DateTimeField(null=True, blank=True, help_text="When AI processing was completed")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Campaign"
        verbose_name_plural = "Campaigns"

    def __str__(self):
        return f"Campaign for {self.property.name} - {self.pk}"
    
    def get_event_dates(self):
        """Get all event dates for this campaign"""
        return self.campaign_dates.filter(date_type='event').order_by('date')
    
    def get_all_dates(self):
        """Get all dates for this campaign"""
        return self.campaign_dates.all().order_by('date')


class CampaignDateType(models.TextChoices):
    EVENT = "event", "Event Date"
    MILESTONE = "milestone", "Milestone"
    DEADLINE = "deadline", "Deadline"
    PROMOTION = "promotion", "Promotion Date"


class CampaignDate(models.Model):
    """
    Represents important dates for a campaign (events, milestones, deadlines, etc.)
    """
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='campaign_dates'
    )
    date = models.DateField()
    date_type = models.CharField(
        max_length=20,
        choices=CampaignDateType.choices,
        default=CampaignDateType.EVENT
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    is_all_day = models.BooleanField(default=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'start_time']
        verbose_name = "Campaign Date"
        verbose_name_plural = "Campaign Dates"

    def __str__(self):
        return f"{self.title} - {self.date} ({self.get_date_type_display()})"

    @property
    def is_past(self):
        """Check if this date is in the past"""
        from django.utils import timezone
        return self.date < timezone.now().date()

    @property
    def is_today(self):
        """Check if this date is today"""
        from django.utils import timezone
        return self.date == timezone.now().date()


class CampaignBudget(models.Model):
    campaign = models.OneToOneField(
        Campaign,
        on_delete=models.CASCADE,
        related_name="budget"
    )
    creative_charges_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    total_gross = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    total_net = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    meta_gross = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    meta_net = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    display_gross = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    display_net = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Budget for {self.campaign.center or self.campaign.id}"

    # Calculated fields (for reports)
    @property
    def gross_with_deductions(self):
        return self.total_gross - self.creative_charges_deductions

    @property
    def net_with_deductions(self):
        return self.total_net - self.creative_charges_deductions


class CreativeAsset(models.Model):
    campaign = models.ForeignKey(
        "Campaign",
        on_delete=models.CASCADE,
        related_name="creative_assets"
    )
    file = models.FileField(upload_to="campaign_assets/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    asset_type = models.CharField(max_length=255, blank=True, null=True)  # e.g., image, video, etc.
    platform_type = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Asset {self.id} for Campaign {self.campaign_id}"



class ClientNotification(models.Model):
    """
    Notifications for the client dashboard.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.email} on Campaign {self.campaign.pk}"

