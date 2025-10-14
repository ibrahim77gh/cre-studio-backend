from django.core.management.base import BaseCommand
from property_app.models import PromptConfiguration


class Command(BaseCommand):
    help = 'Populate default AI prompt configurations for campaign content generation'

    def handle(self, *args, **options):
        prompts_data = [
            {
                'prompt_type': 'meta_ad',
                'property': None,  # Default prompt
                'system_message': 'You are an expert Meta ad copywriter. Generate comprehensive ad content that drives engagement and conversions.',
                'user_prompt_template': '''Generate comprehensive Meta ad content based on the following information:

Messaging: {messaging}
Primary Goal: {primary_goal}
Target Audience: {target_audience}
Campaign Name: {campaign_name}

Please provide:
1. 5 different compelling headlines (max 50 characters each, single line)
2. Five different main copy variations (each max 200 characters, 2-3 lines)
3. Desktop display copy (max 325 characters)
4. An appropriate call-to-action

IMPORTANT: Each text option should utilize as much of the character limit as possible while remaining engaging and on-brand. All content should be optimized for Meta's advertising platform.''',
                'available_variables': {
                    'messaging': 'Campaign messaging and key points',
                    'primary_goal': 'Primary goal of the campaign (e.g., awareness, conversions)',
                    'target_audience': 'Target audience description',
                    'campaign_name': 'Name of the campaign or key event'
                },
            },
            {
                'prompt_type': 'google_display',
                'property': None,  # Default prompt
                'system_message': 'You are an expert Google Ads copywriter. Generate comprehensive ad content optimized for Google Display campaigns.',
                'user_prompt_template': '''Generate comprehensive Google Display ad content based on the following information:

Messaging: {messaging}
Primary Goal: {primary_goal}
Target Audience: {target_audience}
Campaign Name: {campaign_name}

Please provide:
1. Five different headlines (each exactly 30 characters)
2. Three long headlines (each exactly 90 characters)
3. Five different descriptions (each exactly 90 characters)

CRITICAL REQUIREMENTS:
- Each text option should utilize the full character limit as much as possible
- NO exclamation marks are allowed in any Google content
- All content should be optimized for Google Display campaigns and drive the specified goal''',
                'available_variables': {
                    'messaging': 'Campaign messaging and key points',
                    'primary_goal': 'Primary goal of the campaign (e.g., awareness, conversions)',
                    'target_audience': 'Target audience description',
                    'campaign_name': 'Name of the campaign or key event'
                },
            },
        ]

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for prompt_data in prompts_data:
            # Check if default prompt already exists
            existing = PromptConfiguration.objects.filter(
                prompt_type=prompt_data['prompt_type'],
                property__isnull=True
            ).first()

            if existing:
                skipped_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'Skipped: Default {existing.get_prompt_type_display()} prompt already exists (ID: {existing.id})'
                    )
                )
            else:
                prompt = PromptConfiguration.objects.create(**prompt_data)
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created default {prompt.get_prompt_type_display()} prompt (ID: {prompt.id})'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully processed default prompts. Created: {created_count}, Skipped: {skipped_count}'
            )
        )
        
        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    '\nDefault prompts are now available. Super users can create property-specific prompts via the API.'
                )
            )

