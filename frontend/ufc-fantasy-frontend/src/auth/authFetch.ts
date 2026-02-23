import { getToken, clearToken } from "./auth";
import { useAuth0 } from '@auth0/auth0-react';

export const useAuthFetch = () => {
  const {getAccessTokenSilently} = useAuth0();
  // Wraps TanStackQueries useQuery function for authorized api fetching
  return async (url: string, options?: RequestInit) => {
    
    const token = await getAccessTokenSilently();
    const res = await fetch(url, {
      ...options,
      headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`, // Sends auth token for backend authentication
      },
    });

    // If backend rejects authentication (401), clear token and force re-auth
    if (res.status === 401) {
      clearToken();
      throw new Error('Unauthorized')
    }

    return res;
  }
};
