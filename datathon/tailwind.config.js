/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'sk-bg': {
          primary: 'var(--bg-primary)',
          secondary: 'var(--bg-secondary)',
          tertiary: 'var(--bg-tertiary)',
          elevated: 'var(--bg-elevated)',
          surface: 'var(--bg-surface)',
        },
        'sk-border': {
          primary: 'var(--border-primary)',
          secondary: 'var(--border-secondary)',
          focus: 'var(--border-focus)',
        },
        'sk-text': {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          muted: 'var(--text-muted)',
          disabled: 'var(--text-disabled)',
        },
        'sk-blue': 'var(--accent-blue)',
        'sk-teal': 'var(--accent-teal)',
        'sk-amber': 'var(--accent-amber)',
        'sk-coral': 'var(--accent-coral)',
        'sk-purple': 'var(--accent-purple)',
        /* Legacy aliases used across codebase */
        'secondary-bg': 'var(--bg-secondary)',
        'primary-bg': 'var(--bg-primary)',
        'tertiary-bg': 'var(--bg-tertiary)',
        'primary-text': 'var(--text-primary)',
        'secondary-text': 'var(--text-secondary)',
        'muted-text': 'var(--text-muted)',
        'disabled-text': 'var(--text-disabled)',
        'border-color': 'var(--border-primary)',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        display: ['Space Grotesk', 'Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      borderRadius: {
        'xs': '4px',
        'sm': '6px',
        'md': '8px',
        'lg': '12px',
        'xl': '16px',
        '2xl': '20px',
      },
      boxShadow: {
        'sk-xs': 'var(--shadow-xs)',
        'sk-sm': 'var(--shadow-sm)',
        'sk-md': 'var(--shadow-md)',
        'sk-lg': 'var(--shadow-lg)',
        'sk-xl': 'var(--shadow-xl)',
        'sk-blue': 'var(--shadow-glow-blue)',
        'sk-teal': 'var(--shadow-glow-teal)',
        'sk-amber': 'var(--shadow-glow-amber)',
        'sk-coral': 'var(--shadow-glow-coral)',
        'sk-purple': 'var(--shadow-glow-purple)',
        'glow-blue': '0 0 15px rgba(37, 99, 235, 0.4)',
        'glow-teal': '0 0 15px rgba(16, 185, 129, 0.4)',
        'glow-amber': '0 0 15px rgba(245, 158, 11, 0.4)',
        'glow-coral': '0 0 15px rgba(239, 68, 68, 0.4)',
        'glow-purple': '0 0 15px rgba(139, 92, 246, 0.4)',
      },
      spacing: {
        '4.5': '18px',
        '13': '52px',
        '15': '60px',
        '18': '72px',
        '22': '88px',
        '26': '104px',
        'sidebar': '260px',
        'sidebar-collapsed': '64px',
        'header': '64px',
      },
      keyframes: {
        'sk-fade-in': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'sk-fade-out': {
          '0%': { opacity: '1', transform: 'translateY(0)' },
          '100%': { opacity: '0', transform: 'translateY(-8px)' },
        },
        'sk-slide-in-right': {
          '0%': { transform: 'translateX(100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        'sk-slide-in-left': {
          '0%': { transform: 'translateX(-100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        'sk-scale-in': {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        'sk-shimmer': {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'sk-pulse-dot': {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.5', transform: 'scale(1.2)' },
        },
        'sk-spin-slow': {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
      },
      animation: {
        'sk-fade-in': 'sk-fade-in 0.3s ease-out',
        'sk-fade-out': 'sk-fade-out 0.2s ease-in',
        'sk-slide-in-right': 'sk-slide-in-right 0.3s ease-out',
        'sk-slide-in-left': 'sk-slide-in-left 0.3s ease-out',
        'sk-scale-in': 'sk-scale-in 0.2s ease-out',
        'sk-shimmer': 'sk-shimmer 1.5s ease-in-out infinite',
        'sk-pulse-dot': 'sk-pulse-dot 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'sk-spin-slow': 'sk-spin-slow 2s linear infinite',
      },
      transitionDuration: {
        '250': '250ms',
        '350': '350ms',
      },
      backdropBlur: {
        'xs': '2px',
      },
    },
  },
  plugins: [],
}
