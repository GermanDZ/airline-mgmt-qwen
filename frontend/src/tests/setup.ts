/**
 * Test setup file for Vitest + React Testing Library.
 *
 * Imports @testing-library/jest-dom to extend vitest's assertions
 * with DOM-specific matchers (toBeVisible, toBeInTheDocument, etc.).
 */
import '@testing-library/jest-dom/vitest'

// Mock Next/navigation or any browser APIs if needed
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})
