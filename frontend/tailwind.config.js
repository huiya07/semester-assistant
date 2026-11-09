/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // 主色：靛蓝系（避开 Claude 的陶土橙，保证原创性）
        brand: {
          50: '#f2f5fb',
          100: '#e3eaf7',
          200: '#c7d6ee',
          300: '#a3bce0',
          400: '#7a9bd0',
          500: '#557dbf',
          600: '#3f61a3',
          700: '#344d84',
          800: '#2d426d',
          900: '#293a5c',
        },
        surface: {
          0: '#ffffff',
          1: '#fafaf8',
          2: '#f4f4f1',
          3: '#eceae5',
        },
        ink: {
          900: '#1f1e1d',
          700: '#3a3937',
          500: '#6b6a67',
          400: '#8a8984',
          300: '#a8a7a1',
        },
      },
      fontFamily: {
        sans: [
          '"Noto Sans SC"',
          '"Microsoft YaHei"',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'sans-serif',
        ],
        mono: ['"JetBrains Mono"', 'Consolas', 'monospace'],
      },
      borderRadius: {
        card: '14px',
        field: '10px',
      },
      boxShadow: {
        soft: '0 1px 2px rgba(31,30,29,0.04), 0 4px 16px rgba(31,30,29,0.06)',
        pop: '0 8px 32px rgba(31,30,29,0.12), 0 2px 8px rgba(31,30,29,0.06)',
      },
      transitionTimingFunction: {
        // 借用 CDS 的减速曲线：物理参数，不是设计资产
        'sa-out': 'cubic-bezier(0.22, 1, 0.36, 1)',
      },
    },
  },
  plugins: [],
}
