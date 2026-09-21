const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

export class ApiError extends Error {
  status: number;
  data: any;
  constructor(status: number, message: string, data?: any) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("medicore_token") : null;
  
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && !endpoint.includes("/auth/login") && !endpoint.includes("/auth/refresh")) {
    const refreshToken = typeof window !== "undefined" ? localStorage.getItem("medicore_refresh_token") : null;
    if (refreshToken) {
      try {
        const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken })
        });
        if (refreshRes.ok) {
          const tokenData = await refreshRes.json();
          localStorage.setItem("medicore_token", tokenData.access_token);
          if (tokenData.refresh_token) {
            localStorage.setItem("medicore_refresh_token", tokenData.refresh_token);
          }
          // Retry original request with newly issued access token
          headers["Authorization"] = `Bearer ${tokenData.access_token}`;
          const retryResponse = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers
          });
          if (retryResponse.ok) {
            return retryResponse.json();
          }
        }
      } catch {
        // Fall through to logout
      }
    }

    if (typeof window !== "undefined" && !window.location.pathname.includes("/login")) {
      localStorage.removeItem("medicore_token");
      localStorage.removeItem("medicore_refresh_token");
      localStorage.removeItem("medicore_user");
      window.location.href = "/login?session_expired=1";
    }
  }

  if (!response.ok) {
    let errorMessage = "An error occurred";
    let errorData = null;
    try {
      errorData = await response.json();
      errorMessage = errorData.detail || errorData.message || errorMessage;
    } catch {
      errorMessage = response.statusText;
    }
    throw new ApiError(response.status, errorMessage, errorData);
  }

  return response.json();
}

export const api = {
  get: <T>(endpoint: string) => request<T>(endpoint, { method: "GET" }),
  
  post: <T>(endpoint: string, body?: any) => request<T>(endpoint, {
    method: "POST",
    body: body instanceof FormData ? body : JSON.stringify(body)
  }),

  put: <T>(endpoint: string, body?: any) => request<T>(endpoint, {
    method: "PUT",
    body: JSON.stringify(body)
  }),

  delete: <T>(endpoint: string) => request<T>(endpoint, { method: "DELETE" }),

  patch: <T>(endpoint: string, body?: any) => request<T>(endpoint, {
    method: "PATCH",
    body: body ? JSON.stringify(body) : undefined
  }),

  upload: <T>(endpoint: string, formData: FormData) => request<T>(endpoint, {
    method: "POST",
    body: formData
  })
};

export default api;
