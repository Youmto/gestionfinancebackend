/**
 * API Client pour Finance Management Application
 * Backend Django REST Framework
 * Base URL: http://localhost:8000/api/v1/
 *
 * @version 1.0.0
 * @author Finance App Team
 * @description Client API complet avec tous les endpoints du backend Django
 */

import axios from 'axios';

// ============================================================
// CONFIGURATION
// ============================================================

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

// Créer une instance axios avec configuration par défaut
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 secondes
});

// ============================================================
// INTERCEPTEURS
// ============================================================

// Intercepteur pour ajouter le token JWT à chaque requête
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Intercepteur pour gérer le refresh token
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Si erreur 401 et pas déjà retryé
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, {
            refresh: refreshToken,
          });

          const { access } = response.data;
          localStorage.setItem('access_token', access);

          originalRequest.headers.Authorization = `Bearer ${access}`;
          return apiClient(originalRequest);
        }
      } catch (refreshError) {
        // Refresh token invalide, déconnecter l'utilisateur
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// ============================================================
// HELPERS
// ============================================================

/**
 * Stocke les tokens d'authentification
 */
const setTokens = (access, refresh) => {
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);
};

/**
 * Supprime les tokens d'authentification
 */
const clearTokens = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
};

/**
 * Vérifie si l'utilisateur est authentifié
 */
const isAuthenticated = () => {
  return !!localStorage.getItem('access_token');
};

// ============================================================
// AUTHENTICATION & USERS
// ============================================================

const auth = {
  /**
   * Inscription utilisateur classique
   * POST /api/v1/auth/register/
   */
  register: async (data) => {
    const response = await apiClient.post('/auth/register/', data);
    if (response.data.data?.tokens) {
      setTokens(response.data.data.tokens.access, response.data.data.tokens.refresh);
    }
    return response.data;
  },

  /**
   * Connexion utilisateur
   * POST /api/v1/auth/login/
   */
  login: async (email, password) => {
    const response = await apiClient.post('/auth/login/', { email, password });
    if (response.data.data?.tokens) {
      setTokens(response.data.data.tokens.access, response.data.data.tokens.refresh);
    }
    return response.data;
  },

  /**
   * Déconnexion utilisateur
   * POST /api/v1/auth/logout/
   */
  logout: async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    try {
      await apiClient.post('/auth/logout/', { refresh: refreshToken });
    } finally {
      clearTokens();
    }
  },

  /**
   * Rafraîchir le token d'accès
   * POST /api/v1/auth/token/refresh/
   */
  refreshToken: async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    const response = await apiClient.post('/auth/token/refresh/', {
      refresh: refreshToken,
    });
    localStorage.setItem('access_token', response.data.access);
    if (response.data.refresh) {
      localStorage.setItem('refresh_token', response.data.refresh);
    }
    return response.data;
  },

  /**
   * Envoyer un code de vérification par email (OTP)
   * POST /api/v1/auth/send-code/
   */
  sendVerificationCode: async (email, purpose = 'registration') => {
    const response = await apiClient.post('/auth/send-code/', { email, purpose });
    return response.data;
  },

  /**
   * Vérifier un code OTP
   * POST /api/v1/auth/verify-code/
   */
  verifyCode: async (email, code, purpose) => {
    const response = await apiClient.post('/auth/verify-code/', { email, code, purpose });
    return response.data;
  },

  /**
   * Inscription avec code de vérification
   * POST /api/v1/auth/register-with-code/
   */
  registerWithCode: async (data) => {
    const response = await apiClient.post('/auth/register-with-code/', data);
    if (response.data.tokens) {
      setTokens(response.data.tokens.access, response.data.tokens.refresh);
    }
    return response.data;
  },

  /**
   * Réinitialiser le mot de passe avec code
   * POST /api/v1/auth/reset-password-with-code/
   */
  resetPasswordWithCode: async (data) => {
    const response = await apiClient.post('/auth/reset-password-with-code/', data);
    return response.data;
  },

  /**
   * Renvoyer un code de vérification
   * POST /api/v1/auth/resend-code/
   */
  resendCode: async (email, purpose) => {
    const response = await apiClient.post('/auth/resend-code/', { email, purpose });
    return response.data;
  },

  /**
   * Obtenir le profil de l'utilisateur connecté
   * GET /api/v1/auth/me/
   */
  getProfile: async () => {
    const response = await apiClient.get('/auth/me/');
    return response.data;
  },

  /**
   * Mettre à jour le profil
   * PATCH /api/v1/auth/me/
   */
  updateProfile: async (data) => {
    const response = await apiClient.patch('/auth/me/', data);
    return response.data;
  },

  /**
   * Changer le mot de passe
   * PUT /api/v1/auth/change-password/
   */
  changePassword: async (oldPassword, newPassword, newPasswordConfirm) => {
    const response = await apiClient.put('/auth/change-password/', {
      old_password: oldPassword,
      new_password: newPassword,
      new_password_confirm: newPasswordConfirm,
    });
    return response.data;
  },

  // Helpers
  setTokens,
  clearTokens,
  isAuthenticated,
};

// ============================================================
// NOTIFICATION PREFERENCES
// ============================================================

const notifications = {
  /**
   * Obtenir les préférences de notification
   * GET /api/v1/auth/me/notifications/
   */
  getPreferences: async () => {
    const response = await apiClient.get('/auth/me/notifications/');
    return response.data;
  },

  /**
   * Mettre à jour les préférences de notification
   * PATCH /api/v1/auth/me/notifications/
   */
  updatePreferences: async (data) => {
    const response = await apiClient.patch('/auth/me/notifications/', data);
    return response.data;
  },
};

// ============================================================
// CATEGORIES
// ============================================================

const categories = {
  /**
   * Lister les catégories (système + personnalisées)
   * GET /api/v1/finances/categories/
   */
  list: async (params = {}) => {
    const response = await apiClient.get('/finances/categories/', { params });
    return response.data;
  },

  /**
   * Obtenir une catégorie par ID
   * GET /api/v1/finances/categories/:id/
   */
  get: async (id) => {
    const response = await apiClient.get(`/finances/categories/${id}/`);
    return response.data;
  },

  /**
   * Créer une catégorie personnalisée
   * POST /api/v1/finances/categories/
   */
  create: async (data) => {
    const response = await apiClient.post('/finances/categories/', data);
    return response.data;
  },

  /**
   * Modifier une catégorie
   * PUT /api/v1/finances/categories/:id/
   */
  update: async (id, data) => {
    const response = await apiClient.put(`/finances/categories/${id}/`, data);
    return response.data;
  },

  /**
   * Modifier partiellement une catégorie
   * PATCH /api/v1/finances/categories/:id/
   */
  partialUpdate: async (id, data) => {
    const response = await apiClient.patch(`/finances/categories/${id}/`, data);
    return response.data;
  },

  /**
   * Supprimer une catégorie
   * DELETE /api/v1/finances/categories/:id/
   */
  delete: async (id) => {
    const response = await apiClient.delete(`/finances/categories/${id}/`);
    return response.data;
  },

  /**
   * Catégories par type
   * GET /api/v1/finances/categories/by_type/?type=income|expense
   */
  byType: async (type) => {
    const response = await apiClient.get('/finances/categories/by_type/', {
      params: { type },
    });
    return response.data;
  },

  /**
   * Statut du budget d'une catégorie
   * GET /api/v1/finances/categories/:id/budget_status/
   */
  budgetStatus: async (id, year = null, month = null) => {
    const params = {};
    if (year) params.year = year;
    if (month) params.month = month;
    const response = await apiClient.get(`/finances/categories/${id}/budget_status/`, { params });
    return response.data;
  },

  /**
   * Aperçu de tous les budgets
   * GET /api/v1/finances/categories/budget_overview/
   */
  budgetOverview: async (year = null, month = null) => {
    const params = {};
    if (year) params.year = year;
    if (month) params.month = month;
    const response = await apiClient.get('/finances/categories/budget_overview/', { params });
    return response.data;
  },

  /**
   * Alertes budget
   * GET /api/v1/finances/categories/budget_alerts/
   */
  budgetAlerts: async (year = null, month = null) => {
    const params = {};
    if (year) params.year = year;
    if (month) params.month = month;
    const response = await apiClient.get('/finances/categories/budget_alerts/', { params });
    return response.data;
  },

  /**
   * Initialiser les catégories système (admin uniquement)
   * POST /api/v1/finances/init-categories/
   */
  initSystemCategories: async () => {
    const response = await apiClient.post('/finances/init-categories/');
    return response.data;
  },
};

// ============================================================
// TRANSACTIONS
// ============================================================

const transactions = {
  /**
   * Lister les transactions avec filtres
   * GET /api/v1/finances/transactions/
   *
   * Filtres disponibles:
   * - type: income | expense
   * - category: UUID de la catégorie
   * - group: UUID du groupe
   * - date_from: YYYY-MM-DD
   * - date_to: YYYY-MM-DD
   * - min_amount: nombre
   * - max_amount: nombre
   * - search: texte de recherche
   * - ordering: date | -date | amount | -amount
   * - page: numéro de page
   * - page_size: taille de la page
   */
  list: async (params = {}) => {
    const response = await apiClient.get('/finances/transactions/', { params });
    return response.data;
  },

  /**
   * Obtenir une transaction par ID
   * GET /api/v1/finances/transactions/:id/
   */
  get: async (id) => {
    const response = await apiClient.get(`/finances/transactions/${id}/`);
    return response.data;
  },

  /**
   * Créer une transaction
   * POST /api/v1/finances/transactions/
   */
  create: async (data) => {
    const response = await apiClient.post('/finances/transactions/', data);
    return response.data;
  },

  /**
   * Modifier une transaction
   * PUT /api/v1/finances/transactions/:id/
   */
  update: async (id, data) => {
    const response = await apiClient.put(`/finances/transactions/${id}/`, data);
    return response.data;
  },

  /**
   * Modifier partiellement une transaction
   * PATCH /api/v1/finances/transactions/:id/
   */
  partialUpdate: async (id, data) => {
    const response = await apiClient.patch(`/finances/transactions/${id}/`, data);
    return response.data;
  },

  /**
   * Supprimer une transaction (soft delete)
   * DELETE /api/v1/finances/transactions/:id/
   */
  delete: async (id) => {
    const response = await apiClient.delete(`/finances/transactions/${id}/`);
    return response.data;
  },

  /**
   * Partager une dépense de groupe
   * POST /api/v1/finances/transactions/:id/split/
   */
  split: async (id, data) => {
    const response = await apiClient.post(`/finances/transactions/${id}/split/`, data);
    return response.data;
  },

  /**
   * Voir les partages d'une transaction
   * GET /api/v1/finances/transactions/:id/splits/
   */
  getSplits: async (id) => {
    const response = await apiClient.get(`/finances/transactions/${id}/splits/`);
    return response.data;
  },
};

// ============================================================
// EXPENSE SPLITS
// ============================================================

const splits = {
  /**
   * Marquer un partage comme payé
   * PATCH /api/v1/finances/splits/:id/
   */
  markAsPaid: async (id, isPaid = true) => {
    const response = await apiClient.patch(`/finances/splits/${id}/`, { is_paid: isPaid });
    return response.data;
  },
};

// ============================================================
// DASHBOARD & STATISTICS
// ============================================================

const dashboard = {
  /**
   * Tableau de bord financier
   * GET /api/v1/finances/dashboard/
   */
  get: async () => {
    const response = await apiClient.get('/finances/dashboard/');
    return response.data;
  },

  /**
   * Résumé mensuel
   * GET /api/v1/finances/summary/?months=12
   */
  monthlySummary: async (months = 12) => {
    const response = await apiClient.get('/finances/summary/', {
      params: { months },
    });
    return response.data;
  },

  /**
   * Données pour graphiques
   * GET /api/v1/finances/charts/?period=monthly&count=6
   */
  chartData: async (period = 'monthly', count = 6) => {
    const response = await apiClient.get('/finances/charts/', {
      params: { period, count },
    });
    return response.data;
  },
};

// ============================================================
// EXPORTS
// ============================================================

const exports = {
  /**
   * Exporter les transactions (Excel ou PDF)
   * GET /api/v1/finances/export/transactions/?format=excel&date_from=...&date_to=...
   */
  transactions: async (format = 'excel', filters = {}) => {
    const params = { format, ...filters };
    const response = await apiClient.get('/finances/export/transactions/', {
      params,
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * Exporter le rapport de budget (Excel)
   * GET /api/v1/finances/export/budget/?year=2026&month=1
   */
  budgetReport: async (year, month) => {
    const response = await apiClient.get('/finances/export/budget/', {
      params: { year, month },
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * Exporter le rapport mensuel complet (PDF)
   * GET /api/v1/finances/export/monthly/?year=2026&month=1
   */
  monthlyReport: async (year, month) => {
    const response = await apiClient.get('/finances/export/monthly/', {
      params: { year, month },
      responseType: 'blob',
    });
    return response.data;
  },
};

// ============================================================
// GROUPS
// ============================================================

const groups = {
  /**
   * Lister les groupes
   * GET /api/v1/groups/
   */
  list: async (params = {}) => {
    const response = await apiClient.get('/groups/', { params });
    return response.data;
  },

  /**
   * Obtenir un groupe par ID
   * GET /api/v1/groups/:id/
   */
  get: async (id) => {
    const response = await apiClient.get(`/groups/${id}/`);
    return response.data;
  },

  /**
   * Créer un groupe
   * POST /api/v1/groups/
   */
  create: async (data) => {
    const response = await apiClient.post('/groups/', data);
    return response.data;
  },

  /**
   * Modifier un groupe
   * PUT /api/v1/groups/:id/
   */
  update: async (id, data) => {
    const response = await apiClient.put(`/groups/${id}/`, data);
    return response.data;
  },

  /**
   * Modifier partiellement un groupe
   * PATCH /api/v1/groups/:id/
   */
  partialUpdate: async (id, data) => {
    const response = await apiClient.patch(`/groups/${id}/`, data);
    return response.data;
  },

  /**
   * Supprimer un groupe
   * DELETE /api/v1/groups/:id/
   */
  delete: async (id) => {
    const response = await apiClient.delete(`/groups/${id}/`);
    return response.data;
  },

  /**
   * Inviter un membre au groupe
   * POST /api/v1/groups/:groupId/invite/
   */
  invite: async (groupId, email) => {
    const response = await apiClient.post(`/groups/${groupId}/invite/`, { email });
    return response.data;
  },

  /**
   * Accepter une invitation
   * POST /api/v1/groups/invitations/:token/
   */
  acceptInvitation: async (token) => {
    const response = await apiClient.post(`/groups/invitations/${token}/`);
    return response.data;
  },

  /**
   * Lister les membres d'un groupe
   * GET /api/v1/groups/:groupId/members/
   */
  getMembers: async (groupId) => {
    const response = await apiClient.get(`/groups/${groupId}/members/`);
    return response.data;
  },

  /**
   * Modifier un membre du groupe
   * PATCH /api/v1/groups/:groupId/members/:userId/
   */
  updateMember: async (groupId, userId, data) => {
    const response = await apiClient.patch(`/groups/${groupId}/members/${userId}/`, data);
    return response.data;
  },

  /**
   * Supprimer un membre du groupe
   * DELETE /api/v1/groups/:groupId/members/:userId/
   */
  removeMember: async (groupId, userId) => {
    const response = await apiClient.delete(`/groups/${groupId}/members/${userId}/`);
    return response.data;
  },

  /**
   * Quitter un groupe
   * POST /api/v1/groups/:groupId/leave/
   */
  leave: async (groupId) => {
    const response = await apiClient.post(`/groups/${groupId}/leave/`);
    return response.data;
  },

  /**
   * Obtenir le solde du groupe
   * GET /api/v1/groups/:groupId/balance/
   */
  getBalance: async (groupId) => {
    const response = await apiClient.get(`/groups/${groupId}/balance/`);
    return response.data;
  },

  /**
   * Transactions du groupe
   * GET /api/v1/groups/:groupId/transactions/
   */
  getTransactions: async (groupId, params = {}) => {
    const response = await apiClient.get(`/groups/${groupId}/transactions/`, { params });
    return response.data;
  },
};

// ============================================================
// REMINDERS
// ============================================================

const reminders = {
  /**
   * Lister les rappels
   * GET /api/v1/reminders/
   */
  list: async (params = {}) => {
    const response = await apiClient.get('/reminders/', { params });
    return response.data;
  },

  /**
   * Obtenir un rappel par ID
   * GET /api/v1/reminders/:id/
   */
  get: async (id) => {
    const response = await apiClient.get(`/reminders/${id}/`);
    return response.data;
  },

  /**
   * Créer un rappel
   * POST /api/v1/reminders/
   */
  create: async (data) => {
    const response = await apiClient.post('/reminders/', data);
    return response.data;
  },

  /**
   * Modifier un rappel
   * PUT /api/v1/reminders/:id/
   */
  update: async (id, data) => {
    const response = await apiClient.put(`/reminders/${id}/`, data);
    return response.data;
  },

  /**
   * Modifier partiellement un rappel
   * PATCH /api/v1/reminders/:id/
   */
  partialUpdate: async (id, data) => {
    const response = await apiClient.patch(`/reminders/${id}/`, data);
    return response.data;
  },

  /**
   * Supprimer un rappel
   * DELETE /api/v1/reminders/:id/
   */
  delete: async (id) => {
    const response = await apiClient.delete(`/reminders/${id}/`);
    return response.data;
  },

  /**
   * Marquer un rappel comme terminé
   * POST /api/v1/reminders/:id/complete/
   */
  complete: async (id) => {
    const response = await apiClient.post(`/reminders/${id}/complete/`);
    return response.data;
  },

  /**
   * Rappels à venir
   * GET /api/v1/reminders/upcoming/?days=7
   */
  upcoming: async (days = 7) => {
    const response = await apiClient.get('/reminders/upcoming/', {
      params: { days },
    });
    return response.data;
  },

  /**
   * Statistiques des rappels
   * GET /api/v1/reminders/stats/
   */
  stats: async () => {
    const response = await apiClient.get('/reminders/stats/');
    return response.data;
  },
};

// ============================================================
// EVENTS
// ============================================================

const events = {
  /**
   * Lister les événements
   * GET /api/v1/events/
   */
  list: async (params = {}) => {
    const response = await apiClient.get('/events/', { params });
    return response.data;
  },

  /**
   * Obtenir un événement par ID
   * GET /api/v1/events/:id/
   */
  get: async (id) => {
    const response = await apiClient.get(`/events/${id}/`);
    return response.data;
  },

  /**
   * Créer un événement
   * POST /api/v1/events/
   */
  create: async (data) => {
    const response = await apiClient.post('/events/', data);
    return response.data;
  },

  /**
   * Modifier un événement
   * PUT /api/v1/events/:id/
   */
  update: async (id, data) => {
    const response = await apiClient.put(`/events/${id}/`, data);
    return response.data;
  },

  /**
   * Modifier partiellement un événement
   * PATCH /api/v1/events/:id/
   */
  partialUpdate: async (id, data) => {
    const response = await apiClient.patch(`/events/${id}/`, data);
    return response.data;
  },

  /**
   * Supprimer un événement
   * DELETE /api/v1/events/:id/
   */
  delete: async (id) => {
    const response = await apiClient.delete(`/events/${id}/`);
    return response.data;
  },

  /**
   * Vue calendrier
   * GET /api/v1/events/calendar/
   */
  calendar: async () => {
    const response = await apiClient.get('/events/calendar/');
    return response.data;
  },

  /**
   * Calendrier mensuel
   * GET /api/v1/events/calendar/:year/:month/
   */
  monthCalendar: async (year, month) => {
    const response = await apiClient.get(`/events/calendar/${year}/${month}/`);
    return response.data;
  },

  /**
   * Événements à venir
   * GET /api/v1/events/upcoming/?days=7
   */
  upcoming: async (days = 7) => {
    const response = await apiClient.get('/events/upcoming/', {
      params: { days },
    });
    return response.data;
  },

  /**
   * Événements du jour
   * GET /api/v1/events/today/
   */
  today: async () => {
    const response = await apiClient.get('/events/today/');
    return response.data;
  },

  /**
   * Événements d'une date spécifique
   * GET /api/v1/events/date/?date=2026-01-16
   */
  byDate: async (date) => {
    const response = await apiClient.get('/events/date/', {
      params: { date },
    });
    return response.data;
  },

  /**
   * Statistiques des événements
   * GET /api/v1/events/stats/
   */
  stats: async () => {
    const response = await apiClient.get('/events/stats/');
    return response.data;
  },
};

// ============================================================
// PAYMENTS (MOBILE MONEY)
// ============================================================

const payments = {
  /**
   * Lister les fournisseurs de paiement
   * GET /api/v1/payments/providers/
   */
  listProviders: async () => {
    const response = await apiClient.get('/payments/providers/');
    return response.data;
  },

  /**
   * Obtenir un fournisseur de paiement
   * GET /api/v1/payments/providers/:id/
   */
  getProvider: async (id) => {
    const response = await apiClient.get(`/payments/providers/${id}/`);
    return response.data;
  },

  /**
   * Lister les méthodes de paiement de l'utilisateur
   * GET /api/v1/payments/methods/
   */
  listMethods: async () => {
    const response = await apiClient.get('/payments/methods/');
    return response.data;
  },

  /**
   * Ajouter une méthode de paiement
   * POST /api/v1/payments/methods/
   */
  addMethod: async (data) => {
    const response = await apiClient.post('/payments/methods/', data);
    return response.data;
  },

  /**
   * Modifier une méthode de paiement
   * PATCH /api/v1/payments/methods/:id/
   */
  updateMethod: async (id, data) => {
    const response = await apiClient.patch(`/payments/methods/${id}/`, data);
    return response.data;
  },

  /**
   * Supprimer une méthode de paiement
   * DELETE /api/v1/payments/methods/:id/
   */
  deleteMethod: async (id) => {
    const response = await apiClient.delete(`/payments/methods/${id}/`);
    return response.data;
  },

  /**
   * Lister les paiements
   * GET /api/v1/payments/
   */
  list: async (params = {}) => {
    const response = await apiClient.get('/payments/', { params });
    return response.data;
  },

  /**
   * Obtenir un paiement par ID
   * GET /api/v1/payments/:id/
   */
  get: async (id) => {
    const response = await apiClient.get(`/payments/${id}/`);
    return response.data;
  },

  /**
   * Effectuer un dépôt
   * POST /api/v1/payments/deposit/
   */
  deposit: async (data) => {
    const response = await apiClient.post('/payments/deposit/', data);
    return response.data;
  },

  /**
   * Effectuer un retrait
   * POST /api/v1/payments/withdraw/
   */
  withdraw: async (data) => {
    const response = await apiClient.post('/payments/withdraw/', data);
    return response.data;
  },

  /**
   * Effectuer un transfert
   * POST /api/v1/payments/transfer/
   */
  transfer: async (data) => {
    const response = await apiClient.post('/payments/transfer/', data);
    return response.data;
  },

  /**
   * Obtenir le portefeuille
   * GET /api/v1/payments/wallet/
   */
  getWallet: async () => {
    const response = await apiClient.get('/payments/wallet/');
    return response.data;
  },

  /**
   * Transactions du portefeuille
   * GET /api/v1/payments/wallet/transactions/
   */
  walletTransactions: async (params = {}) => {
    const response = await apiClient.get('/payments/wallet/transactions/', { params });
    return response.data;
  },
};

// ============================================================
// EXPORT PRINCIPAL
// ============================================================

const api = {
  // Client axios brut pour requêtes personnalisées
  client: apiClient,

  // Modules
  auth,
  notifications,
  categories,
  transactions,
  splits,
  dashboard,
  exports,
  groups,
  reminders,
  events,
  payments,

  // Configuration
  baseURL: API_BASE_URL,
};

export default api;

// Exports nommés pour imports spécifiques
export {
  auth,
  notifications,
  categories,
  transactions,
  splits,
  dashboard,
  exports as financeExports,
  groups,
  reminders,
  events,
  payments,
  apiClient,
};
