/**
 * Tailwind 配置：本项目基础 token + 从 open-claude-ui（MIT）并入的 CDS 设计系统 token。
 *
 * 关键改动：CDS 的 `clay`（陶土橙 #d97757）整体替换为本项目的靛蓝主色。
 * 这样拷进来的 CDS 组件无需逐个改类名，直接沿用本项目的配色体系，
 * 既拿到它的结构/动效打磨，又不会长得像 Claude 桌面端（原创性要求）。
 */
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // ---- 本项目主色（靛蓝），替换 CDS 的 clay ----
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
        clay: {
          DEFAULT: '#3f61a3',
          hover: '#344d84',
          light: '#eef2f9',
          dark: '#557dbf',
        },
        // ---- 表面色（走 CDS 变量，值在 index.css 里覆盖成暖白）----
        surface: {
          0: 'var(--cds-surface-0)',
          1: 'var(--cds-surface-1)',
          2: 'var(--cds-surface-2)',
          3: 'var(--cds-surface-3)',
          popover: 'var(--cds-surface-popover)',
        },
        ink: {
          900: '#1f1e1d',
          700: '#3a3937',
          600: '#52514e',
          500: '#6b6a67',
          400: '#8a8984',
          300: '#a8a7a1',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          '"Noto Sans SC"',
          '"Microsoft YaHei"',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'sans-serif',
        ],
        mono: ['"JetBrains Mono"', 'Consolas', 'monospace'],
      },
      fontSize: {
        // CDS 组件用到的语义字号（原仓库未开源，此处按实际用法定量补齐）
        heading: ['15px', { lineHeight: '1.5' }],
        body: ['14px', { lineHeight: '1.6' }],
        caption: ['12px', { lineHeight: '1.5' }],
      },
      spacing: {
        xs: '0.5rem',
      },
      transitionDuration: {
        fast: '150ms',
        base: '200ms',
      },
      borderRadius: {
        card: '14px',
        field: '10px',
        panel: 'var(--cds-panel-radius, 10px)',
        bubble: 'var(--cds-message-bubble-radius, 18px)',
        composer: 'var(--cds-radius-composer, 20px)',
        pill: '999px',
      },
      boxShadow: {
        // 本项目
        soft: '0 1px 2px rgba(31,30,29,0.04), 0 4px 16px rgba(31,30,29,0.06)',
        pop: '0 8px 32px rgba(31,30,29,0.12), 0 2px 8px rgba(31,30,29,0.06)',
        // 补齐 CDS 组件依赖、但原仓库未提供定义的两个（否则组件会缺阴影）
        '2xs': '0 1px 2px rgba(31,30,29,0.05)',
        field: 'inset 0 0 0 1px rgba(31,30,29,0.08)',
        // CDS 变量投影
        sm: 'var(--cds-shadow-sm, 0 1px 2px rgba(0,0,0,0.05))',
        md: 'var(--cds-shadow-md, 0 2px 8px rgba(0,0,0,0.08))',
        lg: 'var(--cds-shadow-lg, 0 8px 24px rgba(0,0,0,0.1))',
        popover: 'var(--cds-shadow-popover, 0 8px 32px rgba(31,30,29,0.14))',
        composer: 'var(--cds-shadow-composer, 0 1px 2px rgba(31,30,29,0.05))',
        'composer-hover': 'var(--cds-shadow-composer-hover, 0 2px 8px rgba(31,30,29,0.08))',
        'composer-focus': 'var(--cds-shadow-composer-focus, 0 0 0 4px rgba(63,97,163,0.12))',
        'focus-glow': 'var(--cds-focus-shadow, 0 0 0 3px rgba(63,97,163,0.18))',
        'drop-glow': 'var(--cds-shadow-drop-glow, 0 0 24px rgba(63,97,163,0.2))',
        panel: 'var(--cds-panel-shadow, 0 1px 3px rgba(31,30,29,0.06))',
        'panel-hover': 'var(--cds-panel-shadow-hover, 0 4px 16px rgba(31,30,29,0.1))',
      },
      transitionTimingFunction: {
        'sa-out': 'cubic-bezier(0.22, 1, 0.36, 1)',
      },
      animation: {
        'quiet-dot': 'timeline-quiet-dot 1.9s cubic-bezier(0.4, 0, 0.2, 1) infinite',
        'message-fade-up': 'message-fade-up 0.45s cubic-bezier(0.34, 1.3, 0.64, 1)',
        'clay-breathe': 'dframe-clay-breathe 2.4s infinite ease-in-out',
        'dot-pulse': 'dframe-dot-pulse 1.2s infinite ease-in-out',
        'shimmer-sweep': 'cds-skeleton-sweep 2s linear infinite',
        'skeleton-sweep': 'cds-skeleton-sweep 2s linear infinite',
        'skeleton-breathe': 'cds-skeleton-breathe 2s ease-in-out infinite',
        'thumbnail-grow': 'file-thumbnail-grow-in 250ms cubic-bezier(0.165, 0.84, 0.44, 1)',
      },
    },
  },
  plugins: [],
}
