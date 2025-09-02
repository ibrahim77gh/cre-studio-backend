from djoser.serializers import UserSerializer as BaseUserSerializer, UserCreateSerializer as BaseUserCreateSerializer
from rest_framework import serializers

from property_app.models import PropertyUserRole
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
