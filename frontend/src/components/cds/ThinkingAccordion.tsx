/**
 * Claude Design System (CDS) - ThinkingAccordion.tsx
 * 
 * 逆向溯源：基于 REA v6.5.0 对 /Applications/Claude.app (@ant/desktop v2.37337.1) 取证：
 * - `cc1aae219-DtZTxCKj.css`: .timeline-quiet-dots / .timeline-expand / .timeline-status-*
 * - `shared-2-Cb74JByF.js`: 思考流状态互斥锁与时间轴动画
 * 
 * 核心真实生产规范：
 * 1. 3点静默跳跃指示波浪 (REA 取证自 cc1aae219-DtZTxCKj.css):
 *    - 间距 3.5px，尺寸 3px 圆点，背景 var(--cds-clay, #d97757)
 *    - 延迟：0s / 0.15s / 0.3s
 *    - 曲线：1.9s cubic-bezier(.4, 0, .2, 1) infinite timeline-quiet-dot
 * 2. 状态条升降物理：
 *    - 入场：.timeline-status-enter-quiet (.24s cubic-bezier(.3, .7, .4, 1) translateY(6px) -> 0)
 *    - 退场：.timeline-status-exit-quiet (.18s ease-out translateY(0) -> -4px)
 * 3. 伸缩平滑展开：
 *    - CSS Grid 0fr <-> 1fr 消除高度抖动 (.2s cubic-bezier(.19, 1, .22, 1) timeline-expand)
 * 4. 生成中强制展开互斥锁：
 *    - isThinkingLive 为 true 时强制锁定 open=true，剥夺折叠交互权，避免流式输出产生剧烈视口跳动
 */

import React, { useState } from 'react';

export interface ThinkingAccordionProps {
  thoughtText: string;
  isThinkingLive: boolean; // 模型是否正在流式输出思考
  elapsedMs?: number;
  onCopyQuote?: (text: string) => void;
  className?: string;
}

export const ThinkingAccordion: React.FC<ThinkingAccordionProps> = ({
  thoughtText,
  isThinkingLive,
  elapsedMs = 0,
  onCopyQuote,
  className = '',
}) => {
  const [userExpanded, setUserExpanded] = useState(false);
  const [didCopy, setDidCopy] = useState(false);

  // 核心互斥物理：生成中必定展开，不受用户历史偏好影响
  const isOpen = isThinkingLive || userExpanded;

  // 思考生成中剥夺折叠权限，完成后交还用户
  const handleToggle = () => {
    if (isThinkingLive) return;
    setUserExpanded((prev) => !prev);
  };

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(`> ${thoughtText.split('\n').join('\n> ')}`);
    setDidCopy(true);
    onCopyQuote?.(thoughtText);
    setTimeout(() => setDidCopy(false), 2000);
  };

  if (!thoughtText.trim() && !isThinkingLive) return null;

  const seconds = (elapsedMs / 1000).toFixed(1);

  return (
    <div
      data-cds="ThinkingAccordion"
      className={`group/thinking my-2 rounded-xl border border-[var(--cds-border,#e5e5e3)] dark:border-[var(--cds-border,#2e2e2c)] bg-[var(--cds-surface-1,#faf9f6)] dark:bg-[var(--cds-surface-1,#1a1a19)] transition-colors hover:border-[var(--cds-border-strong,#d1d1cf)] dark:hover:border-[var(--cds-border-strong,#40403e)] ${className}`}
    >
      {/* 头部标题与状态条 */}
      <div
        onClick={handleToggle}
        className={`flex items-center justify-between px-3.5 py-2 select-none ${
          isThinkingLive ? 'cursor-default' : 'cursor-pointer'
        }`}
      >
        <div className="flex items-center gap-2">
          {/* 状态指示：思考中为 3 点 1.9s 静默跳跃波浪，完成后为柔和陶土小圆点 */}
          {isThinkingLive ? (
            <div className="timeline-quiet-dots" aria-label="Thinking in progress">
              <span />
              <span />
              <span />
            </div>
          ) : (
            <span className="size-1.5 rounded-full bg-clay" />
          )}

          <span className="text-xs font-semibold text-[var(--cds-text-primary,#1a1a1a)] dark:text-[var(--cds-text-primary,#f0f0f0)]">
            {isThinkingLive ? (
              <span className="animate-pulse">Thinking…</span>
            ) : (
              <span>Thought for {seconds}s</span>
            )}
          </span>

          {!isThinkingLive && elapsedMs > 0 && (
            <span className="text-[11px] font-mono text-[var(--cds-text-secondary,#6b6b6b)] dark:text-[var(--cds-text-secondary,#9e9e9e)] tabular-nums opacity-75">
              ({elapsedMs}ms)
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* 复制为引用按钮 */}
          <button
            type="button"
            onClick={handleCopy}
            className="flex h-6 items-center gap-1 rounded px-1.5 text-[11px] font-medium text-[var(--cds-text-secondary,#6b6b6b)] dark:text-[var(--cds-text-secondary,#9e9e9e)] hover:bg-[var(--cds-surface-2,#f0eee9)] dark:hover:bg-[var(--cds-surface-2,#262625)] hover:text-[var(--cds-text-primary,#1a1a1a)] dark:hover:text-[var(--cds-text-primary,#f0f0f0)] transition-colors cursor-pointer"
          >
            {didCopy ? (
              <span className="text-emerald-500">✓ Copied</span>
            ) : (
              <span>Copy as quote</span>
            )}
          </button>

          {/* 折叠箭头指示器 */}
          {!isThinkingLive && (
            <span
              className={`text-xs text-[var(--cds-text-secondary,#6b6b6b)] dark:text-[var(--cds-text-secondary,#9e9e9e)] transition-transform duration-200 ${
                isOpen ? 'rotate-180' : ''
              }`}
            >
              ▾
            </span>
          )}
        </div>
      </div>

      {/* 思考正文折叠区域 (CSS Grid 0fr <-> 1fr 展开防抖) */}
      <div
        className="grid transition-[grid-template-rows] duration-200 ease-[cubic-bezier(.19,1,.22,1)]"
        style={{ gridTemplateRows: isOpen ? '1fr' : '0fr' }}
      >
        <div className="min-h-0 overflow-hidden border-t border-[var(--cds-border,#e5e5e3)] dark:border-[var(--cds-border,#2e2e2c)]">
          <div className="p-3.5 text-xs leading-relaxed text-[var(--cds-text-secondary,#6b6b6b)] dark:text-[var(--cds-text-secondary,#9e9e9e)] font-mono whitespace-pre-wrap break-words select-text">
            {thoughtText}
          </div>
        </div>
      </div>
    </div>
  );
};
