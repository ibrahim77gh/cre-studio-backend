from django.contrib.auth.models import AbstractBaseUser,    BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):

  def _create_user(self, email, password, is_staff, is_superuser, **extra_fields):
    if not email:
        raise ValueError('Users must have an email address')
    now = timezone.now()
    email = self.normalize_email(email)
    user = self.model(
        email=email,
        is_staff=is_staff, 
        is_active=True,
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
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

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
    