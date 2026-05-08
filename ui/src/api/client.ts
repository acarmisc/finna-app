import axios, {
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
  AxiosError,
} from "axios";
import { toast } from "sonner";
import { useAuthStore } from "@/store/auth";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

export { API_BASE_URL };

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  },
);

// Track refresh attempts to prevent infinite loops
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & {
      _retry?: boolean;
    };

    // Handle 401 errors
    if (error.response?.status === 401 && originalRequest) {
      if (isRefreshing) {
        // If we're already refreshing, add to queue
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then(() => apiClient(originalRequest))
          .catch((err) => Promise.reject(err));
      }

      isRefreshing = true;

      try {
        // Attempt token refresh
        const refreshResponse = await apiClient.post(
          "/auth/refresh",
          {},
          {
            withCredentials: true,
          },
        );

        if (refreshResponse.data?.access_token) {
          // Update token in store
          useAuthStore.getState().setToken(refreshResponse.data.access_token);

          // Retry original request with new token
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${refreshResponse.data.access_token}`;
          }

          // Process queued requests
          failedQueue.forEach(({ resolve }) => resolve(null));
          failedQueue = [];

          return apiClient(originalRequest as AxiosRequestConfig);
        }
      } catch (refreshError) {
        // Refresh failed - clear tokens and redirect
        useAuthStore.getState().logout();

        // Show nice toast then redirect to login
        if (typeof window !== "undefined") {
          toast.error("Session expired. Redirecting to login...", {
            duration: 2500,
            action: {
              label: "Login",
              onClick: () => { window.location.href = "/#/" },
            },
          })
          setTimeout(() => {
            window.location.href = "/#/"
          }, 2800)
        }

        // Process queued requests with error
        failedQueue.forEach(({ reject }) => reject(refreshError));
        failedQueue = [];

        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    } else if (error.response?.status === 401) {
      // Show nice toast then redirect to login
      if (typeof window !== "undefined") {
        const toastId = toast.error("Session expired. Redirecting to login...", {
          duration: 2500,
          action: {
            label: "Login",
            onClick: () => { window.location.href = "/#/" },
          },
        })
        setTimeout(() => {
          window.location.href = "/#/"
        }, 2800)
      }
    }

    return Promise.reject(error);
  },
);

const createRequest = async <TRequest, TResponse>(
  method: "GET" | "POST" | "PUT" | "DELETE" | "PATCH",
  endpoint: string,
  data?: TRequest,
  config?: AxiosRequestConfig,
): Promise<TResponse> => {
  const response: AxiosResponse<TResponse> = await apiClient.request({
    method,
    url: endpoint,
    data,
    ...config,
  });
  return response.data;
};

export { apiClient, createRequest };

export default apiClient;
