/**
 * Vite config for mocked development mode.
 * Enables MSW browser worker so `npm run dev:mocked` runs against
 * fixture data without a real backend.
 *
 * @see vite.config.ts (real mode — proxies to localhost:3998)
 */
import { defineConfig, PluginOption } from 'vite';
import react from '@vitejs/plugin-react';

// Plugin that injects MSW browser start into main.tsx for mocked dev mode
function mswPlugin(): PluginOption {
  return {
    name: 'vite-plugin-msw-dev',
    transform(code, id) {
      if (id.includes('src/main.tsx')) {
        const mswImport =
          'import("./mocks/browser").then(({ startMockServiceWorker }) => startMockServiceWorker());\n';
        return `${mswImport}${code}`;
      }
      return null;
    },
  };
}

export default defineConfig(({ command }) => {
  const isMocked = command === 'serve';
  return {
    plugins: [
      react(),
      ...(isMocked ? [mswPlugin()] : []),
    ],
    server: {
      port: 3999,
      host: true,
    },
    build: {
      sourcemap: true,
      rollupOptions: {
        output: {
          manualChunks: {
            'react-vendor': ['react', 'react-dom', 'react-router-dom'],
            'store': ['zustand'],
          },
        },
      },
    },
    test: {
      environment: 'jsdom',
      setupFiles: ['./tests/setup.ts'],
      css: true,
      include: ['src/**/*.{test,spec}.{ts,tsx}', 'tests/**/*.{test,spec}.{ts,tsx}'],
      coverage: {
        reporter: ['text', 'html'],
        exclude: ['node_modules/', 'tests/setup.ts'],
      },
    },
  };
});
