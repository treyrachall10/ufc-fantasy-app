const DOMAIN_ENV = 'REACT_APP_AUTH0_DOMAIN';
const CLIENT_ID_ENV = 'REACT_APP_AUTH0_CLIENT_ID';
const AUDIENCE_ENV = 'REACT_APP_AUTH0_AUDIENCE';

export function getAuth0Config(env: NodeJS.ProcessEnv = process.env): {
  domain: string;
  clientId: string;
  audience: string;
} {
  const domain = env[DOMAIN_ENV]?.trim();
  const clientId = env[CLIENT_ID_ENV]?.trim();
  const audience = env[AUDIENCE_ENV]?.trim();

  if (!domain || !clientId || !audience) {
    throw new Error(
      `${DOMAIN_ENV}, ${CLIENT_ID_ENV}, and ${AUDIENCE_ENV} are required.`
    );
  }

  return { domain, clientId, audience };
}
