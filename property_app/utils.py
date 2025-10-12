import os
import re
from openai import OpenAI
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

from property_app.models import (
    Campaign, CampaignComment,
    ClientNotification, PropertyUserRole
)
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from celery import shared_task


load_dotenv()  # Load environment variables from .env file

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Use GPT-5-nano for better structured output
MODEL = "gpt-5-nano"

# Pydantic models for structured outputs
class MetaAdResponse(BaseModel):
    headline: List[str]  # 5 headlines, each max 50 characters
    main_copy_options: List[str]  # 5 variations, each max 200 characters
    desktop_display_copy: str  # max 325 characters
    call_to_action: str

class GoogleDisplayResponse(BaseModel):
    headlines: List[str]  # 5 headlines, each under 30 characters
    long_headline: List[str]  # 3 long headlines, each under 90 characters
    descriptions: List[str]  # 5 descriptions, each under 90 characters


def generate_meta_ad_content(messaging, primary_goal, target_audience, campaign_name):
    """Generate all Meta ad content using a single API call."""
    prompt = f"""
    Generate comprehensive Meta ad content based on the following information:

    Messaging: {messaging}
    Primary Goal: {primary_goal}
    Target Audience: {target_audience}
    Campaign Name: {campaign_name}

    Please provide:
    1. 5 different compelling headline (max 50 characters, single line)
    2. Five different main copy variations (each max 200 characters, 2-3 lines)
    3. Desktop display copy (max 325 characters)
    4. An appropriate call-to-action

    IMPORTANT: Each text option should utilize as much of the character limit as possible while remaining engaging and on-brand. All content should be optimized for Meta's advertising platform.
    """

    try:
        response = client.responses.parse(
            model=MODEL,
            input=[
                {"role": "system", "content": "You are an expert Meta ad copywriter. Generate comprehensive ad content that drives engagement and conversions."},
                {"role": "user", "content": prompt}
            ],
            text_format=MetaAdResponse,
        )
        return response.output_parsed
    except Exception as e:
        # Return None if generation fails
        return None

def generate_google_display_content(messaging, primary_goal, target_audience, campaign_name):
    """Generate all Google Display ad content using a single API call."""
    prompt = f"""
    Generate comprehensive Google Display ad content based on the following information:

    Messaging: {messaging}
    Primary Goal: {primary_goal}
    Target Audience: {target_audience}
    Campaign Name: {campaign_name}

    Please provide:
    1. Five different headlines (each exactly 30 characters)
    2. Three long headlines (exactly 90 characters)
    3. Five different descriptions (each exactly 90 characters)

    CRITICAL REQUIREMENTS:
    - Each text option should utilize the full character limit as much as possible
    - NO exclamation marks are allowed in any Google content
    - All content should be optimized for Google Display campaigns and drive the specified goal
    """

    try:
        response = client.responses.parse(
            model=MODEL,
            input=[
                {"role": "system", "content": "You are an expert Google Ads copywriter. Generate comprehensive ad content optimized for Google Display campaigns."},
                {"role": "user", "content": prompt}
            ],
            text_format=GoogleDisplayResponse,
        )
        return response.output_parsed
    except Exception as e:
        # Return None if generation fails
        return None


def map_pmcb_to_campaign_fields(campaign, pmcb_data):
    """
    Intelligently map pmcb_form_data to Campaign Meta and Google fields using AI.
    Now uses only 2 API calls instead of 6 for much better efficiency.
    """
    if not pmcb_data:
        return

    # Extract AI generation parameters
    campaign_name = pmcb_data.get('keyEvent', '')
    messaging = pmcb_data.get('messaging', '')
    primary_goal = pmcb_data.get('primaryGoal', 'awareness')
    target_audience = pmcb_data.get('targetAudience', '')
    creative_context = pmcb_data.get('creativeContext', '')

    # Generate Meta content with single API call
    meta_content = generate_meta_ad_content(messaging, primary_goal, target_audience, campaign_name)
    if meta_content:
        campaign.meta_headline = meta_content.headline
        campaign.meta_main_copy_options = meta_content.main_copy_options
        campaign.meta_desktop_display_copy = meta_content.desktop_display_copy
        campaign.meta_call_to_action = meta_content.call_to_action

    # Generate Google Display content with single API call
    google_content = generate_google_display_content(messaging, primary_goal, target_audience, campaign_name)
    if google_content:
        campaign.google_headlines = google_content.headlines
        campaign.google_long_headline = google_content.long_headline
        campaign.google_descriptions = google_content.descriptions

    # Save the campaign
    campaign.save()


def get_campaign_notification_users(campaign):
    """
    Get all users who should receive notifications for a campaign.
    This includes:
    - The campaign creator (tenant)
    - Property admins for the campaign's property
    - Group admins for the campaign's property group
    """
    User = get_user_model()
    notification_users = set()
    
    # Add campaign creator
    notification_users.add(campaign.user)
    
    # Add property admins
    property_admins = User.objects.filter(
        property_memberships__property=campaign.property,
        property_memberships__role=PropertyUserRole.PROPERTY_ADMIN
    )
    notification_users.update(property_admins)
    
    # Add group admins
    group_admins = User.objects.filter(
        property_memberships__property_group=campaign.property.property_group,
        property_memberships__role=PropertyUserRole.GROUP_ADMIN
    )
    notification_users.update(group_admins)
    
    return list(notification_users)


def send_comment_notifications(comment):
    """
    Send notifications to relevant users when a comment is created.
    """
    campaign = comment.campaign
    comment_author = comment.user
    
    # Get users who should be notified (excluding the comment author)
    notification_users = get_campaign_notification_users(campaign)
    notification_users = [user for user in notification_users if user != comment_author]
    
    # Determine notification type and content
    if comment.is_reply:
        notification_type = ClientNotification.NotificationType.COMMENT_REPLY
        title = f"New Reply on Campaign {campaign.pk}"
        message = f"{comment_author.email} replied to a comment on campaign {campaign.center or campaign.pk}"
    else:
        notification_type = ClientNotification.NotificationType.COMMENT
        title = f"New Comment on Campaign {campaign.pk}"
        message = f"{comment_author.email} commented on campaign {campaign.center or campaign.pk}"
    
    # Create notifications for each user
    notifications_to_create = []
    for user in notification_users:
        notification = ClientNotification(
            user=user,
            campaign=campaign,
            comment=comment,
            notification_type=notification_type,
            title=title,
            message=message
        )
        notifications_to_create.append(notification)
    
    # Bulk create notifications
    ClientNotification.objects.bulk_create(notifications_to_create)
    
    # Send email notifications asynchronously
    from .tasks import send_comment_email_notifications_task
    send_comment_email_notifications_task.delay(comment.id, [user.id for user in notification_users])
    print(f"Sent email notifications for comment {comment.id} to {len(notification_users)} users")


@shared_task
def send_comment_email_notifications(comment_id, notification_user_ids):
    """
    Send email notifications for new comments as a Celery task.
    """
    try:
        # Get the comment and users from the database
        comment = CampaignComment.objects.select_related('campaign', 'user', 'parent_comment').get(id=comment_id)
        User = get_user_model()
        notification_users = User.objects.filter(id__in=notification_user_ids)
        
        campaign = comment.campaign
        comment_author = comment.user
        
        # Prepare email context
        context = {
            'campaign': campaign,
            'comment': comment,
            'comment_author': comment_author,
            'site_name': getattr(settings, 'SITE_NAME', 'Retail Studio'),
            'is_reply': comment.is_reply,
            'parent_comment': comment.parent_comment if comment.is_reply else None,
        }
        
        # Determine email template and subject
        if comment.is_reply:
            subject = f"New Reply on Campaign {campaign.center or campaign.pk}"
            template_name = 'email/comment_reply_notification.html'
        else:
            subject = f"New Comment on Campaign {campaign.center or campaign.pk}"
            template_name = 'email/comment_notification.html'
        
        # Send emails to each user
        for user in notification_users:
            try:
                # Add user-specific context
                context['recipient'] = user
                
                # Render email content
                html_message = render_to_string(template_name, context)
                plain_message = strip_tags(html_message)
                
                # Send email
                send_mail(
                    subject=subject,
                    message=plain_message,
                    html_message=html_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except Exception as e:
                # Log error but don't fail the entire task
                print(f"Failed to send email notification to {user.email}: {e}")
                
    except CampaignComment.DoesNotExist:
        print(f"Comment with id {comment_id} not found")
    except Exception as e:
        print(f"Error in send_comment_email_notifications task: {e}")


def send_campaign_update_notification(campaign, update_type, updated_by):
    """
    Send notifications when a campaign is updated.
    """
    notification_users = get_campaign_notification_users(campaign)
    notification_users = [user for user in notification_users if user != updated_by]
    
    title = f"Campaign {campaign.pk} Updated"
    message = f"Campaign {campaign.center or campaign.pk} has been updated by {updated_by.email}"
    
    notifications_to_create = []
    for user in notification_users:
        notification = ClientNotification(
            user=user,
            campaign=campaign,
            notification_type=ClientNotification.NotificationType.CAMPAIGN_UPDATE,
            title=title,
            message=message
        )
        notifications_to_create.append(notification)
    
    ClientNotification.objects.bulk_create(notifications_to_create)


@shared_task
def send_campaign_update_email_notifications(campaign_id, updated_by_id, update_type):
    """
    Send email notifications for campaign updates as a Celery task.
    """
    try:
        User = get_user_model()
        
        campaign = Campaign.objects.select_related('property', 'property__property_group').get(id=campaign_id)
        updated_by = User.objects.get(id=updated_by_id)
        
        notification_users = get_campaign_notification_users(campaign)
        notification_users = [user for user in notification_users if user != updated_by]
        
        # Prepare email context
        context = {
            'campaign': campaign,
            'updated_by': updated_by,
            'update_type': update_type,
            'site_name': getattr(settings, 'SITE_NAME', 'CRE Studio'),
        }
        
        subject = f"Campaign {campaign.center or campaign.pk} Updated"
        template_name = 'email/campaign_update_notification.html'
        
        # Send emails to each user
        for user in notification_users:
            try:
                context['recipient'] = user
                
                html_message = render_to_string(template_name, context)
                plain_message = strip_tags(html_message)
                
                send_mail(
                    subject=subject,
                    message=plain_message,
                    html_message=html_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Failed to send campaign update email to {user.email}: {e}")
                
    except (Campaign.DoesNotExist, User.DoesNotExist) as e:
        print(f"Campaign or User not found: {e}")
    except Exception as e:
        print(f"Error in send_campaign_update_email_notifications task: {e}")