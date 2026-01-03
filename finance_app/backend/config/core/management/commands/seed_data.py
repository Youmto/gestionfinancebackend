"""
Commande Django pour générer un jeu de données complet de test
Usage: python manage.py seed_data
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta, date
from decimal import Decimal
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Génère un jeu de données complet pour tester toutes les fonctionnalités'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('🚀 Génération des données de test...'))
        
        # Import des modèles
        from finances.models import Category, Transaction, ExpenseSplit
        from groups.models import Group, GroupMember, GroupInvitation
        from reminders.models import Reminder
        from events.models import Event
        from accounts.models import NotificationPreferences
        
        # ========================================
        # 1. CRÉATION DES UTILISATEURS
        # ========================================
        self.stdout.write('👤 Création des utilisateurs...')
        
        users_data = [
            {
                'email': 'alice@example.com',
                'password': 'TestPass123!',
                'first_name': 'Alice',
                'last_name': 'Dupont',
                'currency': 'EUR',
            },
            {
                'email': 'bob@example.com',
                'password': 'TestPass123!',
                'first_name': 'Bob',
                'last_name': 'Martin',
                'currency': 'EUR',
            },
            {
                'email': 'charlie@example.com',
                'password': 'TestPass123!',
                'first_name': 'Charlie',
                'last_name': 'Bernard',
                'currency': 'EUR',
            },
            {
                'email': 'diana@example.com',
                'password': 'TestPass123!',
                'first_name': 'Diana',
                'last_name': 'Leroy',
                'currency': 'USD',
            },
        ]
        
        users = []
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                email=user_data['email'],
                defaults={
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'currency': user_data['currency'],
                    'is_verified': True,
                }
            )
            if created:
                user.set_password(user_data['password'])
                user.save()
                # Créer les préférences de notification
                NotificationPreferences.objects.get_or_create(user=user)
                self.stdout.write(f'   ✅ {user.email} créé')
            else:
                self.stdout.write(f'   ⏭️  {user.email} existe déjà')
            users.append(user)
        
        alice, bob, charlie, diana = users
        
        # ========================================
        # 2. RÉCUPÉRATION DES CATÉGORIES
        # ========================================
        self.stdout.write('📁 Récupération des catégories...')
        
        # S'assurer que les catégories système existent
        from finances.models import create_default_categories
        create_default_categories()
        
        categories = {
            'salary': Category.objects.filter(name='Salaire', is_system=True).first(),
            'freelance': Category.objects.filter(name='Freelance', is_system=True).first(),
            'food': Category.objects.filter(name='Alimentation', is_system=True).first(),
            'transport': Category.objects.filter(name='Transport', is_system=True).first(),
            'housing': Category.objects.filter(name='Logement', is_system=True).first(),
            'bills': Category.objects.filter(name='Factures & Services', is_system=True).first(),
            'entertainment': Category.objects.filter(name='Divertissement', is_system=True).first(),
            'shopping': Category.objects.filter(name='Shopping', is_system=True).first(),
            'health': Category.objects.filter(name='Santé', is_system=True).first(),
            'travel': Category.objects.filter(name='Voyages', is_system=True).first(),
            'investments': Category.objects.filter(name='Investissements', is_system=True).first(),
            'gifts': Category.objects.filter(name='Cadeaux reçus', is_system=True).first(),
        }
        
        # Créer des catégories personnalisées pour Alice
        custom_cat1, _ = Category.objects.get_or_create(
            name='Crypto',
            user=alice,
            defaults={
                'icon': '₿',
                'color': '#F7931A',
                'type': 'both',
                'is_system': False,
            }
        )
        
        custom_cat2, _ = Category.objects.get_or_create(
            name='Abonnements',
            user=alice,
            defaults={
                'icon': '📺',
                'color': '#E50914',
                'type': 'expense',
                'is_system': False,
            }
        )
        
        self.stdout.write('   ✅ Catégories prêtes')
        
        # ========================================
        # 3. CRÉATION DES TRANSACTIONS (Alice)
        # ========================================
        self.stdout.write('💰 Création des transactions pour Alice...')
        
        today = date.today()
        
        # Transactions d'Alice - 3 derniers mois
        alice_transactions = [
            # Revenus
            {'category': categories['salary'], 'amount': 3500, 'type': 'income', 'description': 'Salaire Janvier', 'date': today.replace(day=1) - timedelta(days=60)},
            {'category': categories['salary'], 'amount': 3500, 'type': 'income', 'description': 'Salaire Février', 'date': today.replace(day=1) - timedelta(days=30)},
            {'category': categories['salary'], 'amount': 3500, 'type': 'income', 'description': 'Salaire Mars', 'date': today.replace(day=1)},
            {'category': categories['freelance'], 'amount': 800, 'type': 'income', 'description': 'Mission freelance site web', 'date': today - timedelta(days=45)},
            {'category': categories['investments'], 'amount': 150, 'type': 'income', 'description': 'Dividendes actions', 'date': today - timedelta(days=20)},
            {'category': categories['gifts'], 'amount': 100, 'type': 'income', 'description': 'Cadeau anniversaire', 'date': today - timedelta(days=10)},
            
            # Dépenses - Logement
            {'category': categories['housing'], 'amount': 850, 'type': 'expense', 'description': 'Loyer Janvier', 'date': today.replace(day=5) - timedelta(days=60)},
            {'category': categories['housing'], 'amount': 850, 'type': 'expense', 'description': 'Loyer Février', 'date': today.replace(day=5) - timedelta(days=30)},
            {'category': categories['housing'], 'amount': 850, 'type': 'expense', 'description': 'Loyer Mars', 'date': today.replace(day=5)},
            
            # Dépenses - Factures
            {'category': categories['bills'], 'amount': 45, 'type': 'expense', 'description': 'Facture électricité', 'date': today - timedelta(days=55)},
            {'category': categories['bills'], 'amount': 30, 'type': 'expense', 'description': 'Facture internet', 'date': today - timedelta(days=50)},
            {'category': categories['bills'], 'amount': 20, 'type': 'expense', 'description': 'Forfait mobile', 'date': today - timedelta(days=48)},
            {'category': categories['bills'], 'amount': 50, 'type': 'expense', 'description': 'Facture électricité', 'date': today - timedelta(days=25)},
            {'category': categories['bills'], 'amount': 30, 'type': 'expense', 'description': 'Facture internet', 'date': today - timedelta(days=20)},
            
            # Dépenses - Alimentation
            {'category': categories['food'], 'amount': 85, 'type': 'expense', 'description': 'Courses Carrefour', 'date': today - timedelta(days=56)},
            {'category': categories['food'], 'amount': 42, 'type': 'expense', 'description': 'Restaurant midi', 'date': today - timedelta(days=52)},
            {'category': categories['food'], 'amount': 95, 'type': 'expense', 'description': 'Courses Leclerc', 'date': today - timedelta(days=45)},
            {'category': categories['food'], 'amount': 28, 'type': 'expense', 'description': 'Boulangerie', 'date': today - timedelta(days=40)},
            {'category': categories['food'], 'amount': 110, 'type': 'expense', 'description': 'Courses Auchan', 'date': today - timedelta(days=30)},
            {'category': categories['food'], 'amount': 65, 'type': 'expense', 'description': 'Restaurant avec amis', 'date': today - timedelta(days=25)},
            {'category': categories['food'], 'amount': 78, 'type': 'expense', 'description': 'Courses Lidl', 'date': today - timedelta(days=15)},
            {'category': categories['food'], 'amount': 35, 'type': 'expense', 'description': 'Pizzeria', 'date': today - timedelta(days=8)},
            {'category': categories['food'], 'amount': 92, 'type': 'expense', 'description': 'Courses supermarché', 'date': today - timedelta(days=3)},
            
            # Dépenses - Transport
            {'category': categories['transport'], 'amount': 75, 'type': 'expense', 'description': 'Pass Navigo', 'date': today - timedelta(days=58)},
            {'category': categories['transport'], 'amount': 75, 'type': 'expense', 'description': 'Pass Navigo', 'date': today - timedelta(days=28)},
            {'category': categories['transport'], 'amount': 45, 'type': 'expense', 'description': 'Essence', 'date': today - timedelta(days=35)},
            {'category': categories['transport'], 'amount': 25, 'type': 'expense', 'description': 'Uber', 'date': today - timedelta(days=12)},
            
            # Dépenses - Divertissement
            {'category': categories['entertainment'], 'amount': 15, 'type': 'expense', 'description': 'Netflix', 'date': today - timedelta(days=50)},
            {'category': categories['entertainment'], 'amount': 12, 'type': 'expense', 'description': 'Spotify', 'date': today - timedelta(days=50)},
            {'category': categories['entertainment'], 'amount': 25, 'type': 'expense', 'description': 'Cinéma', 'date': today - timedelta(days=42)},
            {'category': categories['entertainment'], 'amount': 15, 'type': 'expense', 'description': 'Netflix', 'date': today - timedelta(days=20)},
            {'category': categories['entertainment'], 'amount': 12, 'type': 'expense', 'description': 'Spotify', 'date': today - timedelta(days=20)},
            {'category': categories['entertainment'], 'amount': 60, 'type': 'expense', 'description': 'Concert', 'date': today - timedelta(days=18)},
            
            # Dépenses - Shopping
            {'category': categories['shopping'], 'amount': 89, 'type': 'expense', 'description': 'Vêtements Zara', 'date': today - timedelta(days=38)},
            {'category': categories['shopping'], 'amount': 45, 'type': 'expense', 'description': 'Chaussures', 'date': today - timedelta(days=22)},
            {'category': categories['shopping'], 'amount': 199, 'type': 'expense', 'description': 'Casque audio', 'date': today - timedelta(days=5)},
            
            # Dépenses - Santé
            {'category': categories['health'], 'amount': 25, 'type': 'expense', 'description': 'Pharmacie', 'date': today - timedelta(days=33)},
            {'category': categories['health'], 'amount': 50, 'type': 'expense', 'description': 'Médecin généraliste', 'date': today - timedelta(days=15)},
            
            # Dépenses - Voyages
            {'category': categories['travel'], 'amount': 120, 'type': 'expense', 'description': 'Billet train Lyon', 'date': today - timedelta(days=14)},
            {'category': categories['travel'], 'amount': 85, 'type': 'expense', 'description': 'Hôtel Lyon', 'date': today - timedelta(days=13)},
        ]
        
        # Supprimer les anciennes transactions d'Alice
        Transaction.objects.filter(user=alice, group__isnull=True).delete()
        
        for tx_data in alice_transactions:
            if tx_data['category']:
                Transaction.objects.create(
                    user=alice,
                    category=tx_data['category'],
                    amount=Decimal(str(tx_data['amount'])),
                    type=tx_data['type'],
                    description=tx_data['description'],
                    date=tx_data['date'],
                )
        
        self.stdout.write(f'   ✅ {len(alice_transactions)} transactions créées pour Alice')
        
        # ========================================
        # 4. TRANSACTIONS POUR BOB
        # ========================================
        self.stdout.write('💰 Création des transactions pour Bob...')
        
        bob_transactions = [
            {'category': categories['salary'], 'amount': 2800, 'type': 'income', 'description': 'Salaire', 'date': today.replace(day=1)},
            {'category': categories['housing'], 'amount': 650, 'type': 'expense', 'description': 'Loyer', 'date': today.replace(day=5)},
            {'category': categories['food'], 'amount': 200, 'type': 'expense', 'description': 'Courses', 'date': today - timedelta(days=10)},
            {'category': categories['transport'], 'amount': 50, 'type': 'expense', 'description': 'Essence', 'date': today - timedelta(days=7)},
            {'category': categories['entertainment'], 'amount': 30, 'type': 'expense', 'description': 'Jeux vidéo', 'date': today - timedelta(days=5)},
        ]
        
        Transaction.objects.filter(user=bob, group__isnull=True).delete()
        
        for tx_data in bob_transactions:
            if tx_data['category']:
                Transaction.objects.create(
                    user=bob,
                    category=tx_data['category'],
                    amount=Decimal(str(tx_data['amount'])),
                    type=tx_data['type'],
                    description=tx_data['description'],
                    date=tx_data['date'],
                )
        
        self.stdout.write(f'   ✅ {len(bob_transactions)} transactions créées pour Bob')
        
        # ========================================
        # 5. CRÉATION DES GROUPES
        # ========================================
        self.stdout.write('👥 Création des groupes...')
        
        # Groupe 1: Colocation (Alice owner)
        coloc, created = Group.objects.get_or_create(
            name='Colocation Paris',
            owner=alice,
            defaults={
                'description': 'Gestion des dépenses de notre colocation',
                'currency': 'EUR',
            }
        )
        
        if created:
            # Alice est déjà ajoutée comme admin dans le signal
            # Ajouter Bob et Charlie
            GroupMember.objects.get_or_create(
                group=coloc,
                user=bob,
                defaults={
                    'role': 'member',
                    'status': 'active',
                    'invited_by': alice,
                    'joined_at': timezone.now(),
                }
            )
            GroupMember.objects.get_or_create(
                group=coloc,
                user=charlie,
                defaults={
                    'role': 'member',
                    'status': 'active',
                    'invited_by': alice,
                    'joined_at': timezone.now(),
                }
            )
            self.stdout.write('   ✅ Groupe "Colocation Paris" créé')
        else:
            self.stdout.write('   ⏭️  Groupe "Colocation Paris" existe déjà')
        
        # Groupe 2: Voyage (Bob owner)
        voyage, created = Group.objects.get_or_create(
            name='Voyage Espagne 2025',
            owner=bob,
            defaults={
                'description': 'Budget pour notre voyage à Barcelone',
                'currency': 'EUR',
            }
        )
        
        if created:
            GroupMember.objects.get_or_create(
                group=voyage,
                user=alice,
                defaults={
                    'role': 'member',
                    'status': 'active',
                    'invited_by': bob,
                    'joined_at': timezone.now(),
                }
            )
            GroupMember.objects.get_or_create(
                group=voyage,
                user=diana,
                defaults={
                    'role': 'admin',
                    'status': 'active',
                    'invited_by': bob,
                    'joined_at': timezone.now(),
                }
            )
            self.stdout.write('   ✅ Groupe "Voyage Espagne 2025" créé')
        else:
            self.stdout.write('   ⏭️  Groupe "Voyage Espagne 2025" existe déjà')
        
        # ========================================
        # 6. TRANSACTIONS DE GROUPE
        # ========================================
        self.stdout.write('💰 Création des transactions de groupe...')
        
        # Transactions pour la colocation
        coloc_transactions = [
            {'user': alice, 'category': categories['housing'], 'amount': 1500, 'description': 'Loyer Janvier', 'date': today - timedelta(days=60)},
            {'user': bob, 'category': categories['bills'], 'amount': 120, 'description': 'Facture électricité', 'date': today - timedelta(days=55)},
            {'user': charlie, 'category': categories['bills'], 'amount': 45, 'description': 'Internet', 'date': today - timedelta(days=50)},
            {'user': alice, 'category': categories['housing'], 'amount': 1500, 'description': 'Loyer Février', 'date': today - timedelta(days=30)},
            {'user': bob, 'category': categories['food'], 'amount': 85, 'description': 'Courses communes', 'date': today - timedelta(days=25)},
            {'user': charlie, 'category': categories['bills'], 'amount': 130, 'description': 'Facture électricité', 'date': today - timedelta(days=20)},
            {'user': alice, 'category': categories['food'], 'amount': 65, 'description': 'Dîner commun', 'date': today - timedelta(days=10)},
            {'user': bob, 'category': categories['shopping'], 'amount': 45, 'description': 'Produits ménagers', 'date': today - timedelta(days=5)},
        ]
        
        Transaction.objects.filter(group=coloc).delete()
        ExpenseSplit.objects.filter(transaction__group=coloc).delete()
        
        for tx_data in coloc_transactions:
            if tx_data['category']:
                tx = Transaction.objects.create(
                    user=tx_data['user'],
                    group=coloc,
                    category=tx_data['category'],
                    amount=Decimal(str(tx_data['amount'])),
                    type='expense',
                    description=tx_data['description'],
                    date=tx_data['date'],
                )
                
                # Créer les splits (partage égal entre 3 personnes)
                split_amount = Decimal(str(tx_data['amount'])) / 3
                for member in [alice, bob, charlie]:
                    ExpenseSplit.objects.create(
                        transaction=tx,
                        user=member,
                        amount=split_amount.quantize(Decimal('0.01')),
                        is_paid=(member == tx_data['user']),
                        paid_at=timezone.now() if member == tx_data['user'] else None,
                    )
        
        self.stdout.write(f'   ✅ {len(coloc_transactions)} transactions de colocation créées')
        
        # Transactions pour le voyage
        voyage_transactions = [
            {'user': bob, 'category': categories['travel'], 'amount': 450, 'description': 'Billets avion', 'date': today - timedelta(days=40)},
            {'user': alice, 'category': categories['travel'], 'amount': 280, 'description': 'Hôtel 3 nuits', 'date': today - timedelta(days=35)},
            {'user': diana, 'category': categories['entertainment'], 'amount': 90, 'description': 'Billets Sagrada Familia', 'date': today - timedelta(days=30)},
        ]
        
        Transaction.objects.filter(group=voyage).delete()
        
        for tx_data in voyage_transactions:
            if tx_data['category']:
                tx = Transaction.objects.create(
                    user=tx_data['user'],
                    group=voyage,
                    category=tx_data['category'],
                    amount=Decimal(str(tx_data['amount'])),
                    type='expense',
                    description=tx_data['description'],
                    date=tx_data['date'],
                )
                
                # Split entre 3 personnes
                split_amount = Decimal(str(tx_data['amount'])) / 3
                for member in [alice, bob, diana]:
                    ExpenseSplit.objects.create(
                        transaction=tx,
                        user=member,
                        amount=split_amount.quantize(Decimal('0.01')),
                        is_paid=(member == tx_data['user']),
                    )
        
        self.stdout.write(f'   ✅ {len(voyage_transactions)} transactions de voyage créées')
        
        # ========================================
        # 7. CRÉATION DES RAPPELS
        # ========================================
        self.stdout.write('🔔 Création des rappels...')
        
        Reminder.objects.filter(user__in=users).delete()
        
        reminders_data = [
            # Rappels pour Alice
            {'user': alice, 'title': 'Payer le loyer', 'type': 'payment', 'amount': 850, 'date': today + timedelta(days=5), 'recurring': True, 'config': {'frequency': 'monthly', 'day_of_month': 5}},
            {'user': alice, 'title': 'Facture électricité', 'type': 'bill', 'amount': 50, 'date': today + timedelta(days=10), 'recurring': True, 'config': {'frequency': 'monthly', 'day_of_month': 15}},
            {'user': alice, 'title': 'Renouveler abonnement Netflix', 'type': 'bill', 'amount': 15, 'date': today + timedelta(days=3), 'recurring': True, 'config': {'frequency': 'monthly', 'day_of_month': 20}},
            {'user': alice, 'title': 'RDV dentiste', 'type': 'general', 'amount': None, 'date': today + timedelta(days=14), 'recurring': False, 'config': None},
            {'user': alice, 'title': 'Déclaration impôts', 'type': 'general', 'amount': None, 'date': today + timedelta(days=30), 'recurring': False, 'config': None},
            
            # Rappels pour Bob
            {'user': bob, 'title': 'Payer le loyer', 'type': 'payment', 'amount': 650, 'date': today + timedelta(days=5), 'recurring': True, 'config': {'frequency': 'monthly', 'day_of_month': 5}},
            {'user': bob, 'title': 'Assurance voiture', 'type': 'bill', 'amount': 85, 'date': today + timedelta(days=20), 'recurring': True, 'config': {'frequency': 'monthly', 'day_of_month': 25}},
            
            # Rappels terminés (pour les stats)
            {'user': alice, 'title': 'Payer facture eau', 'type': 'bill', 'amount': 35, 'date': today - timedelta(days=5), 'recurring': False, 'config': None, 'completed': True},
            {'user': alice, 'title': 'Rembourser Bob', 'type': 'payment', 'amount': 20, 'date': today - timedelta(days=10), 'recurring': False, 'config': None, 'completed': True},
        ]
        
        for rem_data in reminders_data:
            reminder = Reminder.objects.create(
                user=rem_data['user'],
                title=rem_data['title'],
                reminder_type=rem_data['type'],
                amount=Decimal(str(rem_data['amount'])) if rem_data['amount'] else None,
                reminder_date=timezone.make_aware(timezone.datetime.combine(rem_data['date'], timezone.datetime.min.time())),
                is_recurring=rem_data['recurring'],
                recurring_config=rem_data['config'],
                is_completed=rem_data.get('completed', False),
                completed_at=timezone.now() if rem_data.get('completed') else None,
            )
        
        self.stdout.write(f'   ✅ {len(reminders_data)} rappels créés')
        
        # ========================================
        # 8. CRÉATION DES ÉVÉNEMENTS
        # ========================================
        self.stdout.write('📅 Création des événements...')
        
        Event.objects.filter(user__in=users).delete()
        
        events_data = [
            # Événements pour Alice
            {'user': alice, 'title': 'Réunion budget mensuel', 'start': today + timedelta(days=2, hours=14), 'end': today + timedelta(days=2, hours=15), 'all_day': False, 'color': '#3B82F6'},
            {'user': alice, 'title': 'Anniversaire Maman', 'start': today + timedelta(days=7), 'end': today + timedelta(days=7), 'all_day': True, 'color': '#EC4899'},
            {'user': alice, 'title': 'Voyage Lyon', 'start': today + timedelta(days=14), 'end': today + timedelta(days=16), 'all_day': True, 'color': '#10B981'},
            {'user': alice, 'title': 'RDV banque', 'start': today + timedelta(days=5, hours=10), 'end': today + timedelta(days=5, hours=11), 'all_day': False, 'color': '#F59E0B'},
            {'user': alice, 'title': 'Dîner colocation', 'start': today + timedelta(days=3, hours=20), 'end': today + timedelta(days=3, hours=23), 'all_day': False, 'color': '#8B5CF6'},
            
            # Événements passés
            {'user': alice, 'title': 'Concert', 'start': today - timedelta(days=5, hours=-20), 'end': today - timedelta(days=5, hours=-23), 'all_day': False, 'color': '#EF4444'},
            {'user': alice, 'title': 'Week-end Normandie', 'start': today - timedelta(days=14), 'end': today - timedelta(days=12), 'all_day': True, 'color': '#10B981'},
            
            # Événements pour Bob
            {'user': bob, 'title': 'Match de foot', 'start': today + timedelta(days=4, hours=18), 'end': today + timedelta(days=4, hours=20), 'all_day': False, 'color': '#10B981'},
            {'user': bob, 'title': 'Voyage Barcelone', 'start': today + timedelta(days=30), 'end': today + timedelta(days=35), 'all_day': True, 'color': '#F59E0B'},
        ]
        
        for evt_data in events_data:
            start_date = evt_data['start'] if isinstance(evt_data['start'], timezone.datetime) else timezone.datetime.combine(evt_data['start'], timezone.datetime.min.time())
            end_date = evt_data['end'] if isinstance(evt_data['end'], timezone.datetime) else timezone.datetime.combine(evt_data['end'], timezone.datetime.max.time())
            
            if timezone.is_naive(start_date):
                start_date = timezone.make_aware(start_date)
            if timezone.is_naive(end_date):
                end_date = timezone.make_aware(end_date)
            
            Event.objects.create(
                user=evt_data['user'],
                title=evt_data['title'],
                start_date=start_date,
                end_date=end_date,
                all_day=evt_data['all_day'],
                color=evt_data['color'],
            )
        
        self.stdout.write(f'   ✅ {len(events_data)} événements créés')
        
        # ========================================
        # 9. INVITATIONS EN ATTENTE
        # ========================================
        self.stdout.write('✉️ Création des invitations...')
        
        GroupInvitation.objects.filter(group__in=[coloc, voyage]).delete()
        
        # Invitation en attente pour le groupe colocation
        GroupInvitation.objects.create(
            group=coloc,
            email='newmember@example.com',
            invited_by=alice,
            expires_at=timezone.now() + timedelta(days=7),
        )
        
        self.stdout.write('   ✅ 1 invitation créée')
        
        # ========================================
        # RÉSUMÉ FINAL
        # ========================================
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('🎉 DONNÉES DE TEST CRÉÉES AVEC SUCCÈS!'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write('')
        self.stdout.write('📊 Résumé:')
        self.stdout.write(f'   👤 Utilisateurs: 4')
        self.stdout.write(f'   📁 Catégories: {Category.objects.count()} (dont 2 personnalisées)')
        self.stdout.write(f'   💰 Transactions: {Transaction.objects.count()}')
        self.stdout.write(f'   👥 Groupes: 2')
        self.stdout.write(f'   🔔 Rappels: {Reminder.objects.count()}')
        self.stdout.write(f'   📅 Événements: {Event.objects.count()}')
        self.stdout.write('')
        self.stdout.write('🔑 Comptes de test:')
        self.stdout.write('   ┌────────────────────────┬─────────────────┐')
        self.stdout.write('   │ Email                  │ Mot de passe    │')
        self.stdout.write('   ├────────────────────────┼─────────────────┤')
        self.stdout.write('   │ alice@example.com      │ TestPass123!    │')
        self.stdout.write('   │ bob@example.com        │ TestPass123!    │')
        self.stdout.write('   │ charlie@example.com    │ TestPass123!    │')
        self.stdout.write('   │ diana@example.com      │ TestPass123!    │')
        self.stdout.write('   └────────────────────────┴─────────────────┘')
        self.stdout.write('')
        self.stdout.write('🚀 Testez maintenant avec Postman!')