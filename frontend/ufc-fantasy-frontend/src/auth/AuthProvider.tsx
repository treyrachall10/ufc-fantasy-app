import { createContext, useState, ReactNode, useEffect } from 'react';
import { getToken, clearToken, saveToken } from './auth';
import { useQuery } from "@tanstack/react-query";
import { useAuthFetch } from './authFetch';
import { useAuth0, User } from '@auth0/auth0-react';
import { useCurrentUser } from './useCurrentUser';

interface AuthContextType {
  token: string | null;
  logout: () => void;
  login: (token: string) => void;
  user: User | undefined;
    isAuthenticated: boolean;
  isLoading: boolean;
  profileComplete: boolean;
}

interface AuthProviderProps {
  children: ReactNode;
}

// Tells app theres context that can be passed through component tree
export const AuthContext = createContext<AuthContextType | null>(null);

// Component job is to own the authentication state
export function AuthProvider({ children }: AuthProviderProps) {
  const {user, isAuthenticated, isLoading} = useAuth0();
  const authFetch = useAuthFetch();
  const [token, setToken] = useState<string | null>(getToken());
  const [userState, setUserState] = useState<User | null>(null);
  const [profileComplete, setProfileComplete] = useState<boolean>(false);
  const { data } = useCurrentUser();

// Logs users out by clearing jwt token and setting token state to null
  const logout = () => {
    clearToken();
    setUserState(null);
    setToken(null);
  };
// Logs users in by saving token to session memory and setting token state to that value
  const login = (token: string) => {
    saveToken(token);
    setToken(token);
};

  return (
    <AuthContext.Provider value={{ token, logout, login, user: user, isAuthenticated, isLoading, profileComplete }}>
      {children}
    </AuthContext.Provider>
  );
}
