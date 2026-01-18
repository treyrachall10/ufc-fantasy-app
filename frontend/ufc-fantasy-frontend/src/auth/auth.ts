export function saveToken(accessToken: string) {
  /* Saves user access token in session storage */
  sessionStorage.setItem('token', accessToken);
}

export function getToken(): string | null {
  /* Gets user access token from session storage */
  const tokenString = sessionStorage.getItem('token');
  return tokenString;
}

export function clearToken(): void {
    /* Gets user access token from session storage */
    sessionStorage.removeItem('token');
}