import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Brand violet — the primary Lumio identity colour.
        primary: {
          50: '#f5f3ff',
          100: '#ede9fe',
          200: '#ddd6fe',
          300: '#c4b5fd',
          400: '#a78bfa',
          500: '#8b5cf6',
          600: '#7c3aed',
          700: '#6d28d9',
          800: '#5b21b6',
          900: '#4c1d95',
        },
        // Cyan accent used for gradients, glows and secondary highlights.
        accent: {
          50: '#ecfeff',
          100: '#cffafe',
          200: '#a5f3fc',
          300: '#67e8f9',
          400: '#22d3ee',
          500: '#06b6d4',
          600: '#0891b2',
          700: '#0e7490',
        },
        ink: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
          950: '#020617',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        // Layered shadows: a tight contact shadow plus a wide soft one reads as
        // real depth, which a single flat shadow never does.
        'depth-sm': '0 1px 2px rgba(15,23,42,.04), 0 4px 12px -2px rgba(15,23,42,.06)',
        depth: '0 1px 3px rgba(15,23,42,.05), 0 8px 24px -4px rgba(15,23,42,.08)',
        'depth-lg': '0 2px 4px rgba(15,23,42,.04), 0 16px 40px -8px rgba(15,23,42,.12)',
        'depth-xl': '0 4px 8px rgba(15,23,42,.04), 0 28px 60px -12px rgba(15,23,42,.18)',
        // Coloured glows for primary actions and focus states.
        glow: '0 8px 24px -6px rgba(124,58,237,.45)',
        'glow-lg': '0 16px 40px -8px rgba(124,58,237,.5)',
        'glow-accent': '0 8px 24px -6px rgba(6,182,212,.45)',
        // Inset highlight along the top edge — the classic "lit from above" 3D cue.
        bevel: 'inset 0 1px 0 rgba(255,255,255,.6)',
        'bevel-dark': 'inset 0 1px 0 rgba(255,255,255,.15)',
      },
      backgroundImage: {
        'gradient-brand': 'linear-gradient(135deg, #7c3aed 0%, #8b5cf6 50%, #06b6d4 100%)',
        'gradient-brand-soft': 'linear-gradient(135deg, #ede9fe 0%, #f5f3ff 50%, #ecfeff 100%)',
        'gradient-sheen':
          'linear-gradient(180deg, rgba(255,255,255,.25) 0%, rgba(255,255,255,0) 60%)',
      },
      keyframes: {
        'float-slow': {
          '0%,100%': { transform: 'translate3d(0,0,0) scale(1)' },
          '50%': { transform: 'translate3d(0,-24px,0) scale(1.05)' },
        },
        'fade-up': {
          from: { opacity: '0', transform: 'translate3d(0,12px,0)' },
          to: { opacity: '1', transform: 'translate3d(0,0,0)' },
        },
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
      },
      animation: {
        'float-slow': 'float-slow 14s ease-in-out infinite',
        'fade-up': 'fade-up .5s cubic-bezier(.21,1.02,.73,1) both',
        shimmer: 'shimmer 2s infinite',
      },
    },
  },
  plugins: [],
} satisfies Config
