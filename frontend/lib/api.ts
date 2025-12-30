const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3081";

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  full_name?: string;
}

export interface User {
  id: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  created_at: string;
  last_login?: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
    // Try to load token from localStorage on client side
    if (typeof window !== "undefined") {
      this.token = localStorage.getItem("token");
    }
  }

  setToken(token: string) {
    this.token = token;
    if (typeof window !== "undefined") {
      localStorage.setItem("token", token);
    }
  }

  clearToken() {
    this.token = null;
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: `HTTP error! status: ${response.status}`,
      }));
      throw new Error(error.detail || "API request failed");
    }

    return response.json();
  }

  // Auth endpoints
  async login(credentials: LoginCredentials): Promise<LoginResponse> {
    const response = await this.request<LoginResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(credentials),
    });
    this.setToken(response.access_token);
    return response;
  }

  async register(data: RegisterData): Promise<User> {
    return this.request<User>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async logout(): Promise<void> {
    try {
      await this.request("/api/v1/auth/logout", { method: "POST" });
    } finally {
      this.clearToken();
    }
  }

  async verifyToken(): Promise<User> {
    return this.request<User>("/api/v1/auth/verify");
  }

  async getCurrentUser(): Promise<User> {
    return this.request<User>("/api/v1/auth/me");
  }

  // Docstore endpoints
  async getDocstores(): Promise<any[]> {
    return this.request("/api/v1/docstores/");
  }

  async createDocstore(data: any): Promise<any> {
    return this.request("/api/v1/docstores/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getDocstore(id: string): Promise<any> {
    return this.request(`/api/v1/docstores/${id}`);
  }

  async updateDocstore(id: string, data: any): Promise<any> {
    return this.request(`/api/v1/docstores/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async deleteDocstore(id: string): Promise<void> {
    return this.request(`/api/v1/docstores/${id}`, {
      method: "DELETE",
    });
  }

  // Document endpoints
  async getDocuments(docstoreId: string): Promise<any[]> {
    return this.request(`/api/v1/docstores/${docstoreId}/documents/`);
  }

  async uploadDocuments(docstoreId: string, files: File[]): Promise<any> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file);
    });

    const headers: Record<string, string> = {};
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    const response = await fetch(
      `${this.baseUrl}/api/v1/docstores/${docstoreId}/documents/upload`,
      {
        method: "POST",
        headers,
        body: formData,
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: `HTTP error! status: ${response.status}`,
      }));
      throw new Error(error.detail || "Document upload failed");
    }

    return response.json();
  }

  async getDocument(documentId: string): Promise<any> {
    return this.request(`/api/v1/documents/${documentId}`);
  }

  async deleteDocument(documentId: string): Promise<void> {
    return this.request(`/api/v1/documents/${documentId}`, {
      method: "DELETE",
    });
  }

  // Pipeline endpoints
  async getPipelines(docstoreId: string): Promise<any[]> {
    return this.request(`/api/v1/docstores/${docstoreId}/pipelines/`);
  }

  async createPipeline(docstoreId: string, pipelineType: string): Promise<any> {
    return this.request(`/api/v1/docstores/${docstoreId}/pipelines/generate`, {
      method: "POST",
      body: JSON.stringify({ pipeline_type: pipelineType }),
    });
  }

  async deployPipeline(pipelineId: string): Promise<any> {
    return this.request(`/api/v1/pipelines/${pipelineId}/deploy`, {
      method: "POST",
    });
  }

  // Query endpoints
  async queryDocstore(docstoreId: string, query: string, topK: number = 5): Promise<any> {
    return this.request(`/api/v1/docstores/${docstoreId}/query`, {
      method: "POST",
      body: JSON.stringify({ query, top_k: topK }),
    });
  }

  async queryMultiDocstores(docstoreIds: string[], query: string, topK: number = 5): Promise<any> {
    return this.request(`/api/v1/query/multi`, {
      method: "POST",
      body: JSON.stringify({ docstore_ids: docstoreIds, query, top_k: topK }),
    });
  }
}

export const api = new ApiClient(API_URL);
