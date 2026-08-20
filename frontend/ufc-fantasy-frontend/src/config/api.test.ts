import { getApiBaseUrl } from './api';

describe('getApiBaseUrl', () => {
  const envKey = 'REACT_APP_UFC_FANTASY_API_BASE_URL';

  it('returns the configured origin', () => {
    expect(
      getApiBaseUrl({ [envKey]: 'http://localhost:8000' })
    ).toBe('http://localhost:8000');
  });

  it('strips a trailing slash from the origin', () => {
    expect(
      getApiBaseUrl({ [envKey]: 'http://localhost:8000/' })
    ).toBe('http://localhost:8000');
  });

  it('throws when the origin is missing', () => {
    expect(() => getApiBaseUrl({})).toThrow(/REACT_APP_UFC_FANTASY_API_BASE_URL/);
  });

  it('throws when the origin is blank', () => {
    expect(() => getApiBaseUrl({ [envKey]: '   ' })).toThrow(
      /REACT_APP_UFC_FANTASY_API_BASE_URL/
    );
  });
});
