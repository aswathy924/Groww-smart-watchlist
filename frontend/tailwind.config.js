/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      colors: {
        surface: {
          950: 'var(--color-surface-950)',
          900: 'var(--color-surface-900)',
          850: 'var(--color-surface-850)',
          800: 'var(--color-surface-800)',
          700: 'var(--color-surface-700)',
          600: 'var(--color-surface-600)',
          500: 'var(--color-surface-500)',
          400: 'var(--color-surface-400)',
        },
        accent: {
          green:  '#00D09C', // Emerald accent
          red:    '#FF5C5C', // Soft coral red
          yellow: '#FDBA2D', // Warm amber gold
          blue:   '#38BDF8', // Sky cyan
          purple: '#A78BFA', // Violet
        },
        text: {
          primary:   'var(--color-text-primary)',
          secondary: 'var(--color-text-secondary)',
          muted:     'var(--color-text-muted)',
        },
        themeborder: {
          subtle: 'var(--border-subtle)',
          strong: 'var(--border-strong)',
        }
      },
      boxShadow: {
        'card': 'var(--card-shadow)',
        'card-hover': '0 8px 30px -4px rgba(0, 0, 0, 0.15), 0 0 15px rgba(0, 208, 156, 0.08)',
        'glow-green': '0 0 25px rgba(0, 208, 156, 0.2)',
        'glow-red': '0 0 25px rgba(255, 92, 92, 0.2)',
      },
      animation: {
        'fade-in': 'fadeIn 0.25s ease-out',
        'slide-up': 'slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-down': 'slideDown 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideDown: {
          '0%': { opacity: '0', transform: 'translateY(-10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}