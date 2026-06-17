import axios, { AxiosError, AxiosHeaders, type InternalAxiosRequestConfig } from "axios";

import { getAccessToken, getActiveAuthRole, getRefreshToken, setAuthTokens } from "@/features/auth/store";
import { getActiveShopKey } from "@/features/shops/store";
import type { TokenPair } from "@/types/auth";

type RetryRequestConfig = InternalAxiosRequestConfig & {
  _retry?: boolean;
};

const resolvedBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

const apiClient = axios.create({
  baseURL: resolvedBaseUrl,
  timeout: 15_000
});

let isRefreshing = false;
let refreshSubscribers: Array<(token: string | null) => void> = [];

function notifyRefreshSubscribers(token: string | null) {
  refreshSubscribers.forEach((callback) => callback(token));
  refreshSubscribers = [];
}

function queueRefreshSubscriber(callback: (token: string | null) => void) {
  refreshSubscribers.push(callback);
}

apiClient.interceptors.request.use((config) => {
  const activeRole = getActiveAuthRole();
  const token = getAccessToken(activeRole ?? undefined);
  const activeShopKey = getActiveShopKey();

  if (token || activeShopKey) {
    config.headers = config.headers ?? new AxiosHeaders();
  }

  if (token) {
    config.headers.Authorization = "Bearer " + token;
  }

  if (activeShopKey) {
    config.headers["X-Shop-Key"] = activeShopKey;
  }

  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const status = error.response?.status;
    const originalRequest = error.config as RetryRequestConfig | undefined;
    const requestUrl = originalRequest?.url ?? "";
    const isAuthEndpoint =
      requestUrl.includes("/auth/login") || requestUrl.includes("/auth/refresh") || requestUrl.includes("/auth/logout");

    if (status !== 401 || originalRequest === undefined || isAuthEndpoint) {
      return Promise.reject(error);
    }

    if (originalRequest._retry === true) {
      return Promise.reject(error);
    }

    const activeRole = getActiveAuthRole();
    if (activeRole === null) {
      return Promise.reject(error);
    }

    const refreshToken = getRefreshToken(activeRole);
    if (refreshToken === null) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        queueRefreshSubscriber((newAccessToken) => {
          if (newAccessToken === null) {
            reject(error);
            return;
          }

          originalRequest.headers = originalRequest.headers ?? new AxiosHeaders();
          originalRequest.headers.Authorization = "Bearer " + newAccessToken;
          resolve(apiClient(originalRequest));
        });
      });
    }

    isRefreshing = true;

    try {
      const activeShopKey = getActiveShopKey();
      const refreshResponse = await axios.post<TokenPair>(
        resolvedBaseUrl + "/auth/refresh",
        {
          refresh_token: refreshToken
        },
        {
          timeout: 15_000,
          headers: activeShopKey
            ? {
                "X-Shop-Key": activeShopKey
              }
            : undefined
        }
      );

      const nextTokens = refreshResponse.data;
      setAuthTokens(nextTokens, activeRole);
      notifyRefreshSubscribers(nextTokens.access_token);

      originalRequest.headers = originalRequest.headers ?? new AxiosHeaders();
      originalRequest.headers.Authorization = "Bearer " + nextTokens.access_token;
      return apiClient(originalRequest);
    } catch (refreshError) {
      notifyRefreshSubscribers(null);
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

export default apiClient;
