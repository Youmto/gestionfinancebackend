"""
Celery tasks for reminders app
"""

import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task
def send_due_reminders():
    """
    Envoie des rappels pour les échéances du jour.
    Exécuté tous les jours à 10h.
    """
    from .models import Reminder
    from core.services.email_service import EmailService
    
    logger.info("Envoi des rappels d'échéance...")
    
    today = timezone.now().date()
    
    # Rappels pour aujourd'hui
    due_today = Reminder.objects.filter(
        due_date=today,
        is_completed=False,
        is_active=True
    ).select_related('user')
    
    # Rappels pour demain (pré-alerte)
    due_tomorrow = Reminder.objects.filter(
        due_date=today + timedelta(days=1),
        is_completed=False,
        is_active=True
    ).select_related('user')
    
    sent_count = 0
    
    # Envoyer rappels du jour
    for reminder in due_today:
        try:
            EmailService.send_reminder_notification(
                user=reminder.user,
                reminder_title=reminder.title,
                reminder_description=reminder.description,
                due_date=reminder.due_date,
                amount=float(reminder.amount) if reminder.amount else None,
                is_urgent=True
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Erreur envoi rappel {reminder.id}: {e}")
    
    # Envoyer pré-alertes pour demain
    for reminder in due_tomorrow:
        try:
            EmailService.send_reminder_notification(
                user=reminder.user,
                reminder_title=reminder.title,
                reminder_description=reminder.description,
                due_date=reminder.due_date,
                amount=float(reminder.amount) if reminder.amount else None,
                is_urgent=False
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Erreur envoi pré-alerte {reminder.id}: {e}")
    
    logger.info(f"Rappels envoyés: {sent_count}")
    return {'sent': sent_count}