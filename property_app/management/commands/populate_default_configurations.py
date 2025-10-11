from django.core.management.base import BaseCommand
from property_app.models import Configuration


class Command(BaseCommand):
    help = 'Populate default system configurations with current hardcoded prompts'

    def handle(self, *args, **options):
        # Default configurations based on current hardcoded prompts
        default_configs = [
            {
                'config_type': Configuration.ConfigType.META_AD_COPYWRITER,
                'name': 'Default Meta Ad Copywriter',
                'description': 'Default system prompt for generating Meta ad content',
                'system_prompt': 'You are an expert Meta ad copywriter. Generate comprehensive ad content that drives engagement and conversions.',
                'user_prompt_template': '''Generate comprehensive Meta ad content based on the following information:

Messaging: {messaging}
Primary Goal: {primary_goal}
Target Audience: {target_audience}
Campaign Name: {campaign_name}

Please provide:
1. 5 different compelling headline (max 50 characters, single line)
2. Five different main copy variations (each max 200 characters, 2-3 lines)
3. Desktop display copy (max 325 characters)
4. An appropriate call-to-action

IMPORTANT: Each text option should utilize as much of the character limit as possible while remaining engaging and on-brand. All content should be optimized for Meta's advertising platform.''',
                'available_variables': [
                    {'name': 'messaging', 'description': 'The main messaging for the campaign'},
                    {'name': 'primary_goal', 'description': 'The primary goal of the campaign'},
                    {'name': 'target_audience', 'description': 'The target audience for the campaign'},
                    {'name': 'campaign_name', 'description': 'The name of the campaign'},
                    {'name': 'property_name', 'description': 'The name of the property'},
                    {'name': 'brand_tone', 'description': 'The brand tone and voice'},
                ],
                'is_default': True,
                'property': None,  # Global configuration
            },
            {
                'config_type': Configuration.ConfigType.GOOGLE_ADS_COPYWRITER,
                'name': 'Default Google Ads Copywriter',
                'description': 'Default system prompt for generating Google Display ad content',
                'system_prompt': 'You are an expert Google Ads copywriter. Generate comprehensive ad content optimized for Google Display campaigns.',
                'user_prompt_template': '''Generate comprehensive Google Display ad content based on the following information:

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
- All content should be optimized for Google Display campaigns and drive the specified goal''',
                'available_variables': [
                    {'name': 'messaging', 'description': 'The main messaging for the campaign'},
                    {'name': 'primary_goal', 'description': 'The primary goal of the campaign'},
                    {'name': 'target_audience', 'description': 'The target audience for the campaign'},
                    {'name': 'campaign_name', 'description': 'The name of the campaign'},
                    {'name': 'property_name', 'description': 'The name of the property'},
                    {'name': 'brand_tone', 'description': 'The brand tone and voice'},
                ],
                'is_default': True,
                'property': None,  # Global configuration
            },
        ]

        created_count = 0
        for config_data in default_configs:
            config, created = Configuration.objects.get_or_create(
                config_type=config_data['config_type'],
                property=config_data['property'],
                is_default=True,
                defaults=config_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created default configuration: {config.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Default configuration already exists: {config.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully processed {len(default_configs)} configurations. Created {created_count} new configurations.')
        )
