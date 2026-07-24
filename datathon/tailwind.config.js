/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'primary-bg': 'var(--primary-bg)',
        'secondary-bg': 'var(--secondary-bg)',
        'card-bg': 'var(--card-bg)',
        'border-color': 'var(--border-color)',
        'accent-blue': 'var(--accent-blue)',
        'accent-teal': 'var(--accent-teal)',
        'accent-amber': 'var(--accent-amber)',
        'accent-coral': 'var(--accent-coral)',
        'accent-purple': 'var(--accent-purple)',
        'primary-text': 'var(--primary-text)',
        'secondary-text': 'var(--secondary-text)',
        'muted-text': 'var(--muted-text)',
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
      },
      keyframes: {
        slideInRight: {
          '0%': { transform: 'translateX(100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
      },
      animation: {
        'slide-in-right': 'slideInRight 0.3s ease-out',
      }
    },
  },
  plugins: [],
}
