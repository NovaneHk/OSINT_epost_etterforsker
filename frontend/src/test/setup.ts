import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { setupMockServer } from '@/lib/msw/server';

// Setup MSW for API mocking in tests
let server: any;
export { server };

beforeAll(async () => {
  server = await setupMockServer();
  if (server) {
    server.listen({
      onUnhandledRequest: 'bypass',
    });
  }
});

afterEach(() => {
  if (server) {
    server.resetHandlers();
  }
});

afterAll(() => {
  if (server) {
    server.close();
  }
});

// Mock Next.js router
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
  useSearchParams: () => ({
    get: vi.fn(),
    getAll: vi.fn(),
    has: vi.fn(),
    keys: vi.fn(),
    values: vi.fn(),
    entries: vi.fn(),
    toString: vi.fn(),
  }),
  usePathname: () => '/',
  useParams: () => ({}),
}));

// Mock Next.js dynamic imports
vi.mock('next/dynamic', () => ({
  default: (dynamicFunction: any, options: any) => {
    const DynamicComponent = (props: any) => {
      const [Component, setComponent] = React.useState(null);

      React.useEffect(() => {
        dynamicFunction().then((mod: any) => {
          setComponent(() => mod.default || mod);
        });
      }, []);

      if (!Component) {
        return options?.loading ? React.createElement(options.loading) : null;
      }

      return React.createElement(Component, props);
    };

    return DynamicComponent;
  },
}));

// Mock IntersectionObserver (class form — arrow fns can't be used with `new`)
class MockIntersectionObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
  takeRecords = vi.fn(() => []);
  root: Element | null = null;
  rootMargin = '';
  thresholds: ReadonlyArray<number> = [];
  constructor(_callback: IntersectionObserverCallback, _options?: IntersectionObserverInit) {}
}
global.IntersectionObserver = MockIntersectionObserver as unknown as typeof IntersectionObserver;

// Mock ResizeObserver (class form)
class MockResizeObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
  constructor(_callback: ResizeObserverCallback) {}
}
global.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;

// Mock window.matchMedia
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
});

// Mock window.performance for performance monitoring tests
Object.defineProperty(window, 'performance', {
  writable: true,
  value: {
    ...window.performance,
    mark: vi.fn(),
    measure: vi.fn(),
    getEntriesByType: vi.fn(() => []),
    getEntriesByName: vi.fn(() => []),
    clearMarks: vi.fn(),
    clearMeasures: vi.fn(),
    now: vi.fn(() => Date.now()),
  },
});

// Mock localStorage and sessionStorage
const createStorageMock = () => ({
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
});

Object.defineProperty(window, 'localStorage', {
  value: createStorageMock(),
});

Object.defineProperty(window, 'sessionStorage', {
  value: createStorageMock(),
});

// Mock console methods for cleaner test output
const originalError = console.error;
const originalWarn = console.warn;

beforeAll(() => {
  console.error = (...args: any[]) => {
    // Don't log expected errors in tests
    if (
      typeof args[0] === 'string' &&
      (args[0].includes('Warning:') ||
       args[0].includes('Error:') ||
       args[0].includes('act('))
    ) {
      return;
    }
    originalError.call(console, ...args);
  };

  console.warn = (...args: any[]) => {
    // Don't log expected warnings in tests
    if (
      typeof args[0] === 'string' &&
      args[0].includes('Warning:')
    ) {
      return;
    }
    originalWarn.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
  console.warn = originalWarn;
});

// Add React import for React.createElement mock
import React from 'react';