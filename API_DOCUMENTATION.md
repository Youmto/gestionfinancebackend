# Documentation API - Finance Management Application

**Version:** 1.0.0
**Base URL:** `http://localhost:8000/api/v1`
**Backend:** Django REST Framework
**Authentication:** JWT (JSON Web Tokens)

---

## Table des matières

1. [Authentication & Users](#1-authentication--users)
2. [Categories](#2-categories)
3. [Transactions](#3-transactions)
4. [Dashboard & Statistics](#4-dashboard--statistics)
5. [Groups](#5-groups)
6. [Reminders](#6-reminders)
7. [Events](#7-events)
8. [Payments (Mobile Money)](#8-payments-mobile-money)
9. [Exports](#9-exports)
10. [Codes d'erreur](#10-codes-derreur)
11. [Pagination](#11-pagination)

---

## 1. Authentication & Users

### 1.1. Inscription utilisateur

**Endpoint:** `POST /api/v1/auth/register/`
**Authentification:** Non requise
**Description:** Crée un nouveau compte utilisateur.

**Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "currency": "XAF"
}
```

**Réponse (201 Created):**
```json
{
  "success": true,
  "message": "Compte créé avec succès.",
  "data": {
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "full_name": "John Doe",
      "phone_number": null,
      "currency": "XAF",
      "avatar": null,
      "is_verified": false,
      "created_at": "2026-01-16T10:30:00Z",
      "last_login": null
    },
    "tokens": {
      "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
      "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
  }
}
```

---

### 1.2. Connexion

**Endpoint:** `POST /api/v1/auth/login/`
**Authentification:** Non requise

**Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Réponse (200 OK):**
```json
{
  "success": true,
  "message": "Connexion réussie",
  "data": {
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "full_name": "John Doe",
      "phone_number": "+237690000000",
      "currency": "XAF",
      "avatar": "https://example.com/avatar.jpg",
      "is_verified": true,
      "created_at": "2026-01-16T10:30:00Z",
      "last_login": "2026-01-16T14:30:00Z"
    },
    "tokens": {
      "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
      "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
  }
}
```

**Erreur (401 Unauthorized):**
```json
{
  "success": false,
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Email ou mot de passe incorrect"
  }
}
```

---

### 1.3. Envoi de code OTP

**Endpoint:** `POST /api/v1/auth/send-code/`
**Authentification:** Non requise
**Description:** Envoie un code de vérification à 6 chiffres par email.

**Body:**
```json
{
  "email": "user@example.com",
  "purpose": "registration"
}
```

**Purposes disponibles:**
- `registration` - Inscription
- `login` - Connexion sans mot de passe
- `password_reset` - Réinitialisation mot de passe
- `email_change` - Changement d'email

**Réponse (200 OK):**
```json
{
  "message": "Code de vérification envoyé avec succès.",
  "email": "user@example.com",
  "expires_in": 900,
  "purpose": "registration"
}
```

**Erreur (429 Too Many Requests):**
```json
{
  "error": "Un code a déjà été envoyé. Veuillez attendre.",
  "retry_after": 45
}
```

---

### 1.4. Vérification de code OTP

**Endpoint:** `POST /api/v1/auth/verify-code/`
**Authentification:** Non requise

**Body:**
```json
{
  "email": "user@example.com",
  "code": "123456",
  "purpose": "registration"
}
```

**Réponse (200 OK) - Purpose: registration:**
```json
{
  "verified": true,
  "message": "Code vérifié avec succès.",
  "email": "user@example.com",
  "purpose": "registration",
  "can_create_account": true
}
```

**Réponse (200 OK) - Purpose: login:**
```json
{
  "verified": true,
  "message": "Code vérifié avec succès.",
  "email": "user@example.com",
  "purpose": "login",
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  },
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```

**Erreur (400 Bad Request):**
```json
{
  "verified": false,
  "error": "Code incorrect. 3 tentative(s) restante(s).",
  "remaining_attempts": 3
}
```

---

### 1.5. Inscription avec code

**Endpoint:** `POST /api/v1/auth/register-with-code/`
**Authentification:** Non requise

**Body:**
```json
{
  "email": "user@example.com",
  "code": "123456",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Réponse (201 Created):**
```json
{
  "message": "Compte créé avec succès.",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_verified": true
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

---

### 1.6. Déconnexion

**Endpoint:** `POST /api/v1/auth/logout/`
**Authentification:** Requise (Bearer Token)

**Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Réponse (200 OK):**
```json
{
  "success": true,
  "message": "Déconnexion réussie"
}
```

---

### 1.7. Rafraîchir le token

**Endpoint:** `POST /api/v1/auth/token/refresh/`
**Authentification:** Non requise

**Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Réponse (200 OK):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

---

### 1.8. Obtenir le profil

**Endpoint:** `GET /api/v1/auth/me/`
**Authentification:** Requise

**Réponse (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe",
  "phone_number": "+237690000000",
  "currency": "XAF",
  "avatar": "https://example.com/avatar.jpg",
  "is_verified": true,
  "created_at": "2026-01-16T10:30:00Z",
  "last_login": "2026-01-16T14:30:00Z"
}
```

---

### 1.9. Mettre à jour le profil

**Endpoint:** `PATCH /api/v1/auth/me/`
**Authentification:** Requise

**Body:**
```json
{
  "first_name": "Jean",
  "last_name": "Dupont",
  "phone_number": "+237690000000",
  "currency": "EUR",
  "avatar": "https://example.com/new-avatar.jpg"
}
```

**Réponse (200 OK):** Retourne le profil mis à jour (même format que GET)

---

### 1.10. Changer le mot de passe

**Endpoint:** `PUT /api/v1/auth/change-password/`
**Authentification:** Requise

**Body:**
```json
{
  "old_password": "OldPass123!",
  "new_password": "NewPass456!",
  "new_password_confirm": "NewPass456!"
}
```

**Réponse (200 OK):**
```json
{
  "success": true,
  "message": "Mot de passe changé avec succès"
}
```

---

### 1.11. Préférences de notification

**Endpoint:** `GET /api/v1/auth/me/notifications/`
**Authentification:** Requise

**Réponse (200 OK):**
```json
{
  "email_reminders": true,
  "email_group_activity": true,
  "email_weekly_summary": true,
  "email_budget_alerts": true,
  "email_payment_notifications": true,
  "push_enabled": false,
  "reminder_time": "09:00:00"
}
```

**Mise à jour (PATCH):**
```json
{
  "email_budget_alerts": false,
  "reminder_time": "08:00:00"
}
```

---

## 2. Categories

### 2.1. Lister les catégories

**Endpoint:** `GET /api/v1/finances/categories/`
**Authentification:** Requise
**Description:** Retourne les catégories système et personnalisées de l'utilisateur.

**Paramètres de requête (optionnels):**
- `type` - Filtrer par type: `income`, `expense`, `both`
- `page` - Numéro de page
- `page_size` - Nombre d'éléments par page

**Réponse (200 OK):**
```json
{
  "count": 17,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "650e8400-e29b-41d4-a716-446655440001",
      "name": "Alimentation",
      "description": "Courses alimentaires, restaurants et livraisons",
      "icon": "🍔",
      "color": "#F59E0B",
      "type": "expense",
      "budget": "50000.00",
      "budget_alert_threshold": 80,
      "budget_status": {
        "budget": 50000.00,
        "spent": 35000.00,
        "remaining": 15000.00,
        "percentage": 70.00,
        "is_over_budget": false,
        "is_alert": false,
        "alert_threshold": 80
      },
      "is_system": true,
      "transaction_count": 45,
      "created_at": "2026-01-01T00:00:00Z"
    },
    {
      "id": "650e8400-e29b-41d4-a716-446655440002",
      "name": "Transport",
      "description": "Carburant, transports en commun, taxi",
      "icon": "🚗",
      "color": "#3B82F6",
      "type": "expense",
      "budget": null,
      "budget_alert_threshold": 80,
      "budget_status": null,
      "is_system": true,
      "transaction_count": 28,
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

---

### 2.2. Créer une catégorie personnalisée

**Endpoint:** `POST /api/v1/finances/categories/`
**Authentification:** Requise

**Body:**
```json
{
  "name": "Investissements Crypto",
  "description": "Trading et investissements en cryptomonnaies",
  "icon": "₿",
  "color": "#F7931A",
  "type": "both",
  "budget": "100000.00",
  "budget_alert_threshold": 90
}
```

**Réponse (201 Created):**
```json
{
  "id": "750e8400-e29b-41d4-a716-446655440010",
  "name": "Investissements Crypto",
  "description": "Trading et investissements en cryptomonnaies",
  "icon": "₿",
  "color": "#F7931A",
  "type": "both",
  "budget": "100000.00",
  "budget_alert_threshold": 90,
  "budget_status": null,
  "is_system": false,
  "transaction_count": 0,
  "created_at": "2026-01-16T14:30:00Z"
}
```

---

### 2.3. Statut du budget d'une catégorie

**Endpoint:** `GET /api/v1/finances/categories/:id/budget_status/`
**Authentification:** Requise

**Paramètres de requête (optionnels):**
- `year` - Année (défaut: année courante)
- `month` - Mois 1-12 (défaut: mois courant)

**Exemple:** `GET /api/v1/finances/categories/650e8400.../budget_status/?year=2026&month=1`

**Réponse (200 OK):**
```json
{
  "category": {
    "id": "650e8400-e29b-41d4-a716-446655440001",
    "name": "Alimentation",
    "icon": "🍔",
    "color": "#F59E0B"
  },
  "period": {
    "year": 2026,
    "month": 1
  },
  "has_budget": true,
  "budget": 50000.00,
  "spent": 42500.00,
  "remaining": 7500.00,
  "percentage": 85.00,
  "is_over_budget": false,
  "is_alert": true,
  "alert_threshold": 80,
  "recent_transactions": [
    {
      "id": "850e8400-e29b-41d4-a716-446655440020",
      "amount": "5000.00",
      "signed_amount": "-5000.00",
      "type": "expense",
      "category": "650e8400-e29b-41d4-a716-446655440001",
      "category_name": "Alimentation",
      "category_icon": "🍔",
      "category_color": "#F59E0B",
      "description": "Courses du mois",
      "date": "2026-01-15",
      "group": null,
      "group_name": null,
      "is_recurring": false,
      "created_at": "2026-01-15T18:30:00Z"
    }
  ]
}
```

---

### 2.4. Aperçu de tous les budgets

**Endpoint:** `GET /api/v1/finances/categories/budget_overview/`
**Authentification:** Requise

**Paramètres de requête (optionnels):**
- `year` - Année
- `month` - Mois 1-12

**Réponse (200 OK):**
```json
{
  "period": {
    "year": 2026,
    "month": 1
  },
  "summary": {
    "total_budget": 200000.00,
    "total_spent": 145000.00,
    "total_remaining": 55000.00,
    "overall_percentage": 72.50,
    "categories_count": 5,
    "alerts_count": 2,
    "over_budget_count": 0
  },
  "categories": [
    {
      "id": "650e8400-e29b-41d4-a716-446655440001",
      "name": "Alimentation",
      "description": "Courses alimentaires, restaurants",
      "icon": "🍔",
      "color": "#F59E0B",
      "budget": 50000.00,
      "spent": 42500.00,
      "remaining": 7500.00,
      "percentage": 85.00,
      "is_over_budget": false,
      "is_alert": true,
      "alert_threshold": 80
    },
    {
      "id": "650e8400-e29b-41d4-a716-446655440003",
      "name": "Logement",
      "description": "Loyer, charges, entretien",
      "icon": "🏠",
      "color": "#8B5CF6",
      "budget": 80000.00,
      "spent": 60000.00,
      "remaining": 20000.00,
      "percentage": 75.00,
      "is_over_budget": false,
      "is_alert": false,
      "alert_threshold": 80
    }
  ]
}
```

---

### 2.5. Alertes budget

**Endpoint:** `GET /api/v1/finances/categories/budget_alerts/`
**Authentification:** Requise

**Réponse (200 OK):**
```json
{
  "period": {
    "year": 2026,
    "month": 1
  },
  "over_budget": [
    {
      "id": "650e8400-e29b-41d4-a716-446655440005",
      "name": "Divertissement",
      "description": "Cinéma, sorties, loisirs",
      "icon": "🎬",
      "color": "#EC4899",
      "budget": 30000.00,
      "spent": 35000.00,
      "remaining": -5000.00,
      "percentage": 116.67,
      "is_over_budget": true,
      "is_alert": true,
      "alert_threshold": 80
    }
  ],
  "alerts": [
    {
      "id": "650e8400-e29b-41d4-a716-446655440001",
      "name": "Alimentation",
      "icon": "🍔",
      "color": "#F59E0B",
      "budget": 50000.00,
      "spent": 42500.00,
      "remaining": 7500.00,
      "percentage": 85.00,
      "is_over_budget": false,
      "is_alert": true,
      "alert_threshold": 80
    }
  ],
  "healthy": [
    {
      "id": "650e8400-e29b-41d4-a716-446655440003",
      "name": "Logement",
      "icon": "🏠",
      "color": "#8B5CF6",
      "budget": 80000.00,
      "spent": 60000.00,
      "remaining": 20000.00,
      "percentage": 75.00,
      "is_over_budget": false,
      "is_alert": false,
      "alert_threshold": 80
    }
  ],
  "summary": {
    "over_budget_count": 1,
    "alerts_count": 1,
    "healthy_count": 1
  }
}
```

---

## 3. Transactions

### 3.1. Lister les transactions

**Endpoint:** `GET /api/v1/finances/transactions/`
**Authentification:** Requise

**Paramètres de requête (optionnels):**
- `type` - `income` ou `expense`
- `category` - UUID de la catégorie
- `group` - UUID du groupe
- `date_from` - Date de début (YYYY-MM-DD)
- `date_to` - Date de fin (YYYY-MM-DD)
- `min_amount` - Montant minimum
- `max_amount` - Montant maximum
- `search` - Recherche dans la description
- `ordering` - Tri: `date`, `-date`, `amount`, `-amount`, `created_at`, `-created_at`
- `page` - Numéro de page
- `page_size` - Taille de la page (défaut: 20)

**Exemple:** `GET /api/v1/finances/transactions/?type=expense&date_from=2026-01-01&ordering=-date`

**Réponse (200 OK):**
```json
{
  "count": 156,
  "next": "http://localhost:8000/api/v1/finances/transactions/?page=2",
  "previous": null,
  "results": [
    {
      "id": "850e8400-e29b-41d4-a716-446655440020",
      "amount": "5000.00",
      "signed_amount": "-5000.00",
      "type": "expense",
      "category": "650e8400-e29b-41d4-a716-446655440001",
      "category_name": "Alimentation",
      "category_icon": "🍔",
      "category_color": "#F59E0B",
      "description": "Courses du mois",
      "date": "2026-01-15",
      "group": null,
      "group_name": null,
      "is_recurring": false,
      "created_at": "2026-01-15T18:30:00Z"
    },
    {
      "id": "850e8400-e29b-41d4-a716-446655440021",
      "amount": "150000.00",
      "signed_amount": "150000.00",
      "type": "income",
      "category": "650e8400-e29b-41d4-a716-446655440011",
      "category_name": "Salaire",
      "category_icon": "💰",
      "category_color": "#22C55E",
      "description": "Salaire mensuel janvier 2026",
      "date": "2026-01-01",
      "group": null,
      "group_name": null,
      "is_recurring": true,
      "created_at": "2026-01-01T08:00:00Z"
    }
  ]
}
```

---

### 3.2. Créer une transaction

**Endpoint:** `POST /api/v1/finances/transactions/`
**Authentification:** Requise

**Body:**
```json
{
  "category": "650e8400-e29b-41d4-a716-446655440001",
  "amount": "12500.00",
  "type": "expense",
  "description": "Restaurant avec amis",
  "date": "2026-01-16",
  "group": null,
  "is_recurring": false,
  "recurring_config": null,
  "attachment": null
}
```

**Body - Transaction récurrente:**
```json
{
  "category": "650e8400-e29b-41d4-a716-446655440011",
  "amount": "150000.00",
  "type": "income",
  "description": "Salaire mensuel",
  "date": "2026-02-01",
  "is_recurring": true,
  "recurring_config": {
    "frequency": "monthly",
    "interval": 1,
    "day_of_month": 1,
    "end_date": null
  }
}
```

**Réponse (201 Created):**
```json
{
  "id": "850e8400-e29b-41d4-a716-446655440025",
  "user": "550e8400-e29b-41d4-a716-446655440000",
  "user_details": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "avatar": null
  },
  "group": null,
  "category": "650e8400-e29b-41d4-a716-446655440001",
  "category_details": {
    "id": "650e8400-e29b-41d4-a716-446655440001",
    "name": "Alimentation",
    "icon": "🍔",
    "color": "#F59E0B",
    "type": "expense"
  },
  "amount": "12500.00",
  "signed_amount": "-12500.00",
  "type": "expense",
  "description": "Restaurant avec amis",
  "date": "2026-01-16",
  "is_recurring": false,
  "recurring_config": null,
  "attachment": null,
  "is_personal": true,
  "splits_count": 0,
  "created_at": "2026-01-16T19:30:00Z",
  "updated_at": "2026-01-16T19:30:00Z"
}
```

---

### 3.3. Obtenir une transaction

**Endpoint:** `GET /api/v1/finances/transactions/:id/`
**Authentification:** Requise

**Réponse (200 OK):** Même format que la réponse de création

---

### 3.4. Modifier une transaction

**Endpoint:** `PATCH /api/v1/finances/transactions/:id/`
**Authentification:** Requise

**Body:**
```json
{
  "amount": "15000.00",
  "description": "Restaurant + cinéma"
}
```

**Réponse (200 OK):** Transaction mise à jour

---

### 3.5. Supprimer une transaction

**Endpoint:** `DELETE /api/v1/finances/transactions/:id/`
**Authentification:** Requise
**Note:** Suppression douce (soft delete)

**Réponse (204 No Content)**

---

### 3.6. Partager une dépense de groupe

**Endpoint:** `POST /api/v1/finances/transactions/:id/split/`
**Authentification:** Requise
**Description:** Divise une dépense de groupe entre les membres.

**Body - Partage égal:**
```json
{
  "equal_split": true,
  "splits": []
}
```

**Body - Partage personnalisé:**
```json
{
  "equal_split": false,
  "splits": [
    {
      "user": "550e8400-e29b-41d4-a716-446655440000",
      "amount": "25000.00"
    },
    {
      "user": "550e8400-e29b-41d4-a716-446655440001",
      "amount": "15000.00"
    },
    {
      "user": "550e8400-e29b-41d4-a716-446655440002",
      "amount": "10000.00"
    }
  ]
}
```

**Réponse (201 Created):**
```json
[
  {
    "id": "950e8400-e29b-41d4-a716-446655440030",
    "transaction": "850e8400-e29b-41d4-a716-446655440025",
    "transaction_details": {
      "id": "850e8400-e29b-41d4-a716-446655440025",
      "description": "Restaurant groupe",
      "total_amount": "50000.00",
      "date": "2026-01-16"
    },
    "user": "550e8400-e29b-41d4-a716-446655440000",
    "user_details": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "full_name": "John Doe",
      "avatar": null
    },
    "amount": "25000.00",
    "is_paid": false,
    "paid_at": null,
    "created_at": "2026-01-16T20:00:00Z"
  }
]
```

---

### 3.7. Voir les partages d'une transaction

**Endpoint:** `GET /api/v1/finances/transactions/:id/splits/`
**Authentification:** Requise

**Réponse (200 OK):** Tableau des partages (même format que ci-dessus)

---

### 3.8. Marquer un partage comme payé

**Endpoint:** `PATCH /api/v1/finances/splits/:id/`
**Authentification:** Requise

**Body:**
```json
{
  "is_paid": true
}
```

**Réponse (200 OK):**
```json
{
  "is_paid": true
}
```

---

## 4. Dashboard & Statistics

### 4.1. Tableau de bord

**Endpoint:** `GET /api/v1/finances/dashboard/`
**Authentification:** Requise

**Réponse (200 OK):**
```json
{
  "total_balance": "125000.00",
  "total_income": "450000.00",
  "total_expense": "325000.00",
  "monthly_income": "150000.00",
  "monthly_expense": "98500.00",
  "recent_transactions": [
    {
      "id": "850e8400-e29b-41d4-a716-446655440020",
      "amount": "5000.00",
      "signed_amount": "-5000.00",
      "type": "expense",
      "category": "650e8400-e29b-41d4-a716-446655440001",
      "category_name": "Alimentation",
      "category_icon": "🍔",
      "category_color": "#F59E0B",
      "description": "Courses du mois",
      "date": "2026-01-15",
      "group": null,
      "group_name": null,
      "is_recurring": false,
      "created_at": "2026-01-15T18:30:00Z"
    }
  ],
  "expense_by_category": [
    {
      "category_id": "650e8400-e29b-41d4-a716-446655440001",
      "category_name": "Alimentation",
      "category_icon": "🍔",
      "category_color": "#F59E0B",
      "total": "42500.00",
      "count": 15,
      "percentage": 43.15
    },
    {
      "category_id": "650e8400-e29b-41d4-a716-446655440002",
      "category_name": "Transport",
      "category_icon": "🚗",
      "category_color": "#3B82F6",
      "total": "28000.00",
      "count": 8,
      "percentage": 28.43
    }
  ],
  "income_by_category": [
    {
      "category_id": "650e8400-e29b-41d4-a716-446655440011",
      "category_name": "Salaire",
      "category_icon": "💰",
      "category_color": "#22C55E",
      "total": "150000.00",
      "count": 1,
      "percentage": 100.00
    }
  ],
  "budget_alerts": [
    {
      "category_id": "650e8400-e29b-41d4-a716-446655440001",
      "category_name": "Alimentation",
      "category_icon": "🍔",
      "category_color": "#F59E0B",
      "budget": 50000.00,
      "spent": 42500.00,
      "remaining": 7500.00,
      "percentage": 85.00,
      "is_over_budget": false,
      "is_alert": true,
      "alert_threshold": 80
    }
  ]
}
```

---

### 4.2. Résumé mensuel

**Endpoint:** `GET /api/v1/finances/summary/`
**Authentification:** Requise

**Paramètres de requête:**
- `months` - Nombre de mois à afficher (défaut: 12, max: 24)

**Exemple:** `GET /api/v1/finances/summary/?months=6`

**Réponse (200 OK):**
```json
[
  {
    "year": 2026,
    "month": 1,
    "income": "150000.00",
    "expense": "98500.00",
    "balance": "51500.00",
    "transaction_count": 47
  },
  {
    "year": 2025,
    "month": 12,
    "income": "150000.00",
    "expense": "112000.00",
    "balance": "38000.00",
    "transaction_count": 52
  },
  {
    "year": 2025,
    "month": 11,
    "income": "150000.00",
    "expense": "95000.00",
    "balance": "55000.00",
    "transaction_count": 43
  }
]
```

---

### 4.3. Données pour graphiques

**Endpoint:** `GET /api/v1/finances/charts/`
**Authentification:** Requise

**Paramètres de requête:**
- `period` - `monthly` ou `weekly` (défaut: monthly)
- `count` - Nombre de périodes (défaut: 6, max: 12)

**Exemple:** `GET /api/v1/finances/charts/?period=monthly&count=6`

**Réponse (200 OK):**
```json
{
  "labels": ["Aoû 2025", "Sep 2025", "Oct 2025", "Nov 2025", "Déc 2025", "Jan 2026"],
  "income_data": ["150000.00", "150000.00", "150000.00", "150000.00", "150000.00", "150000.00"],
  "expense_data": ["92000.00", "88500.00", "103000.00", "95000.00", "112000.00", "98500.00"]
}
```

---

## 5. Groups

### 5.1. Lister les groupes

**Endpoint:** `GET /api/v1/groups/`
**Authentification:** Requise

**Réponse (200 OK):**
```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "a50e8400-e29b-41d4-a716-446655440100",
      "name": "Colocation Appartement",
      "description": "Gestion des dépenses communes de l'appartement",
      "owner": "550e8400-e29b-41d4-a716-446655440000",
      "owner_details": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "user@example.com",
        "full_name": "John Doe"
      },
      "image": null,
      "currency": "XAF",
      "is_active": true,
      "members_count": 4,
      "created_at": "2025-11-01T10:00:00Z",
      "updated_at": "2026-01-15T14:30:00Z"
    }
  ]
}
```

---

### 5.2. Créer un groupe

**Endpoint:** `POST /api/v1/groups/`
**Authentification:** Requise

**Body:**
```json
{
  "name": "Vacances Été 2026",
  "description": "Budget vacances entre amis",
  "currency": "EUR",
  "image": "https://example.com/group-image.jpg"
}
```

**Réponse (201 Created):**
```json
{
  "id": "a50e8400-e29b-41d4-a716-446655440105",
  "name": "Vacances Été 2026",
  "description": "Budget vacances entre amis",
  "owner": "550e8400-e29b-41d4-a716-446655440000",
  "owner_details": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "full_name": "John Doe"
  },
  "image": "https://example.com/group-image.jpg",
  "currency": "EUR",
  "is_active": true,
  "members_count": 1,
  "created_at": "2026-01-16T20:30:00Z",
  "updated_at": "2026-01-16T20:30:00Z"
}
```

---

### 5.3. Inviter un membre

**Endpoint:** `POST /api/v1/groups/:groupId/invite/`
**Authentification:** Requise
**Permissions:** Admin du groupe

**Body:**
```json
{
  "email": "friend@example.com"
}
```

**Réponse (200 OK):**
```json
{
  "message": "Invitation envoyée avec succès.",
  "invitation": {
    "id": "b50e8400-e29b-41d4-a716-446655440200",
    "email": "friend@example.com",
    "token": "xyzABC123...",
    "status": "pending",
    "expires_at": "2026-01-23T20:30:00Z",
    "created_at": "2026-01-16T20:30:00Z"
  }
}
```

---

### 5.4. Accepter une invitation

**Endpoint:** `POST /api/v1/groups/invitations/:token/`
**Authentification:** Requise

**Réponse (200 OK):**
```json
{
  "message": "Vous avez rejoint le groupe avec succès.",
  "group": {
    "id": "a50e8400-e29b-41d4-a716-446655440105",
    "name": "Vacances Été 2026",
    "description": "Budget vacances entre amis"
  },
  "membership": {
    "role": "member",
    "status": "active",
    "joined_at": "2026-01-17T09:00:00Z"
  }
}
```

---

### 5.5. Membres du groupe

**Endpoint:** `GET /api/v1/groups/:groupId/members/`
**Authentification:** Requise

**Réponse (200 OK):**
```json
[
  {
    "id": "c50e8400-e29b-41d4-a716-446655440300",
    "user": "550e8400-e29b-41d4-a716-446655440000",
    "user_details": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "full_name": "John Doe",
      "avatar": null
    },
    "role": "admin",
    "status": "active",
    "invited_by": null,
    "joined_at": "2025-11-01T10:00:00Z",
    "created_at": "2025-11-01T10:00:00Z"
  },
  {
    "id": "c50e8400-e29b-41d4-a716-446655440301",
    "user": "550e8400-e29b-41d4-a716-446655440001",
    "user_details": {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "email": "friend@example.com",
      "first_name": "Jane",
      "last_name": "Smith",
      "full_name": "Jane Smith",
      "avatar": null
    },
    "role": "member",
    "status": "active",
    "invited_by": "550e8400-e29b-41d4-a716-446655440000",
    "joined_at": "2025-11-02T14:30:00Z",
    "created_at": "2025-11-02T14:30:00Z"
  }
]
```

---

### 5.6. Solde du groupe

**Endpoint:** `GET /api/v1/groups/:groupId/balance/`
**Authentification:** Requise

**Réponse (200 OK):**
```json
{
  "income": "250000.00",
  "expense": "185000.00",
  "balance": "65000.00",
  "currency": "XAF"
}
```

---

### 5.7. Transactions du groupe

**Endpoint:** `GET /api/v1/groups/:groupId/transactions/`
**Authentification:** Requise

**Paramètres de requête:** Mêmes filtres que pour les transactions personnelles

**Réponse (200 OK):** Même format que la liste de transactions

---

### 5.8. Quitter un groupe

**Endpoint:** `POST /api/v1/groups/:groupId/leave/`
**Authentification:** Requise

**Réponse (200 OK):**
```json
{
  "message": "Vous avez quitté le groupe avec succès."
}
```

---

## 6. Reminders

### 6.1. Lister les rappels

**Endpoint:** `GET /api/v1/reminders/`
**Authentification:** Requise

**Paramètres de requête (optionnels):**
- `reminder_type` - `payment`, `bill`, `general`
- `is_completed` - `true` ou `false`
- `group` - UUID du groupe
- `page` - Numéro de page
- `page_size` - Taille de la page

**Réponse (200 OK):**
```json
{
  "count": 12,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "d50e8400-e29b-41d4-a716-446655440400",
      "user": "550e8400-e29b-41d4-a716-446655440000",
      "group": null,
      "title": "Paiement loyer février",
      "description": "Ne pas oublier de payer le loyer avant le 1er",
      "reminder_type": "payment",
      "reminder_date": "2026-01-30T09:00:00Z",
      "amount": "80000.00",
      "is_recurring": true,
      "recurring_config": {
        "frequency": "monthly",
        "interval": 1,
        "day_of_month": 30,
        "end_date": null
      },
      "is_completed": false,
      "completed_at": null,
      "notification_sent": false,
      "notification_sent_at": null,
      "created_at": "2026-01-01T10:00:00Z",
      "updated_at": "2026-01-01T10:00:00Z"
    }
  ]
}
```

---

### 6.2. Créer un rappel

**Endpoint:** `POST /api/v1/reminders/`
**Authentification:** Requise

**Body:**
```json
{
  "title": "Paiement loyer février",
  "description": "Ne pas oublier de payer le loyer",
  "reminder_type": "payment",
  "reminder_date": "2026-01-30T09:00:00Z",
  "amount": "80000.00",
  "group": null,
  "is_recurring": true,
  "recurring_config": {
    "frequency": "monthly",
    "interval": 1,
    "day_of_month": 30,
    "end_date": null
  }
}
```

**Réponse (201 Created):** Rappel créé (même format que ci-dessus)

---

### 6.3. Marquer comme terminé

**Endpoint:** `POST /api/v1/reminders/:id/complete/`
**Authentification:** Requise

**Réponse (200 OK):**
```json
{
  "message": "Rappel marqué comme terminé.",
  "is_completed": true,
  "completed_at": "2026-01-16T21:00:00Z"
}
```

---

### 6.4. Rappels à venir

**Endpoint:** `GET /api/v1/reminders/upcoming/`
**Authentification:** Requise

**Paramètres de requête:**
- `days` - Nombre de jours à regarder (défaut: 7)

**Exemple:** `GET /api/v1/reminders/upcoming/?days=14`

**Réponse (200 OK):**
```json
[
  {
    "id": "d50e8400-e29b-41d4-a716-446655440401",
    "title": "Renouvellement assurance",
    "reminder_type": "bill",
    "reminder_date": "2026-01-20T10:00:00Z",
    "amount": "15000.00",
    "is_completed": false
  },
  {
    "id": "d50e8400-e29b-41d4-a716-446655440400",
    "title": "Paiement loyer février",
    "reminder_type": "payment",
    "reminder_date": "2026-01-30T09:00:00Z",
    "amount": "80000.00",
    "is_completed": false
  }
]
```

---

### 6.5. Statistiques

**Endpoint:** `GET /api/v1/reminders/stats/`
**Authentification:** Requise

**Réponse (200 OK):**
```json
{
  "total": 12,
  "completed": 5,
  "pending": 7,
  "overdue": 2,
  "upcoming_7_days": 3,
  "by_type": {
    "payment": 4,
    "bill": 6,
    "general": 2
  }
}
```

---

## 7. Events

### 7.1. Lister les événements

**Endpoint:** `GET /api/v1/events/`
**Authentification:** Requise

**Paramètres de requête (optionnels):**
- `start_date` - Date de début (YYYY-MM-DD)
- `end_date` - Date de fin (YYYY-MM-DD)
- `page` - Numéro de page
- `page_size` - Taille de la page

**Réponse (200 OK):**
```json
{
  "count": 8,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "e50e8400-e29b-41d4-a716-446655440500",
      "user": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Réunion budget familial",
      "description": "Discussion mensuelle sur les finances",
      "start_date": "2026-01-25T19:00:00Z",
      "end_date": "2026-01-25T20:30:00Z",
      "all_day": false,
      "color": "#3B82F6",
      "transaction": null,
      "reminder": null,
      "created_at": "2026-01-10T15:00:00Z",
      "updated_at": "2026-01-10T15:00:00Z"
    }
  ]
}
```

---

### 7.2. Créer un événement

**Endpoint:** `POST /api/v1/events/`
**Authentification:** Requise

**Body:**
```json
{
  "title": "Réunion budget familial",
  "description": "Discussion mensuelle sur les finances",
  "start_date": "2026-01-25T19:00:00Z",
  "end_date": "2026-01-25T20:30:00Z",
  "all_day": false,
  "color": "#3B82F6",
  "transaction": null,
  "reminder": null
}
```

**Réponse (201 Created):** Événement créé

---

### 7.3. Calendrier mensuel

**Endpoint:** `GET /api/v1/events/calendar/:year/:month/`
**Authentification:** Requise

**Exemple:** `GET /api/v1/events/calendar/2026/1/`

**Réponse (200 OK):**
```json
{
  "year": 2026,
  "month": 1,
  "events": [
    {
      "id": "e50e8400-e29b-41d4-a716-446655440500",
      "title": "Réunion budget familial",
      "start_date": "2026-01-25T19:00:00Z",
      "end_date": "2026-01-25T20:30:00Z",
      "all_day": false,
      "color": "#3B82F6"
    },
    {
      "id": "e50e8400-e29b-41d4-a716-446655440501",
      "title": "Paiement loyer",
      "start_date": "2026-01-30T00:00:00Z",
      "end_date": "2026-01-30T23:59:59Z",
      "all_day": true,
      "color": "#EF4444"
    }
  ]
}
```

---

### 7.4. Événements du jour

**Endpoint:** `GET /api/v1/events/today/`
**Authentification:** Requise

**Réponse (200 OK):**
```json
[
  {
    "id": "e50e8400-e29b-41d4-a716-446655440502",
    "title": "Rendez-vous banque",
    "start_date": "2026-01-16T14:00:00Z",
    "end_date": "2026-01-16T15:00:00Z",
    "all_day": false,
    "color": "#10B981"
  }
]
```

---

### 7.5. Événements d'une date

**Endpoint:** `GET /api/v1/events/date/`
**Authentification:** Requise

**Paramètres de requête:**
- `date` - Date au format YYYY-MM-DD (requis)

**Exemple:** `GET /api/v1/events/date/?date=2026-01-25`

**Réponse (200 OK):** Tableau d'événements (même format que ci-dessus)

---

## 8. Payments (Mobile Money)

### 8.1. Fournisseurs de paiement

**Endpoint:** `GET /api/v1/payments/providers/`
**Authentification:** Requise

**Réponse (200 OK):**
```json
[
  {
    "id": "f50e8400-e29b-41d4-a716-446655440600",
    "name": "orange_money",
    "display_name": "Orange Money",
    "logo": "/media/payment_providers/orange.png",
    "is_active": true,
    "is_sandbox": false,
    "fee_percentage": "1.50",
    "fee_fixed": "100.00",
    "min_amount": "100.00",
    "max_amount": "1000000.00"
  },
  {
    "id": "f50e8400-e29b-41d4-a716-446655440601",
    "name": "mtn_momo",
    "display_name": "MTN Mobile Money",
    "logo": "/media/payment_providers/mtn.png",
    "is_active": true,
    "is_sandbox": false,
    "fee_percentage": "1.00",
    "fee_fixed": "50.00",
    "min_amount": "100.00",
    "max_amount": "1000000.00"
  }
]
```

---

### 8.2. Méthodes de paiement

**Endpoint:** `GET /api/v1/payments/methods/`
**Authentification:** Requise

**Réponse (200 OK):**
```json
[
  {
    "id": "g50e8400-e29b-41d4-a716-446655440700",
    "provider": "f50e8400-e29b-41d4-a716-446655440600",
    "provider_details": {
      "name": "orange_money",
      "display_name": "Orange Money",
      "logo": "/media/payment_providers/orange.png"
    },
    "phone_number": "+237690000000",
    "account_name": "John Doe",
    "is_default": true,
    "is_verified": true,
    "created_at": "2025-12-01T10:00:00Z"
  }
]
```

---

### 8.3. Ajouter une méthode de paiement

**Endpoint:** `POST /api/v1/payments/methods/`
**Authentification:** Requise

**Body:**
```json
{
  "provider": "f50e8400-e29b-41d4-a716-446655440601",
  "phone_number": "+237670000000",
  "account_name": "John Doe",
  "is_default": false
}
```

**Réponse (201 Created):** Méthode créée

---

### 8.4. Effectuer un dépôt

**Endpoint:** `POST /api/v1/payments/deposit/`
**Authentification:** Requise

**Body:**
```json
{
  "payment_method": "g50e8400-e29b-41d4-a716-446655440700",
  "amount": "50000.00",
  "description": "Rechargement portefeuille"
}
```

**Réponse (201 Created):**
```json
{
  "id": "h50e8400-e29b-41d4-a716-446655440800",
  "reference": "PAY-1737038400000-A1B2C3D4",
  "type": "deposit",
  "status": "pending",
  "amount": "50000.00",
  "currency": "XAF",
  "fee": "850.00",
  "total_amount": "50850.00",
  "description": "Rechargement portefeuille",
  "payment_method": "g50e8400-e29b-41d4-a716-446655440700",
  "provider": {
    "name": "orange_money",
    "display_name": "Orange Money"
  },
  "initiated_at": "2026-01-16T21:30:00Z",
  "completed_at": null,
  "created_at": "2026-01-16T21:30:00Z"
}
```

---

### 8.5. Effectuer un retrait

**Endpoint:** `POST /api/v1/payments/withdraw/`
**Authentification:** Requise

**Body:**
```json
{
  "payment_method": "g50e8400-e29b-41d4-a716-446655440700",
  "amount": "25000.00",
  "description": "Retrait"
}
```

**Réponse (201 Created):** Même format que deposit

---

### 8.6. Portefeuille

**Endpoint:** `GET /api/v1/payments/wallet/`
**Authentification:** Requise

**Réponse (200 OK):**
```json
{
  "id": "i50e8400-e29b-41d4-a716-446655440900",
  "balance": "75000.00",
  "currency": "XAF",
  "is_active": true,
  "created_at": "2025-10-01T10:00:00Z",
  "updated_at": "2026-01-16T21:30:00Z"
}
```

---

### 8.7. Transactions du portefeuille

**Endpoint:** `GET /api/v1/payments/wallet/transactions/`
**Authentification:** Requise

**Paramètres de requête (optionnels):**
- `type` - `credit` ou `debit`
- `page` - Numéro de page
- `page_size` - Taille de la page

**Réponse (200 OK):**
```json
{
  "count": 25,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "j50e8400-e29b-41d4-a716-446655441000",
      "type": "credit",
      "amount": "50000.00",
      "balance_after": "75000.00",
      "payment": "h50e8400-e29b-41d4-a716-446655440800",
      "description": "Dépôt via Orange Money",
      "created_at": "2026-01-16T21:35:00Z"
    },
    {
      "id": "j50e8400-e29b-41d4-a716-446655441001",
      "type": "debit",
      "amount": "25000.00",
      "balance_after": "25000.00",
      "payment": "h50e8400-e29b-41d4-a716-446655440801",
      "description": "Retrait",
      "created_at": "2026-01-15T14:00:00Z"
    }
  ]
}
```

---

## 9. Exports

### 9.1. Exporter les transactions

**Endpoint:** `GET /api/v1/finances/export/transactions/`
**Authentification:** Requise

**Paramètres de requête:**
- `format` - `excel` ou `pdf` (défaut: excel)
- `date_from` - Date de début (YYYY-MM-DD)
- `date_to` - Date de fin (YYYY-MM-DD)
- `type` - `income` ou `expense`
- `category` - UUID de la catégorie

**Exemple:** `GET /api/v1/finances/export/transactions/?format=excel&date_from=2026-01-01&date_to=2026-01-31`

**Réponse (200 OK):** Fichier binaire (Excel ou PDF)

**Utilisation en JavaScript:**
```javascript
const response = await api.exports.transactions('excel', {
  date_from: '2026-01-01',
  date_to: '2026-01-31'
});

// Créer un lien de téléchargement
const url = window.URL.createObjectURL(new Blob([response]));
const link = document.createElement('a');
link.href = url;
link.setAttribute('download', 'transactions.xlsx');
document.body.appendChild(link);
link.click();
link.remove();
```

---

### 9.2. Exporter le rapport de budget

**Endpoint:** `GET /api/v1/finances/export/budget/`
**Authentification:** Requise

**Paramètres de requête:**
- `year` - Année (requis)
- `month` - Mois 1-12 (requis)

**Exemple:** `GET /api/v1/finances/export/budget/?year=2026&month=1`

**Réponse (200 OK):** Fichier Excel

---

### 9.3. Exporter le rapport mensuel

**Endpoint:** `GET /api/v1/finances/export/monthly/`
**Authentification:** Requise

**Paramètres de requête:**
- `year` - Année (requis)
- `month` - Mois 1-12 (requis)

**Exemple:** `GET /api/v1/finances/export/monthly/?year=2026&month=1`

**Réponse (200 OK):** Fichier PDF complet avec transactions et budgets

---

## 10. Codes d'erreur

### Codes HTTP standards

- `200 OK` - Requête réussie
- `201 Created` - Ressource créée avec succès
- `204 No Content` - Suppression réussie (pas de contenu)
- `400 Bad Request` - Erreur de validation
- `401 Unauthorized` - Non authentifié ou token invalide
- `403 Forbidden` - Accès refusé (permissions insuffisantes)
- `404 Not Found` - Ressource non trouvée
- `429 Too Many Requests` - Trop de requêtes (rate limiting)
- `500 Internal Server Error` - Erreur serveur

### Format des erreurs

**Erreur de validation (400):**
```json
{
  "email": ["Cette adresse email est déjà utilisée."],
  "password": ["Le mot de passe doit contenir au moins 8 caractères."]
}
```

**Erreur d'authentification (401):**
```json
{
  "success": false,
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Email ou mot de passe incorrect"
  }
}
```

**Erreur de permission (403):**
```json
{
  "detail": "Vous n'avez pas la permission d'effectuer cette action."
}
```

**Erreur non trouvée (404):**
```json
{
  "detail": "Élément non trouvé."
}
```

---

## 11. Pagination

Toutes les listes sont paginées par défaut.

**Paramètres de pagination:**
- `page` - Numéro de page (défaut: 1)
- `page_size` - Nombre d'éléments par page (défaut: 20, max: 100)

**Format de réponse paginée:**
```json
{
  "count": 156,
  "next": "http://localhost:8000/api/v1/finances/transactions/?page=2",
  "previous": null,
  "results": [...]
}
```

**Utilisation:**
```javascript
// Page 1
const page1 = await api.transactions.list({ page: 1, page_size: 50 });

// Page suivante
if (page1.next) {
  const page2 = await api.transactions.list({ page: 2, page_size: 50 });
}
```

---

## 12. Authentification JWT

### Headers requis

Pour les endpoints authentifiés, inclure le header:
```
Authorization: Bearer <access_token>
```

### Gestion des tokens

1. **Connexion:** Récupérer les tokens `access` et `refresh`
2. **Stockage:** Stocker les tokens (localStorage ou cookie httpOnly)
3. **Utilisation:** Inclure le token d'accès dans chaque requête
4. **Expiration:** Quand le token expire (401), utiliser le refresh token
5. **Refresh:** Appeler `/api/v1/auth/token/refresh/` avec le refresh token
6. **Nouveau token:** Utiliser le nouveau token d'accès

**Durée de vie des tokens:**
- Access token: 60 minutes
- Refresh token: 7 jours

---

## 13. Rate Limiting

**Limites par défaut:**
- Utilisateurs authentifiés: 1000 requêtes/heure
- Utilisateurs anonymes: 100 requêtes/heure

**En cas de dépassement (429):**
```json
{
  "detail": "Limite de requêtes atteinte. Veuillez réessayer plus tard."
}
```

---

## 14. Notes importantes

### Devises supportées

- `XAF` - Franc CFA CEMAC (défaut)
- `XOF` - Franc CFA UEMOA
- `EUR` - Euro
- `USD` - Dollar US
- `GBP` - Livre Sterling
- `CHF` - Franc Suisse
- `CAD` - Dollar Canadien

### Format des dates

- Dates: `YYYY-MM-DD` (ex: 2026-01-16)
- DateTimes: `YYYY-MM-DDTHH:MM:SSZ` (ex: 2026-01-16T14:30:00Z)

### Soft Delete

Les transactions sont supprimées avec un "soft delete" et peuvent être récupérées par un administrateur.

### Récurrence

Les transactions et rappels peuvent être récurrents avec la configuration:
```json
{
  "frequency": "monthly",  // daily, weekly, monthly, yearly
  "interval": 1,          // tous les X périodes
  "day_of_month": 15,     // pour monthly (optionnel)
  "end_date": null        // null = infini
}
```

---

## 15. Support et Contact

Pour toute question ou problème:
- **Documentation complète:** Disponible à `/api/docs/`
- **Schema OpenAPI:** Disponible à `/api/schema/`
- **Redoc:** Disponible à `/api/redoc/`

---

**Fin de la documentation**
