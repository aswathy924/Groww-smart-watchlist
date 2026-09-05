/** @type {import('tailwindcss').Config} */
export default {
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
          950: '#080A0F',   // darkest base
          900: '#0C0F17',   // main app background
          850: '#111520',   // elevated bg
          800: '#151A27',   // primary card bg
          700: '#1C2333',   // secondary card / hover
          600: '#252F44',   // interactive / input bg
          500: '#323D56',   // active borders
          400: '#475569',   // subtle borders
        },
        accent: {
          green:  '#00D09C', // Groww signature green
          red:    '#FF5C5C', // Soft coral red
          yellow: '#FDBA2D', // Warm amber gold
          blue:   '#38BDF8', // Sky cyan
          purple: '#A78BFA', // Violet
        },
        text: {
          primary:   '#F8FAFC',
          secondary: '#94A3B8',
          muted:     '#64748B',
        }
      },
      boxShadow: {
        'card': '0 4px 20px -2px rgba(0, 0, 0, 0.5), 0 2px 6px -1px rgba(0, 0, 0, 0.3)',
        'card-hover': '0 8px 30px -4px rgba(0, 0, 0, 0.6), 0 0 15px rgba(0, 208, 156, 0.08)',
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