/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        apple: {
          blue: '#0071e3',
          text: '#1d1d1f',
          secondary: '#6e6e73',
          tertiary: '#86868b',
          bg: '#f5f5f7',
          border: '#e8e8ed',
          card: 'rgba(255,255,255,0.8)',
        },
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'SF Pro Display', 'Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        apple: '12px',
        'apple-lg': '18px',
        'apple-xl': '22px',
      },
      boxShadow: {
        apple: '0 2px 12px rgba(0,0,0,0.06)',
        'apple-md': '0 4px 24px rgba(0,0,0,0.08)',
        'apple-hover': '0 8px 32px rgba(0,0,0,0.12)',
      },
      animation: {
        'fade-in': 'fadeIn 0.4s ease-out forwards',
        'slide-up': 'slideUp 0.4s ease-out forwards',
      },
      keyframes: {
        fadeIn: { from: { opacity: '0' }, to: { opacity: '1' } },
        slideUp: { from: { opacity: '0', transform: 'translateY(12px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
      },
    },
  },
  plugins: [],
};
