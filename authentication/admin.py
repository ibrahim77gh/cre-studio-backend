from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser, App, UserAppMembership

@admin.register(CustomUser)
class UserAdmin(BaseUserAdmin):
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name'),
        }),
    )

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (("Personal info"), {"fields": ("first_name", "last_name")}),
        (
            ("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (("Important dates"), {"fields": ("last_login",)}),
    )

    list_display = ('email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser', 'date_joined')
    list_filter = ("is_staff", "is_superuser", "is_active")
    ordering = ("first_name", "last_name")


    def get_list_editable(self, request):
        # Exclude 'date_joined' from list_editable
        editable_fields = super().get_list_editable(request)
        if 'date_joined' in editable_fields:
            editable_fields.remove('date_joined')
        return editable_fields


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UserAppMembership)
class UserAppMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'app', 'created_at')
    list_filter = ('app', 'created_at')
    search_fields = ('user__email', 'app__name', 'app__slug')
    readonly_fields = ('created_at',)

