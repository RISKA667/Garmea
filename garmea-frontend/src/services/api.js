const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class ApiService {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  // Méthode générique pour les requêtes HTTP
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    
    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    };

    const config = {
      ...defaultOptions,
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        throw new Error(`Erreur HTTP: ${response.status}`);
      }

      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      }
      
      return await response.text();
    } catch (error) {
      console.error('Erreur API:', error);
      throw error;
    }
  }

  // Méthodes pour les utilisateurs
  async createUser(userData) {
    return this.request('/users', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  }

  async getUser(userId) {
    return this.request(`/users/${userId}`);
  }

  async updateUser(userId, userData) {
    return this.request(`/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(userData),
    });
  }

  // Méthodes pour les documents
  async uploadDocument(file, userId) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', userId);

    return this.request('/documents/upload', {
      method: 'POST',
      headers: {
        // Ne pas définir Content-Type pour FormData
      },
      body: formData,
    });
  }

  async getDocuments(userId) {
    return this.request(`/documents?user_id=${userId}`);
  }

  async deleteDocument(documentId) {
    return this.request(`/documents/${documentId}`, {
      method: 'DELETE',
    });
  }

  // Méthodes pour l'analyse généalogique
  async analyzeDocuments(userId) {
    return this.request('/analyze', {
      method: 'POST',
      body: JSON.stringify({ user_id: userId }),
    });
  }

  async getAnalysisStatus(analysisId) {
    return this.request(`/analyze/${analysisId}/status`);
  }

  async getFamilyTree(userId) {
    return this.request(`/family-tree/${userId}`);
  }

  // Méthodes pour les ancêtres
  async searchAncestors(searchData) {
    return this.request('/ancestors/search', {
      method: 'POST',
      body: JSON.stringify(searchData),
    });
  }

  async getAncestorDetails(ancestorId) {
    return this.request(`/ancestors/${ancestorId}`);
  }

  // Méthodes pour les rapports
  async generateReport(userId, reportType) {
    return this.request('/reports/generate', {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, type: reportType }),
    });
  }

  async getReport(reportId) {
    return this.request(`/reports/${reportId}`);
  }

  // Méthodes pour l'authentification
  async login(credentials) {
    return this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
  }

  async register(userData) {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  }

  async logout() {
    return this.request('/auth/logout', {
      method: 'POST',
    });
  }

  // Méthodes pour les abonnements
  async getSubscriptionPlans() {
    return this.request('/subscriptions/plans');
  }

  async createSubscription(planId, paymentData) {
    return this.request('/subscriptions', {
      method: 'POST',
      body: JSON.stringify({ plan_id: planId, payment: paymentData }),
    });
  }

  async getCurrentSubscription(userId) {
    return this.request(`/subscriptions/current?user_id=${userId}`);
  }

  // Méthodes utilitaires
  async healthCheck() {
    return this.request('/health');
  }
}

// Instance singleton
const apiService = new ApiService();

export default apiService; 