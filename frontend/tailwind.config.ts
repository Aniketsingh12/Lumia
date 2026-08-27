import type { Config } from 'tailwindcss'

/**
 * Lumio design system — dark, single-theme.
 *
 * Semantic colours are driven by HSL custom properties defined in
 * src/styles/globals.css, referenced here as hsl(var(--token)). Components
 * should prefer the semantic names (bg-background, text-foreground,
 * text-muted-foreground, border-border, bg-primary) over raw scale steps.
 *
 * ── Why the `gray` and `ink` scales are INVERTED ──────────────────────────
 * This app was originally built light-theme, so ~200 utilities across ~30
 * files read `text-gray-900` for headings, `bg-gray-50` for recessed panels,
 * `text-ink-600` for secondary copy, and so on — i.e. "high step = dark".
 *
 * Rather than rewrite every one of those call sites (churn with a high chance
 * of missing some and shipping unreadable dark-on-dark text), both neutral
 * scales are mirrored end-for-end: step 50 is now the DARKEST and step 950 the
 * lightest. `text-gray-900` therefore resolves to near-white on the dark
 * background and `bg-gray-50` to a near-black recessed surface — every existing
 * call site keeps its original *intent* (primary text / recessed panel) and
 * simply renders correctly against a dark ground.
 *
 * The mental model stays "higher step = more contrast against the page".
 * `white` and `black` are deliberately left alone so they still mean what they
 * say; surfaces use the semantic tokens instead.
 */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        'nav-button': 'hsl(var(--nav-button))',
        'hero-bg': 'hsl(var(--hero-bg))',

        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
          // Numeric steps so pre-existing `bg-primary-600` / `text-primary-400`
          // call sites keep working. They ramp around the brand green
          // (119 99% 46%) rather than the old violet.
          50: '#eafff0',
          100: '#c9ffd9',
          200: '#93ffb6',
          300: '#4dfc8a',
          400: '#1af35f',
          500: '#05e04a',
          600: '#02c93f',
          700: '#04a035',
          800: '#0a7c2e',
          900: '#0b6628',
          950: '#003a13',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
          // Accent shares the brand green; steps kept for legacy call sites.
          50: '#eafff0',
          100: '#c9ffd9',
          200: '#93ffb6',
          300: '#4dfc8a',
          400: '#1af35f',
          500: '#05e04a',
          600: '#02c93f',
          700: '#04a035',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },

        // ── Inverted neutral scales (see file header) ──
        gray: {
          50: '#0d0d0d',
          100: '#141414',
          200: '#1f1f1f',
          300: '#2e2e2e',
          400: '#8a8a8a',
          500: '#9a9a9a',
          600: '#b4b4b4',
          700: '#d0d0d0',
          800: '#e4e4e4',
          900: '#f5f5f5',
          950: '#ffffff',
        },
        ink: {
          50: '#0d0d0d',
          100: '#141414',
          200: '#1f1f1f',
          300: '#2e2e2e',
          400: '#8a8a8a',
          500: '#9a9a9a',
          600: '#b4b4b4',
          700: '#d0d0d0',
          800: '#e4e4e4',
          900: '#f5f5f5',
          950: '#ffffff',
        },
      },
      fontFamily: {
        sora: ['Sora', 'sans-serif'],
        sans: ['Sora', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      boxShadow: {
        // Dark themes read depth from glow and border contrast far more than
        // from drop shadows, so these are heavier and cooler than the originals.
        'depth-sm': '0 1px 2px rgba(0,0,0,.5), 0 4px 12px -2px rgba(0,0,0,.45)',
        depth: '0 1px 3px rgba(0,0,0,.55), 0 8px 24px -4px rgba(0,0,0,.5)',
        'depth-lg': '0 2px 4px rgba(0,0,0,.5), 0 16px 40px -8px rgba(0,0,0,.55)',
        'depth-xl': '0 4px 8px rgba(0,0,0,.5), 0 28px 60px -12px rgba(0,0,0,.65)',
        glow: '0 8px 24px -6px hsl(var(--primary) / .45)',
        'glow-lg': '0 16px 40px -8px hsl(var(--primary) / .55)',
        'glow-accent': '0 8px 24px -6px hsl(var(--accent) / .45)',
        bevel: 'inset 0 1px 0 rgba(255,255,255,.06)',
        'bevel-dark': 'inset 0 1px 0 rgba(255,255,255,.04)',
      },
      backgroundImage: {
        'gradient-brand': 'linear-gradient(135deg, hsl(var(--primary)) 0%, #1af35f 50%, #93ffb6 100%)',
        'gradient-brand-soft': 'linear-gradient(135deg, rgba(5,224,74,.16) 0%, rgba(5,224,74,.04) 60%, transparent 100%)',
        'gradient-sheen': 'linear-gradient(180deg, rgba(255,255,255,.08) 0%, rgba(255,255,255,0) 60%)',
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(20px)', filter: 'blur(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)', filter: 'blur(0)' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'float-slow': {
          '0%,100%': { transform: 'translate3d(0,0,0) scale(1)' },
          '50%': { transform: 'translate3d(0,-24px,0) scale(1.05)' },
        },
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
      },
      animation: {
        'fade-up': 'fade-up 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'fade-in': 'fade-in 0.5s ease-out forwards',
        'float-slow': 'float-slow 14s ease-in-out infinite',
        shimmer: 'shimmer 2s infinite',
      },
    },
  },
  plugins: [],
} satisfies Config
