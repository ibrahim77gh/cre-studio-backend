from djoser.serializers import UserSerializer as BaseUserSerializer, UserCreateSerializer as BaseUserCreateSerializer
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from property_app.models import PropertyUserRole, UserPropertyMembership, Property, PropertyGroup
from .models import CustomUser


class UserCreateSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        fields = ['id', 'password',
                  'email', 'first_name', 'last_name']
        

class UserSerializer(BaseUserSerializer):
    role = serializers.SerializerMethodField()

    class Meta(BaseUserSerializer.Meta):
        model = CustomUser
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "role",   # <-- add this
        ]

    def get_role(self, obj):
        # Superuser case
        if obj.is_superuser:
            return {"role": "super_user"}

        memberships = obj.property_memberships.all()

        if not memberships.exists():
            return {"role": None}

        # For simplicity, assume one active membership per user
        membership = memberships.first()

        if membership.role == PropertyUserRole.TENANT:
            return {
                "role": "tenant",
                "property": membership.property.id if membership.property else None,
            }

        if membership.role == PropertyUserRole.PROPERTY_ADMIN:
            return {
                "role": "property_admin",
                "property": membership.property.id if membership.property else None,
            }

        if membership.role == PropertyUserRole.GROUP_ADMIN:
            return {
                "role": "group_admin",
                "group": membership.property_group.id if membership.property_group else None,
            }

        return {"role": membership.role}


class UserManagementCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating users through the management API.
    Handles role assignment and property/group membership.
    """
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(
        choices=PropertyUserRole.choices + [('super_user', 'Super User')],
        write_only=True
    )
    property_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    property_group_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    
    # Read-only fields for response
    role_info = serializers.SerializerMethodField(read_only=True)
    date_joined = serializers.DateTimeField(read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'first_name', 'last_name', 'password', 'confirm_password',
            'role', 'property_id', 'property_group_id', 'is_active', 'role_info', 'date_joined'
        ]

    def validate(self, attrs):
        # Password confirmation
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
            
        # Validate password strength
        try:
            validate_password(attrs['password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": e.messages})
        
        # Role and membership validation
        role = attrs['role']
        property_id = attrs.get('property_id')
        property_group_id = attrs.get('property_group_id')
        
        # Validate role assignment permissions
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            from .permissions import CanCreateUserWithRole
            permission = CanCreateUserWithRole()
            if not permission.can_create_role(
                request.user, role, property_id, property_group_id
            ):
                raise serializers.ValidationError(
                    f"You don't have permission to create users with role '{role}'"
                )
        
        # Role-specific validation
        if role == 'super_user':
            if property_id or property_group_id:
                raise serializers.ValidationError(
                    "Super users cannot be assigned to properties or groups."
                )
        elif role == PropertyUserRole.GROUP_ADMIN:
            if not property_group_id:
                raise serializers.ValidationError(
                    "Property group ID is required for group admin role."
                )
            if property_id:
                raise serializers.ValidationError(
                    "Group admins cannot be assigned to specific properties."
                )
        elif role in [PropertyUserRole.PROPERTY_ADMIN, PropertyUserRole.TENANT]:
            if not property_id:
                raise serializers.ValidationError(
                    f"Property ID is required for {role} role."
                )
            if property_group_id:
                raise serializers.ValidationError(
                    f"{role} users should be assigned to properties, not groups."
                )
                
        # Validate property/group existence
        if property_id:
            try:
                Property.objects.get(id=property_id)
            except Property.DoesNotExist:
                raise serializers.ValidationError("Invalid property ID.")
                
        if property_group_id:
            try:
                PropertyGroup.objects.get(id=property_group_id)
            except PropertyGroup.DoesNotExist:
                raise serializers.ValidationError("Invalid property group ID.")
        
        return attrs

    def create(self, validated_data):
        # Remove non-model fields
        password = validated_data.pop('password')
        validated_data.pop('confirm_password')
        role = validated_data.pop('role')
        property_id = validated_data.pop('property_id', None)
        property_group_id = validated_data.pop('property_group_id', None)

        # Flags for staff/superuser
        is_superuser = False
        is_staff = False

        if role == 'super_user':
            is_superuser = True
            is_staff = True
        elif role in [PropertyUserRole.PROPERTY_ADMIN, PropertyUserRole.GROUP_ADMIN]:
            is_staff = True

        # Create user (do not pass is_staff/superuser here)
        user = CustomUser.objects.create_user(
            password=password,
            **validated_data
        )

        # Assign staff/superuser flags explicitly
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.save()

        # Create membership if not superuser
        if role != 'super_user':
            membership_data = {
                'user': user,
                'role': role,
            }
            if property_id:
                membership_data['property'] = Property.objects.get(id=property_id)
            elif property_group_id:
                membership_data['property_group'] = PropertyGroup.objects.get(id=property_group_id)

            UserPropertyMembership.objects.create(**membership_data)

        return user
    
    def get_role_info(self, obj):
        """Get role information for the created user"""
        if obj.is_superuser:
            return {"role": "super_user"}
            
        memberships = obj.property_memberships.all()
        if not memberships.exists():
            return {"role": None}
            
        membership = memberships.first()
        role_info = {"role": membership.role}
        
        if membership.property:
            role_info["property"] = {
                "id": membership.property.id,
                "name": membership.property.name
            }
        elif membership.property_group:
            role_info["property_group"] = {
                "id": membership.property_group.id,
                "name": membership.property_group.name
            }
            
        return role_info


class UserManagementUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating users through the management API.
    """
    password = serializers.CharField(write_only=True, required=False)
    role = serializers.ChoiceField(
        choices=PropertyUserRole.choices + [('super_user', 'Super User')],
        required=False,
        write_only=True
    )
    property_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    property_group_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    
    # Read-only fields
    role_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'first_name', 'last_name', 'password',
            'role', 'property_id', 'property_group_id', 'is_active', 'role_info'
        ]

    def validate(self, attrs):
        # Password validation if provided
        if 'password' in attrs:
            try:
                validate_password(attrs['password'])
            except DjangoValidationError as e:
                raise serializers.ValidationError({"password": e.messages})
        
        # Role validation if provided
        if 'role' in attrs:
            role = attrs['role']
            property_id = attrs.get('property_id')
            property_group_id = attrs.get('property_group_id')
            
            # Check permissions
            request = self.context.get('request')
            if request and hasattr(request, 'user'):
                from .permissions import CanCreateUserWithRole
                permission = CanCreateUserWithRole()
                if not permission.can_create_role(
                    request.user, role, property_id, property_group_id
                ):
                    raise serializers.ValidationError(
                        f"You don't have permission to assign role '{role}'"
                    )
            
            # Role-specific validation (same as create)
            if role == 'super_user':
                if property_id or property_group_id:
                    raise serializers.ValidationError(
                        "Super users cannot be assigned to properties or groups."
                    )
            elif role == PropertyUserRole.GROUP_ADMIN:
                if not property_group_id:
                    raise serializers.ValidationError(
                        "Property group ID is required for group admin role."
                    )
                if property_id:
                    raise serializers.ValidationError(
                        "Group admins cannot be assigned to specific properties."
                    )
            elif role in [PropertyUserRole.PROPERTY_ADMIN, PropertyUserRole.TENANT]:
                if not property_id:
                    raise serializers.ValidationError(
                        f"Property ID is required for {role} role."
                    )
                if property_group_id:
                    raise serializers.ValidationError(
                        f"{role} users should be assigned to properties, not groups."
                    )
                    
        # Validate property/group existence
        if 'property_id' in attrs and attrs['property_id']:
            try:
                Property.objects.get(id=attrs['property_id'])
            except Property.DoesNotExist:
                raise serializers.ValidationError("Invalid property ID.")
                
        if 'property_group_id' in attrs and attrs['property_group_id']:
            try:
                PropertyGroup.objects.get(id=attrs['property_group_id'])
            except PropertyGroup.DoesNotExist:
                raise serializers.ValidationError("Invalid property group ID.")
        
        return attrs

    def update(self, instance, validated_data):
        # Handle password separately
        password = validated_data.pop('password', None)
        role = validated_data.pop('role', None)
        property_id = validated_data.pop('property_id', None)
        property_group_id = validated_data.pop('property_group_id', None)
        
        # Update basic user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Update password if provided
        if password:
            instance.set_password(password)
            
        # Handle role changes
        if role is not None:
            # Update user flags
            if role == 'super_user':
                instance.is_superuser = True
                instance.is_staff = True
                # Remove all memberships for superusers
                instance.property_memberships.all().delete()
            else:
                instance.is_superuser = False
                instance.is_staff = role in [PropertyUserRole.PROPERTY_ADMIN, PropertyUserRole.GROUP_ADMIN]
                
                # Update membership
                instance.property_memberships.all().delete()  # Remove existing memberships
                
                membership_data = {
                    'user': instance,
                    'role': role,
                }
                
                if property_id:
                    membership_data['property'] = Property.objects.get(id=property_id)
                elif property_group_id:
                    membership_data['property_group'] = PropertyGroup.objects.get(id=property_group_id)
                    
                UserPropertyMembership.objects.create(**membership_data)
        
        instance.save()
        return instance
    
    def get_role_info(self, obj):
        """Get role information for the user"""
        if obj.is_superuser:
            return {"role": "super_user"}
            
        memberships = obj.property_memberships.all()
        if not memberships.exists():
            return {"role": None}
            
        membership = memberships.first()
        role_info = {"role": membership.role}
        
        if membership.property:
            role_info["property"] = {
                "id": membership.property.id,
                "name": membership.property.name
            }
        elif membership.property_group:
            role_info["property_group"] = {
                "id": membership.property_group.id,
                "name": membership.property_group.name
            }
            
        return role_info


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for users to update their own profile information.
    Excludes role-related fields and admin-only fields.
    """
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'first_name', 'last_name', 'password'
        ]
        read_only_fields = ['id', 'email']  # Users cannot change their ID or email
    
    def validate_password(self, value):
        """Validate password if provided"""
        if value:
            try:
                validate_password(value)
            except ValidationError as e:
                raise serializers.ValidationError(e.messages)
        return value
    
    def update(self, instance, validated_data):
        """Update user profile with password handling"""
        password = validated_data.pop('password', None)
        
        # Update basic user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Update password if provided
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance


class UserManagementListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing users in management API.
    """
    role_info = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'first_name', 'last_name', 'is_active',
            'is_staff', 'is_superuser', 'date_joined', 'last_login', 'role_info'
        ]

    def get_role_info(self, obj):
        """Get role information for the user"""
        if obj.is_superuser:
            return {"role": "super_user"}
            
        memberships = obj.property_memberships.all()
        if not memberships.exists():
            return {"role": None}
            
        membership = memberships.first()
        role_info = {"role": membership.role}
        
        if membership.property:
            role_info["property"] = {
                "id": membership.property.id,
                "name": membership.property.name,
                "property_group": {
                    "id": membership.property.property_group.id,
                    "name": membership.property.property_group.name
                } if membership.property.property_group else None
            }
        elif membership.property_group:
            role_info["property_group"] = {
                "id": membership.property_group.id,
                "name": membership.property_group.name
            }
            
        return role_info


class UserStatsSerializer(serializers.Serializer):
    """
    Serializer for user statistics data.
    """
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    admin_users = serializers.IntegerField()
    tenants = serializers.IntegerField()
