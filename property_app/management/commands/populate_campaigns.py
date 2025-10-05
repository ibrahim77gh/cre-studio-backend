from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
import random
import json

from property_app.models import (
    Campaign, Property, PropertyGroup, CampaignDate, CampaignDateType,
    CampaignBudget, UserPropertyMembership, PropertyUserRole
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate the database with sample campaign data for testing pagination'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=25,
            help='Number of campaigns to create (default: 25)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing campaigns before creating new ones'
        )

    def handle(self, *args, **options):
        count = options['count']
        clear_existing = options['clear']

        if clear_existing:
            self.stdout.write('Clearing existing campaigns...')
            Campaign.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS('Successfully cleared existing campaigns')
            )

        # Ensure we have the required data
        self.ensure_required_data()

        # Get available properties and users
        properties = list(Property.objects.all())
        users = list(User.objects.all())

        if not properties:
            raise CommandError('No properties found. Please create properties first.')
        
        if not users:
            raise CommandError('No users found. Please create users first.')

        self.stdout.write(f'Creating {count} campaigns...')

        # Sample data for campaigns
        centers = [
            'Spring Fashion Launch', 'Summer Sale Event', 'Back to School', 'Holiday Shopping',
            'Black Friday', 'Cyber Monday', 'Valentine\'s Day', 'Mother\'s Day',
            'Father\'s Day', 'Memorial Day Sale', 'Independence Day', 'Labor Day',
            'Halloween Special', 'Thanksgiving', 'Christmas Shopping', 'New Year Sale',
            'Winter Clearance', 'Spring Cleaning', 'Easter Special', 'Graduation Sale',
            'Wedding Season', 'Home Improvement', 'Tech Launch', 'Beauty Week',
            'Fitness Challenge', 'Food Festival', 'Art Exhibition', 'Music Concert',
            'Book Fair', 'Toy Drive'
        ]

        meta_headlines = [
            ['Discover Amazing Deals', 'Shop Now and Save', 'Limited Time Offer'],
            ['New Arrivals Daily', 'Fresh Styles', 'Trending Now'],
            ['Exclusive Collection', 'Premium Quality', 'Best Prices'],
            ['Special Promotion', 'Don\'t Miss Out', 'Shop Today'],
            ['Featured Products', 'Customer Favorites', 'Top Rated']
        ]

        google_headlines = [
            ['Shop the Latest Trends', 'Find Your Style', 'Quality You Can Trust'],
            ['Amazing Deals Await', 'Save Big Today', 'Limited Time Only'],
            ['New Collection', 'Fresh Arrivals', 'Trending Styles'],
            ['Exclusive Offers', 'Premium Selection', 'Best Value'],
            ['Special Sale', 'Don\'t Wait', 'Shop Now']
        ]

        google_descriptions = [
            ['Discover our latest collection', 'Find everything you need', 'Quality products at great prices'],
            ['Shop now and save big', 'Limited time offers', 'Don\'t miss out'],
            ['New arrivals daily', 'Fresh styles', 'Trending now'],
            ['Exclusive deals', 'Premium quality', 'Best prices guaranteed'],
            ['Special promotions', 'Shop today', 'Amazing savings']
        ]

        call_to_actions = [
            'Shop Now', 'Learn More', 'Get Started', 'Discover More', 'Find Out More',
            'Sign Up', 'Join Now', 'Try Free', 'Download', 'Buy Now'
        ]

        # Create campaigns
        created_count = 0
        for i in range(count):
            try:
                # Select random property and user
                property_obj = random.choice(properties)
                user = random.choice(users)

                # Generate campaign data
                center = random.choice(centers)
                start_date = date.today() + timedelta(days=random.randint(-30, 60))
                end_date = start_date + timedelta(days=random.randint(7, 30))

                # Create campaign
                campaign = Campaign.objects.create(
                    property=property_obj,
                    user=user,
                    center=center,
                    start_date=start_date,
                    end_date=end_date,
                    meta_main_copy_options=random.choice(meta_headlines),
                    meta_headline=random.choice(meta_headlines),
                    meta_desktop_display_copy=f"Discover amazing deals at {center}. Shop now and save big on our latest collection!",
                    meta_website_url=f"https://example.com/{center.lower().replace(' ', '-')}",
                    meta_call_to_action=random.choice(call_to_actions),
                    meta_notes=f"Campaign notes for {center}",
                    meta_ready="Ready for Meta ads",
                    google_headlines=random.choice(google_headlines),
                    google_long_headline=random.choice(google_headlines),
                    google_descriptions=random.choice(google_descriptions),
                    google_website_url=f"https://example.com/{center.lower().replace(' ', '-')}",
                    google_notes=f"Google ads notes for {center}",
                    google_ready="Ready for Google ads",
                    approval_status=random.choice([
                        Campaign.ApprovalStatus.PENDING,
                        Campaign.ApprovalStatus.ADMIN_APPROVED,
                        Campaign.ApprovalStatus.CLIENT_APPROVED,
                        Campaign.ApprovalStatus.FULLY_APPROVED
                    ]),
                    ai_processing_status=random.choice([
                        Campaign.AIProcessingStatus.PENDING,
                        Campaign.AIProcessingStatus.PROCESSING,
                        Campaign.AIProcessingStatus.COMPLETED,
                        Campaign.AIProcessingStatus.FAILED
                    ]),
                    dms_sync_ready=random.choice([True, False]),
                    pmcb_form_data={
                        'campaign_name': center,
                        'description': f'Marketing campaign for {center}',
                        'target_audience': 'General public',
                        'budget_range': random.choice(['$1,000-$5,000', '$5,000-$10,000', '$10,000+']),
                        'objectives': ['Brand awareness', 'Sales increase', 'Traffic generation']
                    }
                )

                # Create campaign dates
                self.create_campaign_dates(campaign, start_date, end_date)

                # Create campaign budget
                self.create_campaign_budget(campaign)

                created_count += 1

                if created_count % 5 == 0:
                    self.stdout.write(f'Created {created_count} campaigns...')

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating campaign {i+1}: {str(e)}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} campaigns!')
        )

    def ensure_required_data(self):
        """Ensure we have at least one property group, property, and user"""
        
        # Create property group if none exists
        if not PropertyGroup.objects.exists():
            self.stdout.write('Creating sample property group...')
            PropertyGroup.objects.create(name='Shopping Centers')
            PropertyGroup.objects.create(name='Retail Stores')
            PropertyGroup.objects.create(name='Malls')

        # Create properties if none exist
        if not Property.objects.exists():
            self.stdout.write('Creating sample properties...')
            property_groups = PropertyGroup.objects.all()
            
            sample_properties = [
                'Westfield Shopping Center',
                'Mall of America',
                'Times Square Plaza',
                'Downtown Retail District',
                'Metro Shopping Center',
                'Central Plaza',
                'Riverside Mall',
                'Highland Shopping Center'
            ]
            
            for i, prop_name in enumerate(sample_properties):
                Property.objects.create(
                    property_group=property_groups[i % len(property_groups)],
                    name=prop_name,
                    subdomain=prop_name.lower().replace(' ', '-').replace(',', '')
                )

        # Create a test user if none exists
        if not User.objects.exists():
            self.stdout.write('Creating test user...')
            User.objects.create_user(
                email='test@example.com',
                password='testpass123',
                first_name='Test',
                last_name='User'
            )

    def create_campaign_dates(self, campaign, start_date, end_date):
        """Create sample campaign dates"""
        date_types = [CampaignDateType.EVENT, CampaignDateType.MILESTONE, CampaignDateType.DEADLINE]
        
        # Create 2-4 random dates
        num_dates = random.randint(2, 4)
        for _ in range(num_dates):
            date_obj = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
            CampaignDate.objects.create(
                campaign=campaign,
                date=date_obj,
                date_type=random.choice(date_types),
                description=f"Important date for {campaign.center}",
                start_time=f"{random.randint(9, 17):02d}:00:00",
                end_time=f"{random.randint(18, 22):02d}:00:00"
            )

    def create_campaign_budget(self, campaign):
        """Create sample campaign budget"""
        total_gross = random.randint(1000, 50000)
        total_net = int(total_gross * random.uniform(0.8, 0.95))
        meta_gross = int(total_gross * random.uniform(0.3, 0.7))
        meta_net = int(meta_gross * random.uniform(0.8, 0.95))
        display_gross = total_gross - meta_gross
        display_net = int(display_gross * random.uniform(0.8, 0.95))
        creative_charges = random.randint(100, 1000)
        
        CampaignBudget.objects.create(
            campaign=campaign,
            creative_charges_deductions=creative_charges,
            total_gross=total_gross,
            total_net=total_net,
            meta_gross=meta_gross,
            meta_net=meta_net,
            display_gross=display_gross,
            display_net=display_net
        )
