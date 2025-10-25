#!/usr/bin/env python
"""
Simple test script to validate user management APIs
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cre_studio_backend.settings')
django.setup()

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from property_app.models import PropertyGroup, Property, UserPropertyMembership, PropertyUserRole

User = get_user_model()

def test_user_management_permissions():
    """Test the user management permission system"""
    print("Testing User Management APIs...")
    
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
    
    # Test API endpoints
    client = APIClient()
    
    # Test 1: Superuser can access user management endpoints
    print("\nTest 1: Superuser access...")
    client.force_authenticate(user=superuser)
    response = client.get('/api/auth/user-management/')
    print(f"Superuser list users: {response.status_code}")
    
    response = client.get('/api/auth/user-management/my_manageable_scopes/')
    print(f"Superuser manageable scopes: {response.status_code}")
    if response.status_code == 200:
        print(f"Can manage all: {response.data.get('can_manage_all')}")
    
    # Test 2: Group admin can access user management
    print("\nTest 2: Group admin access...")
    client.force_authenticate(user=group_admin)
    response = client.get('/api/auth/user-management/')
    print(f"Group admin list users: {response.status_code}")
    
    response = client.get('/api/auth/user-management/my_manageable_scopes/')
    print(f"Group admin manageable scopes: {response.status_code}")
    if response.status_code == 200:
        print(f"Can manage all: {response.data.get('can_manage_all')}")
        print(f"Manageable properties: {len(response.data.get('properties', []))}")
    
    # Test 3: Property admin can access user management
    print("\nTest 3: Property admin access...")
    client.force_authenticate(user=property_admin)
    response = client.get('/api/auth/user-management/')
    print(f"Property admin list users: {response.status_code}")
    
    response = client.get('/api/auth/user-management/my_manageable_scopes/')
    print(f"Property admin manageable scopes: {response.status_code}")
    if response.status_code == 200:
        print(f"Can manage all: {response.data.get('can_manage_all')}")
        print(f"Manageable properties: {len(response.data.get('properties', []))}")
    
    # Test 4: Tenant cannot access user management
    print("\nTest 4: Tenant access (should be denied)...")
    client.force_authenticate(user=tenant_user)
    response = client.get('/api/auth/user-management/')
    print(f"Tenant list users: {response.status_code}")
    
    # Test 5: Create user as group admin
    print("\nTest 5: Create user as group admin...")
    client.force_authenticate(user=group_admin)
    
    new_user_data = {
        'email': 'newproperty@example.com',
        'password': 'testpass123',
        'confirm_password': 'testpass123',
        'first_name': 'New',
        'last_name': 'PropertyAdmin',
        'role': PropertyUserRole.PROPERTY_ADMIN,
        'property_id': property2.id
    }
    
    response = client.post('/api/auth/user-management/', new_user_data, format='json')
    print(f"Create property admin: {response.status_code}")
    if response.status_code != 201:
        print(f"Error: {response.data}")
    else:
        print(f"Created user: {response.data.get('email')}")
    
    # Test 6: Try to create superuser as group admin (should fail)
    print("\nTest 6: Try to create superuser as group admin (should fail)...")
    superuser_data = {
        'email': 'newsuperuser@example.com',
        'password': 'testpass123',
        'confirm_password': 'testpass123',
        'first_name': 'New',
        'last_name': 'SuperUser',
        'role': 'super_user'
    }
    
    response = client.post('/api/auth/user-management/', superuser_data, format='json')
    print(f"Create superuser (should fail): {response.status_code}")
    if response.status_code != 201:
        print("✓ Correctly blocked unauthorized superuser creation")
    
    print("\n=== User Management API Tests Complete ===")
    
    # Clean up
    print("Cleaning up test data...")
    property_group.delete()
    User.objects.filter(email__endswith='@example.com').delete()
    print("Test cleanup complete!")

if __name__ == "__main__":
    test_user_management_permissions()