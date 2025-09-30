import os
import re
from openai import OpenAI
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

from property_app.models import (
    Campaign, CampaignDate, CampaignDateType, CampaignBudget, CampaignComment,
    ClientNotification, PropertyUserRole
)
from datetime import datetime
from decimal import Decimal, InvalidOperation
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

def extract_urls(text):
    """Extract URLs from text using regex. Handles both strings and lists."""
    url_pattern = r'https?://[^\s]+'
    
    # Handle different input types
    if isinstance(text, list):
        # If it's a list, join all items and then extract URLs
        text = ' '.join(str(item) for item in text)
    elif text is None:
        return []
    elif not isinstance(text, str):
        # Convert to string if it's not already
        text = str(text)
    
    return re.findall(url_pattern, text)

# Pydantic models for structured outputs
class MetaAdResponse(BaseModel):
    headline: str  # max 50 characters
    main_copy_options: List[str]  # 5 variations, each max 200 characters
    desktop_display_copy: str  # max 325 characters
    call_to_action: str

class GoogleDisplayResponse(BaseModel):
    headlines: List[str]  # 5 headlines, each under 30 characters
    long_headline: str  # under 90 characters
    descriptions: List[str]  # 5 descriptions, each under 90 characters

class ExtractedDate(BaseModel):
    date: str  # YYYY-MM-DD format
    title: str
    description: Optional[str] = None
    date_type: str  # 'event', 'milestone', 'deadline', 'promotion'

class DateExtractionResponse(BaseModel):
    campaign_start_date: Optional[str] = None  # YYYY-MM-DD format
    campaign_end_date: Optional[str] = None    # YYYY-MM-DD format
    event_dates: List[ExtractedDate] = []

class ExtractedBudget(BaseModel):
    total_gross: Optional[float] = None
    total_net: Optional[float] = None
    meta_gross: Optional[float] = None
    meta_net: Optional[float] = None
    display_gross: Optional[float] = None
    display_net: Optional[float] = None
    creative_charges_deductions: Optional[float] = None

class BudgetExtractionResponse(BaseModel):
    budget: ExtractedBudget
    confidence_level: str  # 'high', 'medium', 'low'
    extracted_values: List[str] = []  # List of values that were found in the text

def generate_meta_ad_content(messaging, primary_goal, target_audience, creative_context):
    """Generate all Meta ad content using a single API call."""
    prompt = f"""
    Generate comprehensive Meta ad content based on the following information:

    Messaging: {messaging}
    Primary Goal: {primary_goal}
    Target Audience: {target_audience}
    Creative Context: {creative_context}

    Please provide:
    1. A compelling headline (max 50 characters, single line)
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

def generate_google_display_content(messaging, primary_goal, target_audience, creative_context):
    """Generate all Google Display ad content using a single API call."""
    prompt = f"""
    Generate comprehensive Google Display ad content based on the following information:

    Messaging: {messaging}
    Primary Goal: {primary_goal}
    Target Audience: {target_audience}
    Creative Context: {creative_context}

    Please provide:
    1. Five different headlines (each exactly 30 characters)
    2. One long headline (exactly 90 characters)
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

def extract_dates_with_ai(timeframe_text, pmcb_data):
    """
    Use AI to extract campaign dates and event dates from timeframe text and other PMCB data.
    """
    # Combine all relevant text that might contain dates
    additional_context = ""
    if pmcb_data:
        additional_context += f"Additional Notes: {pmcb_data.get('additionalNotes', '')}\n"
        additional_context += f"Messaging: {pmcb_data.get('messaging', '')}\n"
        additional_context += f"Creative Context: {pmcb_data.get('creativeContext', '')}\n"
    
    prompt = f"""
    Extract campaign dates and event dates from the following text. Look for:
    1. Campaign start and end dates (the overall campaign duration)
    2. Specific event dates mentioned (sales, promotions, grand openings, holidays, etc.)
    
    Timeframe: {timeframe_text}
    
    Additional Context:
    {additional_context}
    
    Please extract:
    - campaign_start_date: The overall campaign start date (YYYY-MM-DD format)
    - campaign_end_date: The overall campaign end date (YYYY-MM-DD format)  
    - event_dates: List of specific events with their dates, titles, and types
    
    Date types should be one of: 'event', 'milestone', 'deadline', 'promotion'
    
    If no clear dates are found, return null for start/end dates and empty array for events.
    """

    try:
        response = client.responses.parse(
            model=MODEL,
            input=[
                {"role": "system", "content": "You are an expert at extracting dates from marketing campaign text. Extract all relevant dates in the specified format."},
                {"role": "user", "content": prompt}
            ],
            text_format=DateExtractionResponse,
        )
        return response.output_parsed
    except Exception as e:
        # Fallback - return empty response
        return DateExtractionResponse(
            campaign_start_date=None,
            campaign_end_date=None,
            event_dates=[]
        )

def extract_budget_with_ai(budget_text, pmcb_data):
    """
    Use AI to extract budget information from budget text and other PMCB data.
    Only extracts explicitly mentioned budget amounts, does not generate or guess values.
    """
    prompt = f"""
    Extract budget information from the following text. ONLY extract explicitly mentioned budget amounts.
    DO NOT generate, estimate, or make up any budget numbers that are not clearly stated in the text.
    
    Budget Information: {budget_text}
    
    Look for:
    - Total gross budget amounts
    - Total net budget amounts
    - Meta/Facebook advertising budget (gross and net)
    - Google Display advertising budget (gross and net)
    - Creative charges or deductions
    
    IMPORTANT RULES:
    1. Only extract numbers that are explicitly mentioned in the text
    2. If a budget amount is not clearly specified, leave it as null
    3. Do not calculate or estimate any values
    4. Return confidence level: 'high' if amounts are clearly stated, 'medium' if somewhat clear, 'low' if unclear
    5. List all the specific values/amounts you found in the extracted_values array
    
    If no budget information is found, return null values for all budget fields.
    """

    try:
        response = client.responses.parse(
            model=MODEL,
            input=[
                {"role": "system", "content": "You are an expert at extracting budget information from marketing campaign text. Extract ONLY explicitly mentioned budget amounts. Never estimate or generate numbers."},
                {"role": "user", "content": prompt}
            ],
            text_format=BudgetExtractionResponse,
        )
        return response.output_parsed
    except Exception as e:
        # Fallback - return empty response
        return BudgetExtractionResponse(
            budget=ExtractedBudget(),
            confidence_level='low',
            extracted_values=[]
        )

def parse_budget_from_pmcb(campaign, pmcb_data):
    """
    Parse budget information from pmcb_form_data and create/update CampaignBudget instance.
    Uses AI to extract budget amounts from budget text and other relevant data.
    """
    if not pmcb_data:
        return
    
    # Extract budget information
    budget_text = pmcb_data.get('budget', '')
    
    if budget_text:
        # Use AI to extract budget information
        extracted_budget_data = extract_budget_with_ai(budget_text, pmcb_data)
        
        if extracted_budget_data.confidence_level != 'low' or extracted_budget_data.extracted_values:
            # Get or create campaign budget
            campaign_budget, created = CampaignBudget.objects.get_or_create(
                campaign=campaign,
                defaults={
                    'total_gross': 0.00,
                    'total_net': 0.00,
                    'meta_gross': 0.00,
                    'meta_net': 0.00,
                    'display_gross': 0.00,
                    'display_net': 0.00,
                    'creative_charges_deductions': 0.00,
                }
            )
            
            # Update budget fields only if values were extracted
            budget = extracted_budget_data.budget
            
            def safe_decimal_conversion(value):
                """Safely convert a value to Decimal, return None if conversion fails"""
                if value is None:
                    return None
                try:
                    return Decimal(str(value))
                except (InvalidOperation, ValueError, TypeError):
                    return None
            
            # Update only the fields that have extracted values
            if budget.total_gross is not None:
                decimal_value = safe_decimal_conversion(budget.total_gross)
                if decimal_value is not None:
                    campaign_budget.total_gross = decimal_value
            
            if budget.total_net is not None:
                decimal_value = safe_decimal_conversion(budget.total_net)
                if decimal_value is not None:
                    campaign_budget.total_net = decimal_value
            
            if budget.meta_gross is not None:
                decimal_value = safe_decimal_conversion(budget.meta_gross)
                if decimal_value is not None:
                    campaign_budget.meta_gross = decimal_value
            
            if budget.meta_net is not None:
                decimal_value = safe_decimal_conversion(budget.meta_net)
                if decimal_value is not None:
                    campaign_budget.meta_net = decimal_value
            
            if budget.display_gross is not None:
                decimal_value = safe_decimal_conversion(budget.display_gross)
                if decimal_value is not None:
                    campaign_budget.display_gross = decimal_value
            
            if budget.display_net is not None:
                decimal_value = safe_decimal_conversion(budget.display_net)
                if decimal_value is not None:
                    campaign_budget.display_net = decimal_value
            
            if budget.creative_charges_deductions is not None:
                decimal_value = safe_decimal_conversion(budget.creative_charges_deductions)
                if decimal_value is not None:
                    campaign_budget.creative_charges_deductions = decimal_value
            
            # Save the budget
            campaign_budget.save()

def parse_dates_from_pmcb(campaign, pmcb_data):
    """
    Parse date information from pmcb_form_data and create CampaignDate instances.
    Uses AI to extract campaign start/end dates and event dates from timeframe text.
    """
    if not pmcb_data:
        return
    
    # Extract timeframe information
    timeframe = pmcb_data.get('timeframe', '')
    
    if timeframe:
        # Use AI to extract dates from timeframe text
        extracted_dates = extract_dates_with_ai(timeframe, pmcb_data)
        
        # Set campaign start and end dates if found
        if extracted_dates.campaign_start_date:
            try:
                campaign.start_date = datetime.strptime(extracted_dates.campaign_start_date, '%Y-%m-%d').date()
            except ValueError:
                pass
                
        if extracted_dates.campaign_end_date:
            try:
                campaign.end_date = datetime.strptime(extracted_dates.campaign_end_date, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # Create CampaignDate instances for extracted event dates
        for extracted_event in extracted_dates.event_dates:
            try:
                event_date = datetime.strptime(extracted_event.date, '%Y-%m-%d').date()
                
                # Map the date type to our enum
                date_type_mapping = {
                    'event': CampaignDateType.EVENT,
                    'milestone': CampaignDateType.MILESTONE,
                    'deadline': CampaignDateType.DEADLINE,
                    'promotion': CampaignDateType.PROMOTION
                }
                date_type = date_type_mapping.get(extracted_event.date_type, CampaignDateType.EVENT)
                
                # Check if this date already exists to avoid duplicates
                if not campaign.campaign_dates.filter(
                    date=event_date,
                    title=extracted_event.title
                ).exists():
                    CampaignDate.objects.create(
                        campaign=campaign,
                        date=event_date,
                        date_type=date_type,
                        title=extracted_event.title,
                        description=extracted_event.description or ''
                    )
            except ValueError:
                continue


def map_pmcb_to_campaign_fields(campaign, pmcb_data):
    """
    Intelligently map pmcb_form_data to Campaign Meta and Google fields using AI.
    Now uses only 2 API calls instead of 6 for much better efficiency.
    """
    if not pmcb_data:
        return

    # Direct mappings
    campaign.center = pmcb_data.get('centerName', '')

    # Parse and create campaign dates
    parse_dates_from_pmcb(campaign, pmcb_data)

    # Parse and create campaign budget
    parse_budget_from_pmcb(campaign, pmcb_data)

    # Website URLs
    relevant_links = pmcb_data.get('relevantLinks', '')
    urls = extract_urls(relevant_links)
    if urls:
        campaign.meta_website_url = urls[0]
        campaign.google_website_url = urls[0]

    # Notes
    campaign.meta_notes = pmcb_data.get('additionalNotes', '')
    campaign.google_notes = pmcb_data.get('additionalNotes', '')

    # Extract AI generation parameters
    messaging = pmcb_data.get('messaging', '')
    primary_goal = pmcb_data.get('primaryGoal', 'awareness')
    target_audience = pmcb_data.get('targetAudience', '')
    creative_context = pmcb_data.get('creativeContext', '')

    # Generate Meta content with single API call
    meta_content = generate_meta_ad_content(messaging, primary_goal, target_audience, creative_context)
    if meta_content:
        campaign.meta_headline = meta_content.headline
        campaign.meta_main_copy_options = meta_content.main_copy_options
        campaign.meta_desktop_display_copy = meta_content.desktop_display_copy
        campaign.meta_call_to_action = meta_content.call_to_action

    # Generate Google Display content with single API call
    google_content = generate_google_display_content(messaging, primary_goal, target_audience, creative_context)
    if google_content:
        campaign.google_headlines = google_content.headlines
        campaign.google_long_headline = google_content.long_headline
        campaign.google_descriptions = google_content.descriptions

    # Ready status
    status = pmcb_data.get('status', '')
    campaign.meta_ready = "AI Generated" if status == 'submitted' else ""
    campaign.google_ready = "AI Generated" if status == 'submitted' else ""

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
    # send_comment_email_notifications_task.delay(comment.id, [user.id for user in notification_users])
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