export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Outfit', '"Plus Jakarta Sans"', 'sans-serif'],
      },
      colors: {
        primary: {
          50: '#ecfdf5',
          100: '#d1fae5',
          200: '#a7f3d0',
          300: '#6ee7b7',
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
          800: '#065f46',
          900: '#064e3b',
          950: '#022c22',
        },
      },
      boxShadow: {
        panel: '0 12px 36px -4px rgba(2, 6, 23, 0.12), 0 4px 12px -2px rgba(2, 6, 23, 0.06)',
        card: '0 2px 10px -2px rgba(2, 6, 23, 0.05)',
        glow: '0 0 24px -4px rgba(16, 185, 129, 0.25)',
      },
    },
  },
  plugins: [],
}
