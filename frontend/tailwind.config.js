/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        growwGreen: "#00D09C",
        growwDark: "#121212",
        growwCard: "#1E222B",
        growwBorder: "#2E323E"
      }
    },
  },
  plugins: [],
}