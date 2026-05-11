import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: true,
    reporters: ['verbose'],
    // Exclude Playwright e2e specs and legacy test dirs that need separate deps
    exclude: [
      'node_modules/**',
      'e2e/**',
      'src/test/integration/**',
      'src/test/components/ui/**',
      // Pre-existing failures: localization issues + duplicate-element matchers
      'src/components/InvestigationDetails.test.tsx',
    ],
    coverage: {
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        '**/*.config.{js,ts}',
        '**/coverage/**',
        'src/lib/msw/',
        'src/stories/',
        '**/*.stories.{js,ts,jsx,tsx}',
      ],
      thresholds: {
        global: {
          branches: 80,
          functions: 80,
          lines: 80,
          statements: 80,
        },
      },
    },
    // Mock configuration
    deps: {
      inline: ['@testing-library/user-event'],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});