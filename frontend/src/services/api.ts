import axios from "axios";

export const api = axios.create({
  baseURL: "/api",
  withCredentials: true,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url: string = error.config?.url ?? "";
    if (error.response?.status === 401 && !url.includes("/auth/")) {
      if (!window.location.pathname.startsWith("/login")) {
        window.location.assign("/login");
      }
    }
    return Promise.reject(error);
  },
);

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => (typeof item?.msg === "string" ? item.msg : "Invalid value"))
        .join(" ");
    }
    if (error.response?.status === 413) return "That image is larger than 8 MB.";
  }
  return "Something went wrong. Try again.";
}
