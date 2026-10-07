export type UserRole = "user" | "superuser" | "admin" | "it" | "it_admin" | "it_manager" | "auditor";

export interface User {
  id: number | string;
  email: string;
  fullName?: string;
  full_name?: string;
  role: UserRole | string;
  orgName?: string;
  org_name?: string;
  sector?: string;
  location?: string | null;
  allowed_facilities?: number[] | null;
  status?: "active" | "inactive" | "pending" | string;
  preferences?: Record<string, any> | string | null;
  created_at?: string;
  last_login?: string | null;
  [key: string]: unknown;
}

export interface AuthContextType {
  user: User | null;
  preferences: Record<string, any>;
  updatePreferences: (newPrefs: Record<string, any>) => Promise<void>;
  login: (email: string, password?: string) => Promise<any>;
  register: (userData: Record<string, any>) => Promise<any>;
  logout: (isTimeout?: boolean) => Promise<void>;
  loading: boolean;
  sessionExpired: boolean;
  setSessionExpired: React.Dispatch<React.SetStateAction<boolean>>;
  sessionWarning: boolean;
  setSessionWarning: React.Dispatch<React.SetStateAction<boolean>>;
}
