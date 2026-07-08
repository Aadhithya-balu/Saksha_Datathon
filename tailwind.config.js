/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'primary-bg': '#0B1426',
        'secondary-bg': '#111D35',
        'card-bg': 'rgba(255, 255, 255, 0.04)',
        'border-color': 'rgba(255, 255, 255, 0.07)',
        'accent-blue': '#1E6FD9',
        'accent-teal': '#0E9E78',
        'accent-amber': '#D4820A',
        'accent-coral': '#C94A2A',
        'accent-purple': '#6C43CC',
        'primary-text': '#E8EDF5',
        'secondary-text': '#A8B4CC',
        'muted-text': '#6A7A96',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'glow-blue': '0 0 15px rgba(30, 111, 217, 0.35)',
        'glow-teal': '0 0 15px rgba(14, 158, 120, 0.35)',
        'glow-amber': '0 0 15px rgba(212, 130, 10, 0.35)',
        'glow-coral': '0 0 15px rgba(201, 74, 42, 0.35)',
        'glow-purple': '0 0 15px rgba(108, 67, 204, 0.35)',
        'glow-active-icon': '0 0 20px rgba(30, 111, 217, 0.65)',
      },
      borderRadius: {
        'card': '10px',
        'btn': '6px',
      }
    },
  },
  plugins: [],
}
