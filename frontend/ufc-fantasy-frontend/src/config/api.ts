const API_BASE_URL_ENV = 'REACT_APP_UFC_FANTASY_API_BASE_URL';

type ApiEnv = {
  REACT_APP_UFC_FANTASY_API_BASE_URL?: string;
};

export function getApiBaseUrl(
  env?: ApiEnv
) {
  const raw =
    env?.REACT_APP_UFC_FANTASY_API_BASE_URL ??
    process.env.REACT_APP_UFC_FANTASY_API_BASE_URL;

  if (!raw?.trim()) {
    throw new Error(`${API_BASE_URL_ENV} is required.`);
  }

  return raw.trim().replace(/\/+$/, '');
}