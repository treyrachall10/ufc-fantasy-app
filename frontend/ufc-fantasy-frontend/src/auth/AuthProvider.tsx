import { createContext, useState, ReactNode } from 'react';
import { getToken } from './auth';
import { useAuth0, User } from '@auth0/auth0-react';

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
  const [token] = useState<string | null>(getToken());

  return (
    <AuthContext.Provider value={{ token, user: user, isAuthenticated, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}
