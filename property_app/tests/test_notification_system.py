#!/usr/bin/env python
"""
Test script for the notification system.
This script tests the approval status change notifications.
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cre_studio_backend.settings')
django.setup()

from property_app.models import Campaign, ClientNotification, Property, PropertyGroup, UserPropertyMembership, PropertyUserRole
from authentication.models import CustomUser
from property_app.utils import send_approval_status_notification, get_campaign_notification_users

def test_notification_system():
    """Test the notification system for approval status changes."""
    print("🧪 Testing Notification System...")
    
    # Get or create test data
    try:
        # Get a superuser
        superuser = CustomUser.objects.filter(is_superuser=True).first()
        if not superuser:
            print("❌ No superuser found. Please create a superuser first.")
            return
        
        # Get or create a property
        property_obj = Property.objects.first()
        if not property_obj:
            print("❌ No property found. Please create a property first.")
            return
        
        # Get or create a campaign
        campaign = Campaign.objects.filter(property=property_obj).first()
        if not campaign:
            print("❌ No campaign found. Please create a campaign first.")
            return
        
        print(f"✅ Using campaign: {campaign.center}")
        print(f"✅ Using property: {property_obj.name}")
        print(f"✅ Using superuser: {superuser.email}")
        
        # Test 1: Check notification users include superusers
        print("\n📋 Test 1: Checking notification users include superusers...")
        notification_users = get_campaign_notification_users(campaign)
        superuser_included = any(user.is_superuser for user in notification_users)
        print(f"   Superuser included: {'✅' if superuser_included else '❌'}")
        print(f"   Total notification users: {len(notification_users)}")
        
        # Test 2: Test PENDING to ADMIN_APPROVED notification
        print("\n📋 Test 2: Testing PENDING to ADMIN_APPROVED notification...")
        old_status = Campaign.ApprovalStatus.PENDING
        new_status = Campaign.ApprovalStatus.ADMIN_APPROVED
        
        # Count notifications before
        initial_count = ClientNotification.objects.count()
        
        # Send notification
        send_approval_status_notification(campaign, old_status, new_status, superuser)
        
        # Count notifications after
        final_count = ClientNotification.objects.count()
        new_notifications = final_count - initial_count
        
        print(f"   Notifications created: {new_notifications}")
        print(f"   Status: {'✅' if new_notifications > 0 else '❌'}")
        
        # Test 3: Test ADMIN_APPROVED to CLIENT_APPROVED notification
        print("\n📋 Test 3: Testing ADMIN_APPROVED to CLIENT_APPROVED notification...")
        old_status = Campaign.ApprovalStatus.ADMIN_APPROVED
        new_status = Campaign.ApprovalStatus.CLIENT_APPROVED
        
        # Count notifications before
        initial_count = ClientNotification.objects.count()
        
        # Send notification
        send_approval_status_notification(campaign, old_status, new_status, superuser)
        
        # Count notifications after
        final_count = ClientNotification.objects.count()
        new_notifications = final_count - initial_count
        
        print(f"   Notifications created: {new_notifications}")
        print(f"   Status: {'✅' if new_notifications > 0 else '❌'}")
        
        # Test 4: Test FULLY_APPROVED notification
        print("\n📋 Test 4: Testing FULLY_APPROVED notification...")
        old_status = Campaign.ApprovalStatus.CLIENT_APPROVED
        new_status = Campaign.ApprovalStatus.FULLY_APPROVED
        
        # Count notifications before
        initial_count = ClientNotification.objects.count()
        
        # Send notification
        send_approval_status_notification(campaign, old_status, new_status, superuser)
        
        # Count notifications after
        final_count = ClientNotification.objects.count()
        new_notifications = final_count - initial_count
        
        print(f"   Notifications created: {new_notifications}")
        print(f"   Status: {'✅' if new_notifications > 0 else '❌'}")
        
        # Test 5: Check notification types
        print("\n📋 Test 5: Checking notification types...")
        recent_notifications = ClientNotification.objects.order_by('-created_at')[:3]
        
        for i, notification in enumerate(recent_notifications, 1):
            print(f"   Notification {i}: {notification.notification_type} - {notification.title}")
        
        print("\n🎉 Notification system test completed!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_notification_system()
