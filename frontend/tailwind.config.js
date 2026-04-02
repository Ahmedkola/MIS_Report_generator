/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: '#111827',
          raised: '#1C2333',
          border: '#1E293B',
        },
        gold: {
          DEFAULT: '#C9A84C',
          light: '#E2C46A',
          dark: '#A07830',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
