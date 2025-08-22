import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { I18nProvider } from '@/components/providers/i18n-provider';
import { ThemeProvider } from '@/components/providers/theme-provider';
import { ErrorProvider } from '@/components/providers/error-provider';
import { ToastProvider } from '@/components/providers/toast-provider';

// Create a custom render function that includes providers
const AllTheProviders = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: Infinity,
      },
      mutations: {
        retry: false,
      },
    },
  });

  return (
    <ErrorProvider>
      <I18nProvider>
        <ThemeProvider attribute="class" defaultTheme="light">
          <QueryClientProvider client={queryClient}>
            {children}
            <ToastProvider />
          </QueryClientProvider>
        </ThemeProvider>
      </I18nProvider>
    </ErrorProvider>
  );
};

const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => render(ui, { wrapper: AllTheProviders, ...options });

// Re-export everything
export * from '@testing-library/react';
export { customRender as render };

// Custom render for components that need specific providers
export const renderWithQueryClient = (
  ui: ReactElement,
  options?: {
    queryClient?: QueryClient;
  } & Omit<RenderOptions, 'wrapper'>
) => {
  const { queryClient = new QueryClient(), ...renderOptions } = options || {};

  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );

  return render(ui, { wrapper: Wrapper, ...renderOptions });
};

// Render with i18n only
export const renderWithI18n = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => {
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <I18nProvider>{children}</I18nProvider>
  );

  return render(ui, { wrapper: Wrapper, ...options });
};

// Render with theme provider
export const renderWithTheme = (
  ui: ReactElement,
  options?: {
    theme?: 'light' | 'dark' | 'system';
  } & Omit<RenderOptions, 'wrapper'>
) => {
  const { theme = 'light', ...renderOptions } = options || {};

  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <ThemeProvider attribute="class" defaultTheme={theme}>
      {children}
    </ThemeProvider>
  );

  return render(ui, { wrapper: Wrapper, ...renderOptions });
};

// Mock utilities
export const createMockRouter = (overrides = {}) => ({
  push: vi.fn(),
  replace: vi.fn(),
  back: vi.fn(),
  forward: vi.fn(),
  refresh: vi.fn(),
  prefetch: vi.fn(),
  ...overrides,
});

export const createMockSearchParams = (params: Record<string, string> = {}) => ({
  get: vi.fn((key: string) => params[key] || null),
  getAll: vi.fn((key: string) => params[key] ? [params[key]] : []),
  has: vi.fn((key: string) => key in params),
  keys: vi.fn(() => Object.keys(params)[Symbol.iterator]()),
  values: vi.fn(() => Object.values(params)[Symbol.iterator]()),
  entries: vi.fn(() => Object.entries(params)[Symbol.iterator]()),
  toString: vi.fn(() => new URLSearchParams(params).toString()),
});

// Test data factories
export const createMockLead = (overrides = {}) => ({
  id: '1',
  email: 'test@example.com',
  name: 'Test User',
  company: 'Test Company',
  job_title: 'Developer',
  confidence_score: 85,
  verification_status: 'verified' as const,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  ...overrides,
});

export const createMockSource = (overrides = {}) => ({
  id: '1',
  name: 'Test Source',
  type: 'website' as const,
  status: 'active' as const,
  configuration: {},
  leads_count: 10,
  success_rate: 0.8,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  ...overrides,
});

export const createMockCampaign = (overrides = {}) => ({
  id: '1',
  name: 'Test Campaign',
  description: 'Test Description',
  status: 'active' as const,
  filter_criteria: {},
  leads_count: 5,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  ...overrides,
});

export const createMockUser = (overrides = {}) => ({
  id: '1',
  email: 'test@example.com',
  name: 'Test User',
  role: 'admin' as const,
  isVerified: true,
  createdAt: '2024-01-01T00:00:00Z',
  permissions: ['leads:read', 'leads:write'],
  ...overrides,
});

// Async utilities
export const waitForLoadingToFinish = () => {
  return new Promise(resolve => setTimeout(resolve, 0));
};

// Form testing utilities
export const fillFormField = async (
  user: any,
  fieldLabel: string,
  value: string
) => {
  const field = screen.getByLabelText(fieldLabel);
  await user.clear(field);
  await user.type(field, value);
};

export const submitForm = async (user: any, buttonText = 'Submit') => {
  const submitButton = screen.getByRole('button', { name: buttonText });
  await user.click(submitButton);
};

// Accessibility testing utilities
export const expectToBeAccessible = async (container: HTMLElement) => {
  // Basic accessibility checks without axe-core dependency
  // Check for common accessibility issues
  const images = container.querySelectorAll('img');
  images.forEach(img => {
    expect(img).toHaveAttribute('alt');
  });

  const buttons = container.querySelectorAll('button');
  buttons.forEach(button => {
    expect(button).toHaveAccessibleName();
  });

  const inputs = container.querySelectorAll('input');
  inputs.forEach(input => {
    if (input.type !== 'hidden') {
      expect(input).toHaveAccessibleName();
    }
  });
};

// Mock fetch for API testing
export const mockFetch = (response: any, options: { status?: number; ok?: boolean } = {}) => {
  const { status = 200, ok = true } = options;

  global.fetch = vi.fn(() =>
    Promise.resolve({
      ok,
      status,
      json: () => Promise.resolve(response),
      text: () => Promise.resolve(JSON.stringify(response)),
    } as Response)
  );
};

// Wait for element to disappear
export const waitForElementToBeRemoved = async (element: HTMLElement) => {
  const { waitForElementToBeRemoved: waitFor } = await import('@testing-library/react');
  return waitFor(element);
};

// Custom matchers and assertions
export const expectToHaveClass = (element: HTMLElement, className: string) => {
  expect(element).toHaveClass(className);
};

export const expectToBeVisible = (element: HTMLElement) => {
  expect(element).toBeVisible();
};

export const expectToBeHidden = (element: HTMLElement) => {
  expect(element).not.toBeVisible();
};

// Performance testing utilities
export const measureRenderTime = async (renderFn: () => void) => {
  const start = performance.now();
  renderFn();
  await waitForLoadingToFinish();
  const end = performance.now();
  return end - start;
};

// Error boundary testing
export const expectErrorBoundary = (renderFn: () => void) => {
  const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

  expect(() => renderFn()).toThrow();

  spy.mockRestore();
};

// Keyboard navigation testing
export const pressKey = async (user: any, key: string) => {
  await user.keyboard(`{${key}}`);
};

export const pressKeys = async (user: any, keys: string[]) => {
  for (const key of keys) {
    await pressKey(user, key);
  }
};

// Import required testing utilities
import { vi } from 'vitest';
import { screen } from '@testing-library/react';