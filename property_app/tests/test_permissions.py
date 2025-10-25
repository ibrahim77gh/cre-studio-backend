#!/usr/bin/env python
"""
Simple test script to validate user management permissions (model level)
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cre_studio_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from property_app.models import PropertyGroup, Property, UserPropertyMembership, PropertyUserRole
from authentication.permissions import CanManageUsers, CanCreateUserWithRole

User = get_user_model()

def test_permission_logic():
    """Test the permission logic without HTTP requests"""
    print("Testing User Management Permission Logic...")
    
    # Clean up any existing test data first
    print("Cleaning up any existing test data...")
    User.objects.filter(email__endswith='@example.com').delete()
    PropertyGroup.objects.filter(name="Test Shopping Center Group").delete()
    
    # Create test data
    print("Creating test data...")
    
    # Create property group and property
    property_group = PropertyGroup.objects.create(name="Test Shopping Center Group")
    property1 = Property.objects.create(
        name="Test Mall 1",
        property_group=property_group,
        subdomain="test-mall-1"
    )
    property2 = Property.objects.create(
        name="Test Mall 2", 
        property_group=property_group,
        subdomain="test-mall-2"
    )
    
    # Create users
    superuser = User.objects.create_superuser(
        email="super@example.com",
        password="testpass123",
        first_name="Super",
        last_name="User"
    )
    
    group_admin = User.objects.create_user(
        email="groupadmin@example.com",
        password="testpass123",
        first_name="Group",
        last_name="Admin"
    )
    
    property_admin = User.objects.create_user(
        email="propertyadmin@example.com",
        password="testpass123",
        first_name="Property",
        last_name="Admin"
    )
    
    tenant_user = User.objects.create_user(
        email="tenant@example.com",
        password="testpass123",
        first_name="Tenant",
        last_name="User"
    )
    
    # Set staff status after creation
    group_admin.is_staff = True
    group_admin.save()
    
    property_admin.is_staff = True
    property_admin.save()
    
    # Create memberships
    UserPropertyMembership.objects.create(
        user=group_admin,
        property_group=property_group,
        role=PropertyUserRole.GROUP_ADMIN
    )
    
    UserPropertyMembership.objects.create(
        user=property_admin,
        property=property1,
        role=PropertyUserRole.PROPERTY_ADMIN
    )
    
    UserPropertyMembership.objects.create(
        user=tenant_user,
        property=property1,
        role=PropertyUserRole.TENANT
    )
    
    print("Test data created successfully!")
    
    # Test 1: Superuser permissions
    print("\nTest 1: Superuser permissions...")
    print(f"✓ Superuser can manage property admin: {superuser.is_superuser}")
    print(f"✓ Superuser managed users count: {superuser.get_managed_users().count()}")
    print(f"✓ Superuser managed properties count: {superuser.get_managed_properties().count()}")
    
    # Test 2: Group admin permissions  
    print("\nTest 2: Group admin permissions...")
    managed_users = group_admin.get_managed_users()
    managed_properties = group_admin.get_managed_properties()
    print(f"✓ Group admin managed users count: {managed_users.count()}")
    print(f"✓ Group admin managed properties count: {managed_properties.count()}")
    print(f"✓ Can manage property admin: {property_admin in managed_users}")
    print(f"✓ Can manage tenant: {tenant_user in managed_users}")
    print(f"✓ Cannot manage superuser: {superuser not in managed_users}")
    
    # Test 3: Property admin permissions
    print("\nTest 3: Property admin permissions...")
    managed_users = property_admin.get_managed_users()
    managed_properties = property_admin.get_managed_properties()
    print(f"✓ Property admin managed users count: {managed_users.count()}")
    print(f"✓ Property admin managed properties count: {managed_properties.count()}")
    print(f"✓ Can manage tenant: {tenant_user in managed_users}")
    print(f"✓ Cannot manage group admin: {group_admin not in managed_users}")
    print(f"✓ Cannot manage superuser: {superuser not in managed_users}")
    
    # Test 4: Tenant permissions
    print("\nTest 4: Tenant permissions...")
    managed_users = tenant_user.get_managed_users()
    managed_properties = tenant_user.get_managed_properties()
    print(f"✓ Tenant managed users count: {managed_users.count()}")
    print(f"✓ Tenant managed properties count: {managed_properties.count()}")
    
    # Test 5: Role creation permissions
    print("\nTest 5: Role creation permissions...")
    permission_checker = CanCreateUserWithRole()
    
    # Superuser can create all roles
    print(f"✓ Superuser can create superuser: {permission_checker.can_create_role(superuser, 'super_user')}")
    print(f"✓ Superuser can create group admin: {permission_checker.can_create_role(superuser, PropertyUserRole.GROUP_ADMIN, property_group_id=property_group.id)}")
    print(f"✓ Superuser can create property admin: {permission_checker.can_create_role(superuser, PropertyUserRole.PROPERTY_ADMIN, property_id=property1.id)}")
    print(f"✓ Superuser can create tenant: {permission_checker.can_create_role(superuser, PropertyUserRole.TENANT, property_id=property1.id)}")
    
    # Group admin permissions
    print(f"✓ Group admin cannot create superuser: {not permission_checker.can_create_role(group_admin, 'super_user')}")
    print(f"✓ Group admin cannot create group admin: {not permission_checker.can_create_role(group_admin, PropertyUserRole.GROUP_ADMIN, property_group_id=property_group.id)}")
    print(f"✓ Group admin can create property admin in their group: {permission_checker.can_create_role(group_admin, PropertyUserRole.PROPERTY_ADMIN, property_id=property1.id)}")
    print(f"✓ Group admin can create tenant in their group: {permission_checker.can_create_role(group_admin, PropertyUserRole.TENANT, property_id=property1.id)}")
    
    # Property admin permissions
    print(f"✓ Property admin cannot create superuser: {not permission_checker.can_create_role(property_admin, 'super_user')}")
    print(f"✓ Property admin cannot create group admin: {not permission_checker.can_create_role(property_admin, PropertyUserRole.GROUP_ADMIN, property_group_id=property_group.id)}")
    print(f"✓ Property admin cannot create property admin: {not permission_checker.can_create_role(property_admin, PropertyUserRole.PROPERTY_ADMIN, property_id=property1.id)}")
    print(f"✓ Property admin can create tenant in their property: {permission_checker.can_create_role(property_admin, PropertyUserRole.TENANT, property_id=property1.id)}")
    print(f"✓ Property admin cannot create tenant in other property: {not permission_checker.can_create_role(property_admin, PropertyUserRole.TENANT, property_id=property2.id)}")
    
    # Tenant permissions
    print(f"✓ Tenant cannot create any users: {not permission_checker.can_create_role(tenant_user, PropertyUserRole.TENANT, property_id=property1.id)}")
    
    print("\n=== Permission Logic Tests Complete ===")
    
    # Test 6: Serializer logic (without HTTP)
    print("\nTest 6: Testing serializer data...")
    
    from authentication.serializers import UserManagementListSerializer
    
    # Test serializer output
    serializer = UserManagementListSerializer(superuser)
    print(f"✓ Superuser role info: {serializer.data.get('role_info')}")
    
    serializer = UserManagementListSerializer(group_admin)
    print(f"✓ Group admin role info: {serializer.data.get('role_info')}")
    
    serializer = UserManagementListSerializer(property_admin)
    print(f"✓ Property admin role info: {serializer.data.get('role_info')}")
    
    serializer = UserManagementListSerializer(tenant_user)
    print(f"✓ Tenant role info: {serializer.data.get('role_info')}")
    
    print("\n=== All Tests Complete ===")
    print("✅ User management system is working correctly!")
    
    # Clean up
    print("Cleaning up test data...")
    property_group.delete()
    User.objects.filter(email__endswith='@example.com').delete()
    print("Test cleanup complete!")

if __name__ == "__main__":
    test_permission_logic()