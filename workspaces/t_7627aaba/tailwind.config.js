/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // AVO theme — deep blues and tech accent
        'avo-bg': '#0f172a',
        'avo-surface': '#1e293b',
        'avo-border': '#33415d',
        'avo-text': '#e2e8f0',
        'avo-text-muted': '#94a3a5',
        // Agent status colors
        'status-planning': '#fbbf24', // amber
        'status-executing': '#38bdf8', // sky blue
        'status-observing': '#a78bfa', // violet
        'status-done': '#4ade80', // green
        'status-failed': '#f87171', // red
        // HTN node status colors
        'node-pending': '#64748b',
        'node-running': '#38bdf8',
        'node-complete': '#4ade80',
        'node-failed': '#f87171',
      },
      animation: {
        'pulse-subtle': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-in': 'bounce-in 0.3s ease-out',
      },
      keyframes: {
        'bounce-in': {
          '0%': { opacity: '0', transform: 'scale(0.9)' },
          '50%': { transform: 'scale(1.02)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
      },
    },
  },
  plugins: [],
};
