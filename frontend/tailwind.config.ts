/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        background: '#0A0E17',
        card: '#151B29',
        primary: {
          DEFAULT: '#635BFF',
          foreground: '#F5F5F7',
        },
        success: {
          DEFAULT: '#00D4A0',
          foreground: '#0A0E17',
        },
        foreground: '#F5F5F7',
        muted: {
          DEFAULT: '#1E2640',
          foreground: '#8B9CC7',
        },
        border: '#252D45',
        destructive: {
          DEFAULT: '#E5484D',
          foreground: '#F5F5F7',
        },
        warning: {
          DEFAULT: '#E8A23B',
          foreground: '#0A0E17',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      borderRadius: {
        lg: '0.75rem',
        md: '0.5rem',
        sm: '0.375rem',
      },
      boxShadow: {
        'glow-primary': '0 0 20px rgba(99, 91, 255, 0.25)',
        'glow-success': '0 0 20px rgba(0, 212, 160, 0.25)',
        'card': '0 4px 24px rgba(0, 0, 0, 0.4)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
}
