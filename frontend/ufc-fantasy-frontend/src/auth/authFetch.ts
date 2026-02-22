import { clearToken } from "./auth";
import { useAuth0 } from "@auth0/auth0-react";

// Wraps TanStackQueries useQuery function for authorized api fetching
export async function authFetch(url: string, options?: RequestInit) {
  const { getAccessTokenSilently } = useAuth0();
  
  try {
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
      throw new Error('Unauthorized');
    }

    return res;
  } catch (error) {
    console.error('API request failed:', error);
    throw error; // Re-throw so caller knows it failed
  }
}
