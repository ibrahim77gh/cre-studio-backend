from django.contrib.auth.models import AbstractBaseUser,    BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError


class UserManager(BaseUserManager):

  def _create_user(self, email, password, is_staff, is_superuser, **extra_fields):
    if not email:
        raise ValueError('Users must have an email address')
    now = timezone.now()
    email = self.normalize_email(email)
    user = self.model(
        email=email,
        is_staff=is_staff, 
        is_active=False,  # Users start inactive until invitation is accepted
        is_superuser=is_superuser, 
        last_login=now,
        date_joined=now, 
        **extra_fields
    )
    user.set_password(password)
    user.save(using=self._db)
    return user

  def create_user(self, email, password, **extra_fields):
    return self._create_user(email, password, False, False, **extra_fields)

  def create_superuser(self, email, password, **extra_fields):
    user=self._create_user(email, password, True, True, **extra_fields)
    user.save(using=self._db)
    return user


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=254, unique=True)
    first_name = models.CharField(max_length=254, null=True, blank=True)
    last_name = models.CharField(max_length=254, null=True, blank=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)  # Changed to False - users need invitation acceptance
    last_login = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    
    # Invitation fields
    invitation_sent = models.BooleanField(default=False)
    invitation_accepted = models.BooleanField(default=False)
    invitation_token = models.CharField(max_length=100, blank=True, null=True)
    invitation_sent_at = models.DateTimeField(null=True, blank=True)
    invitation_accepted_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    def __str__(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.email

    def get_absolute_url(self):
        return "/users/%i/" % (self.pk)
    
    def is_property_admin(self, property):
        """Check if user is admin of a specific property"""
        if self.is_superuser:
            return True
        
        from property_app.models import PropertyUserRole
        return self.property_memberships.filter(
            property=property, role=PropertyUserRole.PROPERTY_ADMIN
        ).exists()
    
    def is_group_admin(self, property_group):
        """Check if user is admin of a specific property group"""
        if self.is_superuser:
            return True
            
        from property_app.models import PropertyUserRole
        return self.property_memberships.filter(
            property_group=property_group, role=PropertyUserRole.GROUP_ADMIN
        ).exists()
    
    def get_managed_properties(self):
        """Get all properties this user can manage"""
        if self.is_superuser:
            from property_app.models import Property
            return Property.objects.all()
            
        from property_app.models import PropertyUserRole, Property
        managed_property_ids = set()
        
        for membership in self.property_memberships.all():
            if membership.role == PropertyUserRole.GROUP_ADMIN and membership.property_group:
                # Group admins can manage all properties in their group
                group_properties = membership.property_group.properties.all()
                managed_property_ids.update(group_properties.values_list('id', flat=True))
            elif membership.role == PropertyUserRole.PROPERTY_ADMIN and membership.property:
                # Property admins can manage their specific property
                managed_property_ids.add(membership.property.id)
                
        return Property.objects.filter(id__in=managed_property_ids)
    
    def get_managed_users(self):
        """Get all users this user can manage"""
        if self.is_superuser:
            return CustomUser.objects.all()
            
        from property_app.models import PropertyUserRole
        manageable_user_ids = set()
        
        for membership in self.property_memberships.all():
            if membership.role == PropertyUserRole.GROUP_ADMIN and membership.property_group:
                # Group admins can manage users in their property group
                group_properties = membership.property_group.properties.all()
                
                # Users in group properties
                group_property_users = CustomUser.objects.filter(
                    property_memberships__property__in=group_properties,
                    property_memberships__role__in=[PropertyUserRole.PROPERTY_ADMIN, PropertyUserRole.TENANT]
                )
                
                # Users directly in the group
                group_users = CustomUser.objects.filter(
                    property_memberships__property_group=membership.property_group,
                    property_memberships__role__in=[PropertyUserRole.PROPERTY_ADMIN, PropertyUserRole.TENANT]
                )
                
                manageable_user_ids.update(group_property_users.values_list('id', flat=True))
                manageable_user_ids.update(group_users.values_list('id', flat=True))
                
            elif membership.role == PropertyUserRole.PROPERTY_ADMIN and membership.property:
                # Property admins can manage tenants in their property
                property_tenants = CustomUser.objects.filter(
                    property_memberships__property=membership.property,
                    property_memberships__role=PropertyUserRole.TENANT
                )
                manageable_user_ids.update(property_tenants.values_list('id', flat=True))
        
        return CustomUser.objects.filter(id__in=manageable_user_ids)
    
    def has_access_to_app(self, app):
        """Check if user has access to a specific app"""
        if self.is_superuser:
            return True
        return self.app_memberships.filter(app=app).exists()
    
    def get_accessible_apps(self):
        """Get all apps this user has access to"""
        if self.is_superuser:
            return App.objects.all()
        return App.objects.filter(memberships__user=self).distinct()
    
    def get_app_membership(self, app):
        """Get the user's membership for a specific app"""
        try:
            return self.app_memberships.get(app=app)
        except UserAppMembership.DoesNotExist:
            return None


class App(models.Model):
    """
    Represents an application in the multi-app system.
    Users must be assigned to an app to access it.
    """
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=100, unique=True, help_text="URL-friendly identifier for the app")
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "App"
        verbose_name_plural = "Apps"
    
    def __str__(self):
        return self.name


class UserAppMembership(models.Model):
    """
    Represents a user's membership/assignment to an app.
    Users must have a membership to login to an app.
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="app_memberships"
    )
    app = models.ForeignKey(
        App,
        on_delete=models.CASCADE,
        related_name="memberships"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'app']
        verbose_name = "User App Membership"
        verbose_name_plural = "User App Memberships"
    
    def __str__(self):
        return f"{self.user.email} - {self.app.name}"
    
    def clean(self):
        """Validate that user and app are provided"""
        if not self.user:
            raise ValidationError("User is required.")
        if not self.app:
            raise ValidationError("App is required.")