from django.core.management.base import BaseCommand
from property_app.models import Platform


class Command(BaseCommand):
    help = 'Populate initial advertising platforms'

    def handle(self, *args, **options):
        platforms_data = [
            {
                'name': 'meta',
                'display_name': 'Meta Ads',
                'net_rate': 0.8500,  # 85% net rate (15% deduction)
            },
            {
                'name': 'google_display',
                'display_name': 'Google Display',
                'net_rate': 0.8500,  # 85% net rate (15% deduction)
            },
            {
                'name': 'youtube',
                'display_name': 'YouTube',
                'net_rate': 0.8500,  # 85% net rate (15% deduction)
            },
            {
                'name': 'ott',
                'display_name': 'OTT',
                'net_rate': 0.8500,  # 85% net rate (15% deduction)
            },
        ]

        created_count = 0
        updated_count = 0

        for platform_data in platforms_data:
            platform, created = Platform.objects.get_or_create(
                name=platform_data['name'],
                defaults={
                    'display_name': platform_data['display_name'],
                    'net_rate': platform_data['net_rate'],
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created platform: {platform.display_name}')
                )
            else:
                # Update existing platform with new data
                platform.display_name = platform_data['display_name']
                platform.net_rate = platform_data['net_rate']
                platform.is_active = True
                platform.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated platform: {platform.display_name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed platforms. Created: {created_count}, Updated: {updated_count}'
            )
        )
