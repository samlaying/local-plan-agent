import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Design System Color Palette
        'paper-bg': '#F8F1E7',
        'card-bg': '#FFFDF8',
        'card-soft': '#FBF6EC',
        'clay-orange': '#D97745',
        'clay-orange-dark': '#C95F2E',
        'pine-green': '#4F6F52',
        'pine-green-soft': '#E8EFE4',
        'ink': '#2B2118',
        'muted': '#8A7A68',
        'line': '#E8DCCB',
        'success': '#6A994E',
        'warning': '#C0842D',
        'danger': '#C75C48',
      },
      borderRadius: {
        '3xl': '1.5rem', // 24px - 符合设计指南
      },
      spacing: {
        '18': '4.5rem', // 72px - AppHeader 高度
        '22': '5.5rem', // 220px - SideNav 宽度
        '75': '18.75rem', // 300px - RightContextPanel 宽度
      },
      fontFamily: {
        sans: [
          'PingFang SC',
          'Hiragino Sans GB',
          'Microsoft YaHei',
          'Noto Sans SC',
          'sans-serif',
        ],
      },
      boxShadow: {
        'paper': '0 12px 30px rgba(43, 33, 24, 0.06)',
        'paper-hover': '0 18px 40px rgba(43, 33, 24, 0.10)',
        'clay': '0 4px 14px rgba(217, 119, 69, 0.3)',
        'clay-hover': '0 6px 20px rgba(217, 119, 69, 0.4)',
      },
      animation: {
        'fade-up': 'fadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1)',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeUp: {
          '0%': {
            opacity: '0',
            transform: 'translateY(12px)',
          },
          '100%': {
            opacity: '1',
            transform: 'translateY(0)',
          },
        },
      },
      transitionTimingFunction: {
        'premium': 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
    },
  },
  plugins: [],
};

export default config;
