"""
Celery tasks for finances app
"""

import logging
from decimal import Decimal
from datetime import datetime, timedelta
from calendar import monthrange

from celery import shared_task
from django.db.models import Sum, Case, When, DecimalField, Q
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def check_all_budgets(self):
    """
    Vérifie les budgets de tous les utilisateurs et envoie des alertes.
    Exécuté tous les jours à 8h.
    """
    from .models import Category, Transaction
    from .services import BudgetAlertService
    
    logger.info("Démarrage de la vérification des budgets...")
    
    # Utilisateurs avec des catégories ayant un budget
    users = User.objects.filter(
        is_active=True
    ).distinct()
    
    alerts_sent = 0
    errors = 0
    
    for user in users:
        try:
            BudgetAlertService.check_and_send_alerts(user)
            alerts_sent += 1
        except Exception as e:
            logger.error(f"Erreur vérification budget pour {user.email}: {e}")
            errors += 1
    
    logger.info(f"Vérification terminée: {alerts_sent} utilisateurs vérifiés, {errors} erreurs")
    
    return {
        'users_checked': alerts_sent,
        'errors': errors
    }


@shared_task(bind=True, max_retries=3)
def send_weekly_summary(self):
    """
    Envoie un résumé hebdomadaire à tous les utilisateurs.
    Exécuté chaque lundi à 9h.
    """
    from .models import Transaction
    from accounts.models import NotificationPreferences
    from core.services.email_service import EmailService
    
    logger.info("Envoi des résumés hebdomadaires...")
    
    # Calculer la semaine précédente
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday() + 7)  # Lundi dernier
    week_end = week_start + timedelta(days=6)  # Dimanche dernier
    
    users = User.objects.filter(is_active=True)
    sent_count = 0
    
    for user in users:
        try:
            # Vérifier les préférences
            try:
                prefs = NotificationPreferences.objects.get(user=user)
                if not prefs.email_weekly_summary:
                    continue
            except NotificationPreferences.DoesNotExist:
                pass  # Par défaut, envoyer
            
            # Calculer les stats de la semaine
            transactions = Transaction.objects.filter(
                user=user,
                group__isnull=True,
                is_deleted=False,
                date__gte=week_start,
                date__lte=week_end
            )
            
            stats = transactions.aggregate(
                total_income=Sum(
                    Case(
                        When(type='income', then='amount'),
                        default=Decimal('0'),
                        output_field=DecimalField()
                    )
                ),
                total_expense=Sum(
                    Case(
                        When(type='expense', then='amount'),
                        default=Decimal('0'),
                        output_field=DecimalField()
                    )
                )
            )
            
            income = stats['total_income'] or Decimal('0')
            expense = stats['total_expense'] or Decimal('0')
            balance = income - expense
            transaction_count = transactions.count()
            
            # Envoyer l'email
            if transaction_count > 0:
                EmailService.send_weekly_summary(
                    user=user,
                    week_start=week_start,
                    week_end=week_end,
                    income=float(income),
                    expense=float(expense),
                    balance=float(balance),
                    transaction_count=transaction_count
                )
                sent_count += 1
                
        except Exception as e:
            logger.error(f"Erreur envoi résumé hebdo pour {user.email}: {e}")
    
    logger.info(f"Résumés hebdomadaires envoyés: {sent_count}")
    return {'sent': sent_count}


@shared_task(bind=True, max_retries=3)
def send_monthly_summary(self):
    """
    Envoie un résumé mensuel à tous les utilisateurs.
    Exécuté le 1er de chaque mois à 9h.
    """
    from .models import Transaction, Category
    from accounts.models import NotificationPreferences
    from core.services.email_service import EmailService
    
    logger.info("Envoi des résumés mensuels...")
    
    # Mois précédent
    today = timezone.now().date()
    first_day_this_month = today.replace(day=1)
    last_day_prev_month = first_day_this_month - timedelta(days=1)
    first_day_prev_month = last_day_prev_month.replace(day=1)
    
    users = User.objects.filter(is_active=True)
    sent_count = 0
    
    for user in users:
        try:
            # Vérifier les préférences
            try:
                prefs = NotificationPreferences.objects.get(user=user)
                if not prefs.email_monthly_summary:
                    continue
            except NotificationPreferences.DoesNotExist:
                pass
            
            # Stats du mois
            transactions = Transaction.objects.filter(
                user=user,
                group__isnull=True,
                is_deleted=False,
                date__gte=first_day_prev_month,
                date__lte=last_day_prev_month
            )
            
            stats = transactions.aggregate(
                total_income=Sum(
                    Case(
                        When(type='income', then='amount'),
                        default=Decimal('0'),
                        output_field=DecimalField()
                    )
                ),
                total_expense=Sum(
                    Case(
                        When(type='expense', then='amount'),
                        default=Decimal('0'),
                        output_field=DecimalField()
                    )
                )
            )
            
            income = stats['total_income'] or Decimal('0')
            expense = stats['total_expense'] or Decimal('0')
            balance = income - expense
            
            # Top catégories dépenses
            top_expenses = transactions.filter(type='expense').values(
                'category__name', 'category__icon'
            ).annotate(
                total=Sum('amount')
            ).order_by('-total')[:5]
            
            # Envoyer l'email
            if transactions.exists():
                EmailService.send_monthly_summary(
                    user=user,
                    month=last_day_prev_month.month,
                    year=last_day_prev_month.year,
                    income=float(income),
                    expense=float(expense),
                    balance=float(balance),
                    transaction_count=transactions.count(),
                    top_expenses=list(top_expenses)
                )
                sent_count += 1
                
        except Exception as e:
            logger.error(f"Erreur envoi résumé mensuel pour {user.email}: {e}")
    
    logger.info(f"Résumés mensuels envoyés: {sent_count}")
    return {'sent': sent_count}


@shared_task
def check_user_budget(user_id, category_id=None):
    """
    Vérifie le budget d'un utilisateur spécifique.
    Peut être appelé manuellement ou après une transaction.
    """
    from .services import BudgetAlertService
    
    try:
        user = User.objects.get(id=user_id)
        
        if category_id:
            from .models import Category
            category = Category.objects.get(id=category_id)
            BudgetAlertService.check_and_send_alerts(user, category)
        else:
            BudgetAlertService.check_and_send_alerts(user)
        
        return {'status': 'success', 'user': user.email}
        
    except User.DoesNotExist:
        logger.error(f"Utilisateur {user_id} non trouvé")
        return {'status': 'error', 'message': 'User not found'}
    except Exception as e:
        logger.error(f"Erreur check_user_budget: {e}")
        return {'status': 'error', 'message': str(e)}