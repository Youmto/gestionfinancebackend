"""
Service centralisé pour l'envoi d'emails.
"""

import logging
from typing import Optional, Dict, Any, List
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service centralisé pour l'envoi d'emails.
    
    Usage:
        EmailService.send_verification_code('user@example.com', '123456', 'registration')
        EmailService.send_welcome_email(user)
        EmailService.send_budget_alert(user, category, budget_status)
    """
    
    @staticmethod
    def _get_app_name():
        return getattr(settings, 'APP_NAME', 'Finance App')
    
    @staticmethod
    def _get_frontend_url():
        return getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
    
    @staticmethod
    def _send_email(
        to_email: str,
        subject: str,
        template_name: str,
        context: Dict[str, Any],
        from_email: Optional[str] = None
    ) -> bool:
        """
        Méthode interne pour envoyer un email avec template HTML.
        """
        try:
            # Ajouter les variables communes au contexte
            context.update({
                'app_name': EmailService._get_app_name(),
                'frontend_url': EmailService._get_frontend_url(),
                'support_email': getattr(settings, 'DEFAULT_FROM_EMAIL', ''),
            })
            
            # Générer le contenu HTML et texte
            try:
                html_content = render_to_string(f'emails/{template_name}.html', context)
                text_content = strip_tags(html_content)
            except Exception as template_error:
                # Si le template n'existe pas, utiliser un format simple
                logger.warning(f"Template emails/{template_name}.html non trouvé: {template_error}")
                html_content = EmailService._generate_simple_html(subject, context)
                text_content = strip_tags(html_content)
            
            # Créer et envoyer l'email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
                to=[to_email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)
            
            logger.info(f"Email '{template_name}' envoyé à {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi email à {to_email}: {str(e)}")
            return False
    
    @staticmethod
    def _generate_simple_html(subject: str, context: Dict[str, Any]) -> str:
        """Génère un HTML simple si le template n'existe pas."""
        code = context.get('code', '')
        app_name = context.get('app_name', 'Finance App')
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{subject}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #6366F1; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px; }}
                .code {{ font-size: 32px; font-weight: bold; color: #6366F1; letter-spacing: 8px; text-align: center; padding: 20px; background: white; border-radius: 8px; margin: 20px 0; }}
                .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{app_name}</h1>
                </div>
                <div class="content">
                    <h2>{subject}</h2>
                    {f'<div class="code">{code}</div>' if code else ''}
                    <p>Ce code expire dans 15 minutes.</p>
                </div>
                <div class="footer">
                    <p>© {app_name} - Tous droits réservés</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    # ================================================================
    # EMAILS DE VÉRIFICATION / AUTHENTIFICATION
    # ================================================================
    
    @classmethod
    def send_verification_code(
        cls,
        email: str,
        code: str,
        purpose: str = 'registration'
    ) -> bool:
        """
        Envoie un code de vérification OTP.
        """
        purpose_texts = {
            'registration': {
                'title': 'Confirmez votre inscription',
                'message': 'Utilisez ce code pour confirmer votre inscription',
                'subject': 'Code de vérification - Inscription'
            },
            'login': {
                'title': 'Connexion à votre compte',
                'message': 'Utilisez ce code pour vous connecter',
                'subject': 'Code de vérification - Connexion'
            },
            'password_reset': {
                'title': 'Réinitialisation du mot de passe',
                'message': 'Utilisez ce code pour réinitialiser votre mot de passe',
                'subject': 'Code de vérification - Mot de passe'
            },
            'email_change': {
                'title': 'Changement d\'adresse email',
                'message': 'Utilisez ce code pour confirmer votre nouvelle adresse email',
                'subject': 'Code de vérification - Changement email'
            }
        }
        
        purpose_data = purpose_texts.get(purpose, purpose_texts['registration'])
        
        context = {
            'code': code,
            'title': purpose_data['title'],
            'message': purpose_data['message'],
            'validity_minutes': getattr(settings, 'OTP_VALIDITY_MINUTES', 15),
            'email': email,
        }
        
        return cls._send_email(
            to_email=email,
            subject=f"{purpose_data['subject']} - {cls._get_app_name()}",
            template_name='verification_code',
            context=context
        )
    
    @classmethod
    def send_welcome_email(cls, user) -> bool:
        """
        Envoie un email de bienvenue après inscription.
        """
        context = {
            'user': user,
            'first_name': user.first_name or 'Utilisateur',
        }
        
        return cls._send_email(
            to_email=user.email,
            subject=f"Bienvenue sur {cls._get_app_name()}!",
            template_name='welcome',
            context=context
        )
    
    @classmethod
    def send_password_changed_notification(cls, user) -> bool:
        """
        Notifie l'utilisateur que son mot de passe a été changé.
        """
        context = {
            'user': user,
            'first_name': user.first_name or 'Utilisateur',
        }
        
        return cls._send_email(
            to_email=user.email,
            subject=f"Mot de passe modifié - {cls._get_app_name()}",
            template_name='password_changed',
            context=context
        )
    
    @classmethod
    def send_password_reset_link(cls, user, reset_token: str) -> bool:
        """
        Envoie un lien de réinitialisation de mot de passe.
        """
        reset_url = f"{cls._get_frontend_url()}/reset-password?token={reset_token}"
        
        context = {
            'user': user,
            'first_name': user.first_name or 'Utilisateur',
            'reset_url': reset_url,
            'validity_hours': 24,
        }
        
        return cls._send_email(
            to_email=user.email,
            subject=f"Réinitialisation de mot de passe - {cls._get_app_name()}",
            template_name='password_reset',
            context=context
        )
    
    # ================================================================
    # EMAILS BUDGET
    # ================================================================
    
    @classmethod
    def send_budget_alert(
        cls,
        user,
        category_name: str,
        category_icon: str,
        budget: float,
        spent: float,
        percentage: float,
        is_over_budget: bool = False
    ) -> bool:
        """
        Envoie une alerte de budget.
        """
        if is_over_budget:
            subject = f"🚨 Budget dépassé: {category_name}"
            alert_type = 'over_budget'
        else:
            subject = f"⚠️ Alerte budget: {category_name}"
            alert_type = 'warning'
        
        context = {
            'user': user,
            'first_name': user.first_name or 'Utilisateur',
            'category_name': category_name,
            'category_icon': category_icon,
            'budget': budget,
            'spent': spent,
            'remaining': budget - spent,
            'percentage': percentage,
            'alert_type': alert_type,
            'is_over_budget': is_over_budget,
        }
        
        return cls._send_email(
            to_email=user.email,
            subject=f"{subject} - {cls._get_app_name()}",
            template_name='budget_alert',
            context=context
        )
    
    @classmethod
    def send_weekly_budget_summary(
        cls,
        user,
        budgets_data: List[Dict[str, Any]],
        total_budget: float,
        total_spent: float
    ) -> bool:
        """
        Envoie un résumé hebdomadaire des budgets.
        """
        context = {
            'user': user,
            'first_name': user.first_name or 'Utilisateur',
            'budgets': budgets_data,
            'total_budget': total_budget,
            'total_spent': total_spent,
            'total_remaining': total_budget - total_spent,
            'overall_percentage': round((total_spent / total_budget * 100) if total_budget > 0 else 0, 1),
        }
        
        return cls._send_email(
            to_email=user.email,
            subject=f"📊 Résumé hebdomadaire de vos budgets - {cls._get_app_name()}",
            template_name='budget_summary',
            context=context
        )
    
    # ================================================================
    # EMAILS GROUPES
    # ================================================================
    
    @classmethod
    def send_group_invitation(cls, inviter, invitee_email: str, group) -> bool:
        """
        Envoie une invitation à rejoindre un groupe.
        """
        invite_url = f"{cls._get_frontend_url()}/groups/join/{group.invite_code}"
        
        context = {
            'inviter_name': inviter.full_name or inviter.email,
            'group_name': group.name,
            'invite_url': invite_url,
        }
        
        return cls._send_email(
            to_email=invitee_email,
            subject=f"Invitation à rejoindre {group.name} - {cls._get_app_name()}",
            template_name='group_invitation',
            context=context
        )
    
    @classmethod
    def send_expense_split_notification(
        cls,
        user,
        transaction_description: str,
        amount: float,
        group_name: str,
        payer_name: str
    ) -> bool:
        """
        Notifie un membre qu'il a une part à payer.
        """
        context = {
            'user': user,
            'first_name': user.first_name or 'Utilisateur',
            'transaction_description': transaction_description,
            'amount': amount,
            'group_name': group_name,
            'payer_name': payer_name,
        }
        
        return cls._send_email(
            to_email=user.email,
            subject=f"Nouvelle dépense partagée: {amount:,.0f} XAF - {cls._get_app_name()}",
            template_name='expense_split',
            context=context
        )
    
    # ================================================================
    # EMAILS RAPPELS ET RAPPORTS
    # ================================================================
    
    @classmethod
    def send_reminder_notification(
        cls,
        user,
        reminder_title: str,
        reminder_description: str,
        due_date: str,
        amount: Optional[float] = None
    ) -> bool:
        """
        Envoie un rappel.
        """
        context = {
            'user': user,
            'first_name': user.first_name or 'Utilisateur',
            'title': reminder_title,
            'description': reminder_description,
            'due_date': due_date,
            'amount': amount,
        }
        
        return cls._send_email(
            to_email=user.email,
            subject=f"🔔 Rappel: {reminder_title} - {cls._get_app_name()}",
            template_name='reminder',
            context=context
        )
    
    @classmethod
    def send_monthly_report(
        cls,
        user,
        month_name: str,
        year: int,
        total_income: float,
        total_expense: float,
        top_categories: List[Dict[str, Any]]
    ) -> bool:
        """
        Envoie le rapport mensuel.
        """
        context = {
            'user': user,
            'first_name': user.first_name or 'Utilisateur',
            'month_name': month_name,
            'year': year,
            'total_income': total_income,
            'total_expense': total_expense,
            'balance': total_income - total_expense,
            'top_categories': top_categories,
        }
        
        return cls._send_email(
            to_email=user.email,
            subject=f"📈 Rapport financier {month_name} {year} - {cls._get_app_name()}",
            template_name='monthly_report',
            context=context
        )
    
@classmethod
def send_weekly_summary(cls, user, week_start, week_end, income, expense, balance, transaction_count):
    """Envoie le résumé hebdomadaire."""
    context = {
        'first_name': user.first_name or 'Utilisateur',
        'week_start': week_start.strftime('%d/%m/%Y'),
        'week_end': week_end.strftime('%d/%m/%Y'),
        'income': income,
        'expense': expense,
        'balance': balance,
        'transaction_count': transaction_count,
        'is_positive': balance >= 0,
    }
    
    return cls._send_email(
        to_email=user.email,
        subject=f"📊 Votre résumé de la semaine du {context['week_start']}",
        template_name='emails/weekly_summary.html',
        context=context
    )

@classmethod
def send_monthly_summary(cls, user, month, year, income, expense, balance, transaction_count, top_expenses):
    """Envoie le résumé mensuel."""
    month_names = [
        'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
        'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
    ]
    
    context = {
        'first_name': user.first_name or 'Utilisateur',
        'month_name': month_names[month - 1],
        'year': year,
        'income': income,
        'expense': expense,
        'balance': balance,
        'transaction_count': transaction_count,
        'top_expenses': top_expenses,
        'is_positive': balance >= 0,
    }
    
    return cls._send_email(
        to_email=user.email,
        subject=f"📈 Votre bilan de {context['month_name']} {year}",
        template_name='emails/monthly_summary.html',
        context=context
    )

@classmethod
def send_reminder_notification(cls, user, reminder_title, reminder_description, due_date, amount=None, is_urgent=False):
    """Envoie une notification de rappel."""
    context = {
        'first_name': user.first_name or 'Utilisateur',
        'reminder_title': reminder_title,
        'reminder_description': reminder_description,
        'due_date': due_date.strftime('%d/%m/%Y'),
        'amount': amount,
        'is_urgent': is_urgent,
    }
    
    subject = "🚨 URGENT: " if is_urgent else "⏰ "
    subject += f"Rappel: {reminder_title}"
    
    return cls._send_email(
        to_email=user.email,
        subject=subject,
        template_name='emails/reminder_notification.html',
        context=context
    )