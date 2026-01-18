import { getToken, clearToken } from "./auth";

// Wraps TanStackQueries useQuery function for authorized api fetching
export async function authFetch(url: string, options?: RequestInit) {
  const token = getToken();
  
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
