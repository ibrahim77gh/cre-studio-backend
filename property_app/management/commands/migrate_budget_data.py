from django.core.management.base import BaseCommand
from property_app.models import CampaignBudget, Platform, PlatformBudget


class Command(BaseCommand):
    help = 'Migrate existing budget data from old structure to new platform-based structure'

    def handle(self, *args, **options):
        migrated_count = 0
        
        # Get all existing campaign budgets
        budgets = CampaignBudget.objects.all()
        
        for budget in budgets:
            # Check if this budget has old platform-specific data
            # Note: These fields should be removed in the migration, but we check for them anyway
            if hasattr(budget, 'meta_gross') and budget.meta_gross:
                meta_platform = Platform.objects.get(name='meta')
                platform_budget, created = PlatformBudget.objects.get_or_create(
                    campaign_budget=budget,
                    platform=meta_platform
                )
                if created:
                    platform_budget.gross_amount = budget.meta_gross
                    platform_budget.save()
                    self.stdout.write(f'Migrated Meta budget for campaign {budget.campaign.id}')

            if hasattr(budget, 'display_gross') and budget.display_gross:
                display_platform = Platform.objects.get(name='google_display')
                platform_budget, created = PlatformBudget.objects.get_or_create(
                    campaign_budget=budget,
                    platform=display_platform
                )
                if created:
                    platform_budget.gross_amount = budget.display_gross
                    platform_budget.save()
                    self.stdout.write(f'Migrated Google Display budget for campaign {budget.campaign.id}')

            migrated_count += 1

        self.stdout.write(
            self.style.SUCCESS(f'Successfully migrated {migrated_count} campaign budgets')
        )
