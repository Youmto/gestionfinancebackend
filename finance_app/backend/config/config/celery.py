"""
Celery configuration for Finance App
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Create Celery app
app = Celery('finance_app')

# Load config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Celery Beat Schedule - Tâches planifiées
app.conf.beat_schedule = {
    # Vérifier les budgets tous les jours à 8h
    'check-budgets-daily': {
        'task': 'finances.tasks.check_all_budgets',
        'schedule': crontab(hour=8, minute=0),
    },
    
    # Envoyer un résumé hebdomadaire le lundi à 9h
    'weekly-summary': {
        'task': 'finances.tasks.send_weekly_summary',
        'schedule': crontab(hour=9, minute=0, day_of_week=1),
    },
    
    # Envoyer un résumé mensuel le 1er du mois à 9h
    'monthly-summary': {
        'task': 'finances.tasks.send_monthly_summary',
        'schedule': crontab(hour=9, minute=0, day_of_month=1),
    },
    
    # Nettoyer les codes OTP expirés tous les jours à minuit
    'cleanup-expired-codes': {
        'task': 'accounts.tasks.cleanup_expired_codes',
        'schedule': crontab(hour=0, minute=0),
    },
    
    # Envoyer les rappels de paiement tous les jours à 10h
    'payment-reminders': {
        'task': 'reminders.tasks.send_due_reminders',
        'schedule': crontab(hour=10, minute=0),
    },
}

app.conf.timezone = 'Europe/Paris'


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')