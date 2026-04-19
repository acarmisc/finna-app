import { ToastTone } from '../types';

interface APIError {
  error: string;
  message?: string;
  detail?: string;
}

interface ApiResponse<T> {
  data?: T;
  error?: APIError;
  status: number;
}

class APIClient {
  private baseUrl: string;
  private token: string | null;

  constructor(baseUrl: string = this.getApiUrl()) {
    this.baseUrl = baseUrl;
    this.token = this.getTokenFromStorage();
  }

  private getApiUrl(): string {
    return import.meta.env.VITE_API_URL || 'http://localhost:8000';
  }

  private getTokenFromStorage(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('finna-auth-token');
    }
    return null;
  }

  private async handleResponse<T>(response: Response): Promise<ApiResponse<T>> {
    const contentType = response.headers.get('content-type');
    
    if (!contentType || !contentType.includes('application/json')) {
      return { status: response.status, error: { error: 'unexpected_response', message: 'Non-JSON response received' } };
    }

    try {
      const data = await response.json();

      if (!response.ok) {
        return {
          status: response.status,
          error: {
            error: data.error || 'api_error',
            message: data.message,
            detail: data.detail,
          },
        };
      }

      return { data, status: response.status };
    } catch (e) {
      return { 
        status: response.status, 
        error: { error: 'parse_error', message: 'Failed to parse response' } 
      };
    }
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers,
        credentials: 'include', // Include cookies for session
      });

      return this.handleResponse<T>(response);
    } catch (e) {
      return {
        status: 0,
        error: {
          error: 'network_error',
          message: e instanceof Error ? e.message : 'Unknown network error',
        },
      };
    }
  }

  // Authentication
  async login(username: string, password: string): Promise<ApiResponse<{ token: string }>> {
    const result = await this.request<{ token: string }>('/api/v1/auth/token', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });

    if (result.data?.token) {
      this.token = result.data.token;
      localStorage.setItem('finna-auth-token', result.data.token);
    }

    return result;
  }

  async logout(): Promise<void> {
    this.token = null;
    localStorage.removeItem('finna-auth-token');
  }

  // Connections
  async getConnections(): Promise<ApiResponse<any[]>> {
    return this.request('/api/v1/config/connections');
  }

  async createConnection(data: any): Promise<ApiResponse<any>> {
    return this.request('/api/v1/config/connections', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Costs
  async getCosts(params?: { 
    provider?: string; 
    project?: string; 
    startDate?: string; 
    endDate?: string 
  }): PromiseApiResponse<any[]>> {
    const query = new URLSearchParams(params as any).toString();
    const endpoint = query ? `/api/v1/costs?${query}` : '/api/v1/costs';
    return this.request(endpoint);
  }

  // Alerts
  async getAlerts(): Promise<ApiResponse<any[]>> {
    return this.request('/api/v1/alerts');
  }

  // Runs/Extractors
  async getRuns(): Promise<ApiResponse<any[]>> {
    return this.request('/api/v1/extractors/runs');
  }

  async runExtractor(type: string, provider?: string): Promise<ApiResponse<any>> {
    return this.request('/api/v1/extractors/run', {
      method: 'POST',
      body: JSON.stringify({ type, provider }),
    });
  }

  // Projects
  async getProjects(): Promise<ApiResponse<any[]>> {
    return this.request('/api/v1/config/projects');
  }

  async createProject(data: any): Promise<ApiResponse<any>> {
    return this.request('/api/v1/config/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Health
  async healthCheck(): Promise<ApiResponse<any>> {
    return this.request('/healthz');
  }

  // Generic error handling with toast
  showErrorToast(error?: APIError, defaultTitle: string = 'Error'): void {
    if (!error) return;

    const title = error.message || error.error || defaultTitle;
    const body = error.detail || (error.error === 'network_error' ? 'Please check your connection' : '');

    console.error('API Error:', error);
    // This would be called from a component that has access to pushToast
  }
}

// Singleton instance
let apiClient: APIClient | null = null;

export function getApiClient(): APIClient {
  if (!apiClient) {
    apiClient = new APIClient();
  }
  return apiClient;
}
