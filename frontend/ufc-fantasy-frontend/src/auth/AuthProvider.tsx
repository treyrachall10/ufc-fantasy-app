import { createContext, useState, ReactNode, useEffect } from 'react';
import { getToken, clearToken, saveToken } from './auth';
import { useQuery } from "@tanstack/react-query";
import { useAuthFetch } from './authFetch';
import { useAuth0, User } from '@auth0/auth0-react';
import { useCurrentUser } from './useCurrentUser';

interface AuthContextType {
  token: string | null;
  user: User | undefined;
    isAuthenticated: boolean;
  isLoading: boolean;
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

  return (
    <AuthContext.Provider value={{ token, user: user, isAuthenticated, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}
