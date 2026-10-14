import { request } from "./client"
import type { AuthResponse, AuthUser } from "../types/entities"

export const login = (username: string, password: string) =>
  request<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) })

export const register = (name: string, username: string, password: string) =>
  request<AuthResponse>("/auth/register", { method: "POST", body: JSON.stringify({ name, username, password }) })

export const getMe = () => request<AuthUser>("/auth/me")

export const logout = () => request<{ status: string }>("/auth/logout", { method: "POST" })
