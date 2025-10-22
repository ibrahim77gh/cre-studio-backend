from djoser.email import ActivationEmail, ConfirmationEmail, PasswordResetEmail, PasswordChangedConfirmationEmail
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import secrets
import hashlib
from datetime import datetime, timedelta

class CustomActivationEmail(ActivationEmail):
    template_name = "email/activation.html"

    def get_context_data(self):
        context = super().get_context_data()
        context['site_name'] = settings.SITE_NAME
        return context

class CustomConfirmationEmail(ConfirmationEmail):
    template_name = "email/confirmation.html"

    def get_context_data(self):
        context = super().get_context_data()
        context['site_name'] = settings.SITE_NAME
        return context

class CustomPasswordResetEmail(PasswordResetEmail):
    template_name = "email/password_reset.html"

    def get_context_data(self):
        context = super().get_context_data()
        context['site_name'] = settings.SITE_NAME
        return context

class InvitationEmail:
    """
    Custom invitation email class for sending user invitations
    """
    template_name = "email/invitation.html"
    
    def __init__(self, user, role_info=None):
        self.user = user
        self.role_info = role_info
        self.site_name = getattr(settings, 'SITE_NAME', 'CRE Studio')
        self.site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000/')
    
    def generate_invitation_token(self):
        """Generate a secure invitation token"""
        # Create a unique token based on user email and timestamp
        timestamp = str(int(datetime.now().timestamp()))
        random_string = secrets.token_urlsafe(32)
        token_data = f"{self.user.email}:{timestamp}:{random_string}"
        token = hashlib.sha256(token_data.encode()).hexdigest()
        return token
    
    def get_context_data(self):
        """Get context data for the email template"""
        invitation_token = self.generate_invitation_token()
        
        # Store the token in the user model
        self.user.invitation_token = invitation_token
        self.user.invitation_sent = True
        self.user.invitation_sent_at = datetime.now()
        self.user.save()
        
        # Create the invitation URL
        invitation_url = f"{self.site_url}api/auth/accept-invitation/{invitation_token}/"
        
        return {
            'user': self.user,
            'site_name': self.site_name,
            'url': invitation_url,
            'role_info': self.role_info,
        }
    
    def send(self):
        """Send the invitation email"""
        context = self.get_context_data()
        
        # Render the email template
        html_content = render_to_string(self.template_name, context)
        text_content = strip_tags(html_content)
        
        # Create the email
        subject = f"You're invited to join {self.site_name}"
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
        
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[self.user.email]
        )
        msg.attach_alternative(html_content, "text/html")
        
        # Send the email
        msg.send()
        
        return True

class CustomPasswordChangedConfirmationEmail(PasswordChangedConfirmationEmail):
    template_name = "email/password_changed_confirmation.html"

    def get_context_data(self):
        context = super().get_context_data()
        context['site_name'] = settings.SITE_NAME
        return context
