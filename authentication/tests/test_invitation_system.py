"""
Test cases for the invitation email system
"""
from django.test import TestCase
from django.core import mail
from django.utils import timezone
from datetime import datetime, timedelta
from authentication.models import CustomUser
from authentication.email import InvitationEmail
from authentication.serializers import UserManagementCreateSerializer
from property_app.models import Property, PropertyGroup, PropertyUserRole, UserPropertyMembership


class InvitationEmailSystemTest(TestCase):
    """Test the invitation email system functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Create a superuser for testing
        self.superuser = CustomUser.objects.create_superuser(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User'
        )
        
        # Create test property and group
        self.property_group = PropertyGroup.objects.create(
            name='Test Property Group'
        )
        
        self.property = Property.objects.create(
            name='Test Property',
            property_group=self.property_group
        )
    
    def test_user_creation_sends_invitation_email(self):
        """Test that creating a user sends an invitation email"""
        # Clear mail outbox
        mail.outbox = []
        
        # Create user data
        user_data = {
            'email': 'newuser@test.com',
            'password': 'testpass123',
            'confirm_password': 'testpass123',
            'first_name': 'New',
            'last_name': 'User',
            'role': PropertyUserRole.TENANT,
            'property_id': self.property.id
        }
        
        # Create serializer and save
        serializer = UserManagementCreateSerializer(
            data=user_data,
            context={'request': type('obj', (object,), {'user': self.superuser})()}
        )
        
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        
        # Check that user is created as inactive
        self.assertFalse(user.is_active)
        self.assertTrue(user.invitation_sent)
        self.assertFalse(user.invitation_accepted)
        self.assertIsNotNone(user.invitation_token)
        self.assertIsNotNone(user.invitation_sent_at)
        
        # Check that invitation email was sent
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn('invited to join', email.subject)
        self.assertEqual(email.to, ['newuser@test.com'])
        self.assertIn('Accept Invitation', email.body)
    
    def test_invitation_email_content(self):
        """Test that invitation email contains correct content"""
        # Create a user
        user = CustomUser.objects.create_user(
            email='testuser@test.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        # Create membership
        UserPropertyMembership.objects.create(
            user=user,
            property=self.property,
            role=PropertyUserRole.TENANT
        )
        
        # Prepare role info
        role_info = {
            'role_label': 'Tenant',
            'property_name': self.property.name,
            'property_group_name': self.property_group.name
        }
        
        # Send invitation email
        invitation_email = InvitationEmail(user, role_info)
        invitation_email.send()
        
        # Check email content
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        
        # Check that email contains role and property information
        self.assertIn('Tenant', email.body)
        self.assertIn(self.property.name, email.body)
        self.assertIn(self.property_group.name, email.body)
    
    def test_invitation_token_generation(self):
        """Test that invitation tokens are generated correctly"""
        user = CustomUser.objects.create_user(
            email='tokenuser@test.com',
            password='testpass123',
            first_name='Token',
            last_name='User'
        )
        
        invitation_email = InvitationEmail(user)
        token1 = invitation_email.generate_invitation_token()
        token2 = invitation_email.generate_invitation_token()
        
        # Tokens should be different each time
        self.assertNotEqual(token1, token2)
        
        # Tokens should be stored in user model
        self.assertIsNotNone(user.invitation_token)
        self.assertTrue(user.invitation_sent)
    
    def test_invitation_expiry(self):
        """Test that invitations expire after 7 days"""
        user = CustomUser.objects.create_user(
            email='expiryuser@test.com',
            password='testpass123',
            first_name='Expiry',
            last_name='User'
        )
        
        # Set invitation sent time to 8 days ago
        user.invitation_sent_at = timezone.now() - timedelta(days=8)
        user.invitation_token = 'test_token'
        user.save()
        
        # Try to accept expired invitation
        from authentication.views import AcceptInvitationView
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get(f'/api/auth/accept-invitation/{user.invitation_token}/')
        view = AcceptInvitationView()
        
        response = view.get(request, user.invitation_token)
        
        # Should return error for expired invitation
        self.assertEqual(response.status_code, 400)
        self.assertIn('expired', response.data['error'])
    
    def test_invitation_already_accepted(self):
        """Test that already accepted invitations cannot be accepted again"""
        user = CustomUser.objects.create_user(
            email='accepteduser@test.com',
            password='testpass123',
            first_name='Accepted',
            last_name='User'
        )
        
        # Mark invitation as already accepted
        user.invitation_accepted = True
        user.invitation_token = 'test_token'
        user.save()
        
        # Try to accept already accepted invitation
        from authentication.views import AcceptInvitationView
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get(f'/api/auth/accept-invitation/{user.invitation_token}/')
        view = AcceptInvitationView()
        
        response = view.get(request, user.invitation_token)
        
        # Should return error for already accepted invitation
        self.assertEqual(response.status_code, 400)
        self.assertIn('already been accepted', response.data['error'])
    
    def test_successful_invitation_acceptance(self):
        """Test successful invitation acceptance"""
        user = CustomUser.objects.create_user(
            email='successuser@test.com',
            password='testpass123',
            first_name='Success',
            last_name='User'
        )
        
        # Set up invitation
        user.invitation_token = 'test_token'
        user.invitation_sent_at = timezone.now()
        user.save()
        
        # Accept invitation
        from authentication.views import AcceptInvitationView
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get(f'/api/auth/accept-invitation/{user.invitation_token}/')
        view = AcceptInvitationView()
        
        response = view.get(request, user.invitation_token)
        
        # Should be successful
        self.assertEqual(response.status_code, 200)
        self.assertIn('accepted successfully', response.data['message'])
        
        # User should be activated
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.invitation_accepted)
        self.assertIsNotNone(user.invitation_accepted_at)
