import { APIRequestContext } from '@playwright/test';

export async function waitForHealthy(
  request: APIRequestContext,
  {
    timeoutMs = 30000,
    intervalMs = 500,
  }: { timeoutMs?: number; intervalMs?: number } = {},
): Promise<void> {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    try {
      const response = await request.get('/health');
      if (response.ok()) {
        const body = await response.json();
        if (body.status === 'ok' && body.opa === true && body.redis === true) {
          return;
        }
      }
    } catch (error) {
      // Server might not be ready yet.
    }

    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }

  throw new Error('Health check did not become ready within timeout');
}
