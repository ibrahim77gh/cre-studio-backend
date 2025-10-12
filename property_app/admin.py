from django.contrib import admin
from .models import (
    PropertyGroup, Property, UserPropertyMembership, 
    Campaign, CampaignDate, CampaignBudget, CreativeAsset, 
    ClientNotification, Platform, PlatformBudget
)

# Inline admin for related models
class CampaignDateInline(admin.TabularInline):
    model = CampaignDate
    extra = 1
    fields = ['date', 'date_type', 'title', 'description', 'is_all_day', 'start_time', 'end_time']

class CreativeAssetInline(admin.TabularInline):
    model = CreativeAsset
    extra = 1
    fields = ['file', 'asset_type', 'platform_type']
    readonly_fields = ['uploaded_at']

class PlatformBudgetInline(admin.TabularInline):
    model = PlatformBudget
    extra = 1
    fields = ['platform', 'gross_amount', 'net_amount']
    readonly_fields = ['net_amount']

class CampaignBudgetInline(admin.StackedInline):
    model = CampaignBudget
    extra = 0
    inlines = [PlatformBudgetInline]

# Enhanced Campaign admin
@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'property', 'user', 'start_date', 'end_date', 'created_at']
    list_filter = ['property', 'start_date', 'end_date', 'created_at']
    search_fields = ['property__name', 'user__email', 'center']
    inlines = [CampaignDateInline, CreativeAssetInline, CampaignBudgetInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('property', 'user', 'center', 'start_date', 'end_date')
        }),
        ('Meta Ads', {
            'fields': ('meta_headline', 'meta_main_copy_options', 'meta_desktop_display_copy', 
                      'meta_website_url', 'meta_call_to_action', 'meta_notes', 'meta_ready')
        }),
        ('Google Display', {
            'fields': ('google_headlines', 'google_long_headline', 'google_descriptions',
                      'google_website_url', 'google_notes', 'google_ready')
        }),
        ('Form Data', {
            'fields': ('pmcb_form_data',),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': ('dms_sync_ready',),
            'classes': ('collapse',)
        })
    )

# Enhanced CampaignDate admin
@admin.register(CampaignDate)
class CampaignDateAdmin(admin.ModelAdmin):
    list_display = ['title', 'campaign', 'date', 'date_type', 'is_all_day']
    list_filter = ['date_type', 'is_all_day', 'date']
    search_fields = ['title', 'campaign__property__name', 'description']
    ordering = ['date', 'start_time']

# Platform admin
@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'net_rate', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'display_name']
    ordering = ['name']

@admin.register(PlatformBudget)
class PlatformBudgetAdmin(admin.ModelAdmin):
    list_display = ['campaign_budget', 'platform', 'gross_amount', 'net_amount']
    list_filter = ['platform', 'created_at']
    search_fields = ['campaign_budget__campaign__center', 'platform__display_name']
    readonly_fields = ['net_amount']

# Register other models
admin.site.register(PropertyGroup)
admin.site.register(Property)
admin.site.register(UserPropertyMembership)
admin.site.register(CampaignBudget)
admin.site.register(CreativeAsset)
admin.site.register(ClientNotification)
