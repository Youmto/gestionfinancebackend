"""
Celery tasks for accounts app
"""

import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_codes():
    """
    Supprime les codes OTP expirés.
    Exécuté tous les jours à minuit.
    """
    from .models import EmailVerificationCode
    
    logger.info("Nettoyage des codes expirés...")
    
    expired = EmailVerificationCode.objects.filter(
        expires_at__lt=timezone.now()
    )
    
    count = expired.count()
    expired.delete()
    
    logger.info(f"{count} codes expirés supprimés")
    return {'deleted': count}


@shared_task
def send_welcome_email_async(user_id):
    """
    Envoie l'email de bienvenue de manière asynchrone.
    """
    from django.contrib.auth import get_user_model
    from core.services.email_service import EmailService
    
    User = get_user_model()
    
    try:
        user = User.objects.get(id=user_id)
        EmailService.send_welcome_email(user)
        logger.info(f"Email de bienvenue envoyé à {user.email}")
        return {'status': 'success'}
    except User.DoesNotExist:
        logger.error(f"Utilisateur {user_id} non trouvé")
        return {'status': 'error'}