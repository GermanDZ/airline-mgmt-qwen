/**
 * Test utilities and mocks for frontend tests.
 */
import { vi } from 'vitest'

/**
 * Mock the API client with configurable responses.
 *
 * Usage:
 *   const mockApi = createMockApi({ get: '/flights' })
 *   // ... component uses api.get('/flights')
 *   expect(mockApi.get).toHaveBeenCalledWith('/flights')
 */
export function createMockApi(overrides: Record<string, any> = {}) {
  const mockFetch = vi.fn()

  return {
    ...overrides,
    fetch: mockFetch,
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  }
}

/**
 * Reset all Vitest mocks between tests.
 */
export function resetMocks() {
  vi.clearAllMocks()
}

/**
 * Wait for a condition to become true with timeout.
 */
export async function waitForCondition(
  condition: () => boolean,
  options: { timeout?: number; interval?: number } = {}
): Promise<void> {
  const { timeout = 1000, interval = 50 } = options
  const start = Date.now()

  while (!condition()) {
    if (Date.now() - start > timeout) {
      throw new Error('Condition not met within timeout')
    }
    await new Promise((resolve) => setTimeout(resolve, interval))
  }
}

/**
 * Serialize snapshot for deterministic test output.
 */
export function serializeSnapshot<T>(data: T): string {
  return JSON.stringify(data, null, 2).replace(/\d{4}-\d{2}-\d{2}/g, '[DATE]')
}
