"""
Management command: python manage.py seed --env=staging
Generates the full test dataset for the staging environment.
"""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Seed the database with test data for staging/development'

    def add_arguments(self, parser):
        parser.add_argument(
            '--env',
            type=str,
            default='staging',
            choices=['dev', 'staging', 'demo'],
            help='Target environment (dev=minimal, staging=full, demo=curated)',
        )

    def handle(self, *args, **options):
        from django.conf import settings

        if settings.APP_ENVIRONMENT == 'production':
            raise CommandError(
                'BLOCKED: Cannot seed test data in production environment. '
                'This is a safety check to prevent test data contamination.'
            )

        env = options['env']
        self.stdout.write(self.style.WARNING(f'Seeding {env} data...'))

        from apps.seed_data import seed_all
        seed_all()

        self.stdout.write(self.style.SUCCESS('Seeding completed successfully.'))
