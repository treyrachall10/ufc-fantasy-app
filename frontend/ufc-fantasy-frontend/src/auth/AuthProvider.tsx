import { createContext, useState, ReactNode, useEffect } from 'react';
import { getToken, clearToken, saveToken } from './auth';
import { useQuery } from "@tanstack/react-query";
import { authFetch } from './authFetch';

interface AuthContextType {
  token: string | null;
  logout: () => void;
  login: (token: string) => void;
  user: User | null;
}

interface User {
  pk: number
  email: string
  username: string
}

interface AuthProviderProps {
  children: ReactNode;
}

// Tells app theres context that can be passed through component tree
export const AuthContext = createContext<AuthContextType | null>(null);

// Component job is to own the authentication state
export function AuthProvider({ children }: AuthProviderProps) {
  const [token, setToken] = useState<string | null>(getToken());
  const [user, setUser] = useState<User | null>(null);

  // Calls api to store user info if token exists
  const { data, isPending, error} = useQuery<User>({
      queryKey: ['UserInfo', token],
      queryFn: () => authFetch(`http://localhost:8000/dj-rest-auth/user/`).then(r => r.json()),
      enabled: !!token,
  })
  // Runs when user data changes
  useEffect(() => {
    if (data) {
      setUser({
        pk: data.pk,
        email: data.email,
        username: data.username
      });
    }
  }, [data]);

  useEffect(() => {
  if (token && error) {
      clearToken()
      setToken(null)
      setUser(null)
    }
  }, [token, error])

// Logs users out by clearing jwt token and setting token state to null
  const logout = () => {
    clearToken();
    setUser(null);
    setToken(null);
  };
// Logs users in by saving token to session memory and setting token state to that value
  const login = (token: string) => {
    saveToken(token);
    setToken(token);
};

  return (
    <AuthContext.Provider value={{ token, logout, login, user }}>
      {children}
    </AuthContext.Provider>
  );
}
