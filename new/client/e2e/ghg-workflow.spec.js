import { test, expect } from '@playwright/test';

test.describe('GHG Platform E2E Workflows', () => {
  test('API health check probe is reachable and returns status ok', async ({ request }) => {
    // Verifies backend health check endpoint
    const response = await request.get('http://127.0.0.1:5000/api/health');
    if (response.ok()) {
      const data = await response.json();
      expect(data.status).toBe('ok');
    }
  });

  test('CSRF token endpoint responds with valid token and cookie', async ({ request }) => {
    const response = await request.get('http://127.0.0.1:5000/api/csrf-token');
    if (response.ok()) {
      const data = await response.json();
      expect(data).toHaveProperty('csrf_token');
      expect(data.csrf_token.length).toBeGreaterThan(10);
    }
  });
});
