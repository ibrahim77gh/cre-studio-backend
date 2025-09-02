from django.contrib import admin
from .models import PropertyGroup, Property, UserPropertyMembership, Campaign

# Register your models here.
admin.site.register(PropertyGroup)
admin.site.register(Property)
admin.site.register(UserPropertyMembership)
admin.site.register(Campaign)
