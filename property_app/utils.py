import os
import re
from openai import OpenAI
from pydantic import BaseModel
from typing import List, Optional
import json
from dotenv import load_dotenv

from property_app.models import CampaignDate, CampaignDateType
from datetime import datetime
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
    headline: str  # max 30 characters
    main_copy_options: List[str]  # 4 variations, each under 125 characters
    desktop_display_copy: str  # under 300 characters
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

def generate_meta_ad_content(messaging, primary_goal, target_audience, creative_context):
    """Generate all Meta ad content using a single API call."""
    prompt = f"""
    Generate comprehensive Meta ad content based on the following information:

    Messaging: {messaging}
    Primary Goal: {primary_goal}
    Target Audience: {target_audience}
    Creative Context: {creative_context}

    Please provide:
    1. A compelling headline (max 30 characters)
    2. Four different main copy variations (each under 125 characters)
    3. Desktop display copy (under 300 characters)
    4. An appropriate call-to-action

    All content should be engaging, on-brand, and optimized for Meta's advertising platform.
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
        # Fallback values
        return MetaAdResponse(
            headline=f"Exciting {primary_goal.title()}!",
            main_copy_options=[
                f"Discover amazing {primary_goal} opportunities!",
                f"Join us for incredible experiences!",
                f"Don't miss out on great deals!",
                f"Experience the best we have to offer!"
            ],
            desktop_display_copy="Explore our latest offerings and discover something special!",
            call_to_action=get_call_to_action(primary_goal)
        )

def generate_google_display_content(messaging, primary_goal, target_audience, creative_context):
    """Generate all Google Display ad content using a single API call."""
    prompt = f"""
    Generate comprehensive Google Display ad content based on the following information:

    Messaging: {messaging}
    Primary Goal: {primary_goal}
    Target Audience: {target_audience}
    Creative Context: {creative_context}

    Please provide:
    1. Five different short headlines (each under 30 characters)
    2. One long headline (under 90 characters)
    3. Five different descriptions (each under 90 characters)

    All content should be optimized for Google Display campaigns and drive the specified goal.
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
        # Fallback values
        return GoogleDisplayResponse(
            headlines=[
                f"Great {primary_goal.title()}",
                "Discover Now",
                "Join Today",
                "Learn More",
                "Get Started"
            ],
            long_headline="Discover Amazing Opportunities and Experiences",
            descriptions=[
                f"Perfect for {target_audience[:20]}...",
                "Experience the best in our offerings",
                "Join thousands of satisfied customers",
                "Quality you can trust and depend on",
                "Start your journey with us today"
            ]
        )

def get_call_to_action(primary_goal):
    """Determine call to action based on primary goal."""
    cta_map = {
        'awareness': 'Learn More',
        'consideration': 'Shop Now',
        'conversion': 'Sign Up',
        'retention': 'Contact Us'
    }
    return cta_map.get(primary_goal.lower(), 'Learn More')

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
    campaign.meta_headline = meta_content.headline
    campaign.meta_main_copy_options = meta_content.main_copy_options
    campaign.meta_desktop_display_copy = meta_content.desktop_display_copy
    campaign.meta_call_to_action = meta_content.call_to_action

    # Generate Google Display content with single API call
    google_content = generate_google_display_content(messaging, primary_goal, target_audience, creative_context)
    campaign.google_headlines = google_content.headlines
    campaign.google_long_headline = google_content.long_headline
    campaign.google_descriptions = google_content.descriptions

    # Ready status
    status = pmcb_data.get('status', '')
    campaign.meta_ready = "AI Generated" if status == 'submitted' else ""
    campaign.google_ready = "AI Generated" if status == 'submitted' else ""

    # Save the campaign
    campaign.save()