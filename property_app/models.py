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
        
    def is_property_admin(self, property):
        if self.is_superuser:
            return True
        return self.property_memberships.filter(
            property=property, role=PropertyUserRole.PROPERTY_ADMIN
        ).exists()


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

    # Fields for Meta Ads Tab
    meta_campaign_dates = models.CharField(max_length=255, blank=True, null=True)
    meta_assets = models.TextField(max_length=255, blank=True, null=True)
    meta_main_copy_options = models.JSONField(null=True, blank=True) # Stores a list of texts
    meta_headline = models.TextField(blank=True, null=True) # Using TextField to avoid limits
    meta_desktop_display_copy = models.TextField(blank=True, null=True)
    meta_website_url = models.URLField(max_length=500, blank=True, null=True)
    meta_call_to_action = models.CharField(max_length=255, blank=True, null=True)
    meta_notes = models.TextField(blank=True, null=True)
    meta_ready = models.TextField(blank=True, null=True)

    # Fields for Google Display Tab
    google_campaign_dates = models.CharField(max_length=255, blank=True, null=True)
    google_assets = models.CharField(max_length=255, blank=True, null=True)
    google_headlines = models.JSONField(null=True, blank=True) # Using JSONField to store multiple headlines as a list
    google_long_headline = models.TextField(blank=True, null=True)
    google_descriptions = models.JSONField(null=True, blank=True) # Using JSONField to store multiple descriptions as a list
    google_website_url = models.URLField(max_length=500, blank=True, null=True)
    google_notes = models.TextField(blank=True, null=True)
    google_ready = models.TextField(blank=True, null=True)

    # General fields for all campaigns
    dms_sync_ready = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Campaign"
        verbose_name_plural = "Campaigns"

    def __str__(self):
        return f"Campaign for {self.property.name} - {self.pk}"


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
        return f"Budget for {self.campaign.title or self.campaign.id}"

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

