"""
Management command to initialize the database with default data.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from finances.models import create_default_categories


class Command(BaseCommand):
    help = 'Initialize the database with default categories and other data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of default data even if it exists',
        )
    
    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Initializing default data...')
        
        # Create default categories
        self.stdout.write('Creating default categories...')
        count = create_default_categories()
        
        if count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Created {count} default categories')
            )
        else:
            self.stdout.write(
                self.style.WARNING('  Default categories already exist')
            )
        
        self.stdout.write(self.style.SUCCESS('\n✓ Database initialization complete!'))