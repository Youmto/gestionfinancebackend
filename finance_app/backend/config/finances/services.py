"""
Services pour les finances - Alertes budget automatiques
"""

import logging
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


class BudgetAlertService:
    """Service pour gérer les alertes de budget."""
    
    _recent_alerts = {}
    
    @classmethod
    def check_and_send_alerts(cls, user, category=None):
        """Vérifie les budgets et envoie des alertes si nécessaire."""
        from accounts.models import NotificationPreferences
        
        try:
            prefs = NotificationPreferences.objects.get(user=user)
            if not prefs.email_budget_alerts:
                return
        except NotificationPreferences.DoesNotExist:
            pass
        
        if category and category.budget and category.budget > 0:
            cls._check_category_budget(user, category)
    
    @classmethod
    def _check_category_budget(cls, user, category):
        """Vérifie le budget d'une catégorie et envoie une alerte."""
        from core.services.email_service import EmailService
        
        budget_status = category.get_budget_status()
        if not budget_status:
            return
        
        percentage = budget_status['percentage']
        threshold = float(category.budget_alert_threshold or 80)
        
        alert_type = None
        if percentage >= 100:
            alert_type = 'over_budget'
        elif percentage >= threshold:
            alert_type = 'warning'
        
        if not alert_type:
            return
        
        # Éviter les doublons (1 par jour)
        alert_key = f"{user.id}_{category.id}_{alert_type}"
        last_alert = cls._recent_alerts.get(alert_key)
        
        if last_alert and (timezone.now() - last_alert) < timedelta(hours=24):
            return
        
        try:
            success = EmailService.send_budget_alert(
                user=user,
                category_name=category.name,
                category_icon=category.icon or '📊',
                budget=float(category.budget),
                spent=float(budget_status['spent']),
                percentage=percentage,
                is_over_budget=(alert_type == 'over_budget')
            )
            
            if success:
                cls._recent_alerts[alert_key] = timezone.now()
                logger.info(f"Alerte budget: {category.name} ({percentage}%)")
        except Exception as e:
            logger.error(f"Erreur alerte budget: {e}")