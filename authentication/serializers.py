from djoser.serializers import UserSerializer as BaseUserSerializer, UserCreateSerializer as BaseUserCreateSerializer
from rest_framework import serializers
from .models import CustomUser
from django.contrib.auth.models import Group


class UserCreateSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        fields = ['id', 'password',
                  'email', 'first_name', 'last_name']
        
        def create(self, validated_data):
            # Create user first
            user = super().create(validated_data)
            # Get or create client_user group
            client_group, _ = Group.objects.get_or_create(name="client_user")
            # Assign the group
            user.groups.add(client_group)
            return user

class UserSerializer(BaseUserSerializer):
    class Meta(BaseUserSerializer.Meta):
        fields = ['id', 'email', 'first_name', 'last_name', 'is_staff']


class UserSerializer(serializers.ModelSerializer):
    groups = serializers.SerializerMethodField()
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'password', 'is_active', 'is_staff', 'is_superuser', 'groups']
        extra_kwargs = {'password': {'write_only': True}}

    def get_groups(self, obj):
        """
        Returns a list of group names for the user object.
        """
        return [group.name for group in obj.groups.all()]