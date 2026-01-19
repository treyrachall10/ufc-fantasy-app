import { createContext, useState, ReactNode } from 'react';
import { getToken, clearToken, saveToken } from './auth';

interface AuthContextType {
  token: string | null;
  logout: () => void;
  login: (token: string) => void;
}

interface AuthProviderProps {
  children: ReactNode;
}

// Tells app theres context that can be passed through component tree
export const AuthContext = createContext<AuthContextType | null>(null);

// Component job is to own the authentication state
export function AuthProvider({ children }: AuthProviderProps) {
  const [token, setToken] = useState<string | null>(getToken());

// Logs users out by clearing jwt token and setting token state to null
  const logout = () => {
    clearToken();
    setToken(null);
  };
// Logs users in by saving token to session memory and setting token state to that value
  const login = (token: string) => {
    saveToken(token);
    setToken(token);
};

  return (
    <AuthContext.Provider value={{ token, logout, login }}>
      {children}
    </AuthContext.Provider>
  );
}
