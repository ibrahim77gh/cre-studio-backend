# models.py
from django.db import models
from django.utils import timezone
from django.conf import settings

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
    slug = models.SlugField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class PropertyBudget(models.Model):
    """
    Stores budget information for a specific property.
    Using DecimalField for financial accuracy.
    """
    property = models.OneToOneField(
        Property,
        on_delete=models.CASCADE,
        related_name='budget'
    )
    gross_seasonal_campaign_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    creative_charges_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_gross = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_net = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    meta_gross = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    meta_net = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    display_gross = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    display_net = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Budget for {self.property.name}"

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
    # The form data from the PMCB
    pmcb_form_data = models.JSONField(null=True, blank=True)

    # Fields for Meta Ads Tab
    meta_campaign_dates = models.CharField(max_length=255, blank=True)
    meta_video_image = models.CharField(max_length=255, blank=True)
    meta_main_copy_options = models.JSONField(null=True, blank=True) # Stores a list of texts
    meta_headline = models.TextField(blank=True) # Using TextField to avoid limits
    meta_desktop_display_copy = models.TextField(blank=True)
    meta_website_url = models.URLField(max_length=500, blank=True)
    meta_call_to_action = models.CharField(max_length=255, blank=True)
    
    # Fields for Google Display Tab
    google_campaign_dates = models.CharField(max_length=255, blank=True)
    google_creative = models.CharField(max_length=255, blank=True)
    # Using JSONField to store multiple headlines as a list
    google_headlines = models.JSONField(null=True, blank=True)
    google_long_headline = models.TextField(blank=True)
    # Using JSONField to store multiple descriptions as a list
    google_descriptions = models.JSONField(null=True, blank=True)
    google_website_url = models.URLField(max_length=500, blank=True)

    # General fields for all campaigns
    notes = models.TextField(blank=True)
    dms_sync_ready = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Campaign"
        verbose_name_plural = "Campaigns"

    def __str__(self):
        return f"Campaign for {self.property.name} - {self.pk}"

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
        return f"Notification for {self.user.email} on {self.campaign.campaign_name}"