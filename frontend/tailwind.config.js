export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          500: '#22c55e',
          600: '#16a34a'
        }
      },
      boxShadow: {
        panel: '0 20px 45px rgba(15, 23, 42, 0.18)'
      }
    },
  },
  plugins: [],
}
