/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        clinic: {
          void: '#0a0e17',
          panel: '#101827',
          cyan: '#00e5cc',
          teal: '#17f5d2',
          bone: '#f0f4f8',
          muted: '#8ea0b8',
          amber: '#fbbf24',
          red: '#fb7185',
          green: '#34d399',
        },
      },
      fontFamily: {
        mono: ['Space Mono', 'monospace'],
        sans: ['DM Sans', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        glow: '0 0 34px rgba(0, 229, 204, 0.24)',
        card: '0 24px 80px rgba(0, 0, 0, 0.36)',
      },
      animation: {
        pulseBorder: 'pulseBorder 2.4s ease-in-out infinite',
        shimmer: 'shimmer 1.8s linear infinite',
        scan: 'scan 2.2s ease-in-out infinite',
        waveform: 'waveform 1s ease-in-out infinite',
      },
      keyframes: {
        pulseBorder: {
          '0%, 100%': { boxShadow: '0 0 0 rgba(0, 229, 204, 0)' },
          '50%': { boxShadow: '0 0 28px rgba(0, 229, 204, 0.38)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% center' },
          '100%': { backgroundPosition: '200% center' },
        },
        scan: {
          '0%': { transform: 'translateY(-120%)' },
          '100%': { transform: 'translateY(420%)' },
        },
        waveform: {
          '0%, 100%': { transform: 'scaleY(0.45)' },
          '50%': { transform: 'scaleY(1)' },
        },
      },
    },
  },
  plugins: [],
};
