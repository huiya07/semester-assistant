/**
 * Claude Design System (CDS) - Status Indicators & Shimmer
 * 
 * 逆向溯源：依据 REA v6.5.0 对 Claude Desktop 生产环境 (shared-styles-Bl9zqrv-.css / cc1aae219-DtZTxCKj.css / c6a992d55-sXiDGMFQ.css)
 * AST 逆向提取的完整指示灯与骨架屏规范。
 * 
 * 核心动效：
 *   - 官方标准 6px 状态灯 (.status-dot)：
 *       [data-kind="ready"]: var(--cds-fill-accent)
 *       [data-kind="running"]: 1.2s ease-in-out infinite dframe-dot-blink
 *       [data-kind="error"]: var(--cds-fill-danger)
 *       [data-kind="clay"]: 3.0s ease-in-out infinite dframe-clay-breathe (scale 0.86->1, brightness 0.96->1.06)
 *   - 思考中三点波浪跳跃 (.timeline-quiet-dots)：
 *       3px 圆点，间距 3.5px，1.9s cubic-bezier(.4,0,.2,1) infinite，阶梯延迟 0s, 0.15s, 0.3s
 *   - 骨架屏高级倾斜扫光 (cds-skeleton-sweep)：
 *       2.0s 周期，105° 倾角线性渐变 (RTL 下为 255°)
 */

import React from "react";

export type StatusDotKind = "ready" | "running" | "error" | "clay";

// ============================================================================
// 1. 官方标准 6px 状态指示灯 (StatusDot)
// ============================================================================

export function StatusDot({
  kind = "ready",
  label,
  className = "",
}: {
  kind?: StatusDotKind;
  label?: string;
  className?: string;
}) {
  return (
    <div className={`inline-flex items-center gap-2 select-none ${className}`}>
      <span
        data-cds="StatusDot"
        data-kind={kind}
        className="status-dot shrink-0"
        aria-hidden="true"
      />
      {label && (
        <span className="text-xs font-medium text-neutral-700 dark:text-neutral-300">
          {label}
        </span>
      )}
    </div>
  );
}

// ============================================================================
// 2. 陶土呼吸指示灯 (ClayBreatheDot)
// ============================================================================

export function ClayBreatheDot({
  label,
  className = "",
}: {
  label?: string;
  className?: string;
}) {
  return (
    <StatusDot kind="clay" label={label} className={className} />
  );
}

// ============================================================================
// 3. 实时活动脉冲灯 (PulseRunningDot)
// ============================================================================

export function PulseRunningDot({
  label,
  className = "",
}: {
  label?: string;
  className?: string;
}) {
  return (
    <StatusDot kind="running" label={label} className={className} />
  );
}

// ============================================================================
// 4. 思考波浪三点跳跃 (QuietDotsWave - .timeline-quiet-dots)
// ============================================================================

export function QuietDotsWave({
  label = "Thinking...",
  className = "",
}: {
  label?: string;
  className?: string;
}) {
  return (
    <div className={`inline-flex items-center gap-2 select-none ${className}`}>
      <div
        className="timeline-quiet-dots inline-flex items-center"
        style={{ gap: "3.5px", position: "relative", top: "0.26em" }}
      >
        <span
          className="size-[3px] rounded-full bg-clay"
          style={{
            animation: "timeline-quiet-dot 1.9s infinite cubic-bezier(0.4, 0, 0.2, 1)",
            animationDelay: "0s",
          }}
        />
        <span
          className="size-[3px] rounded-full bg-clay"
          style={{
            animation: "timeline-quiet-dot 1.9s infinite cubic-bezier(0.4, 0, 0.2, 1)",
            animationDelay: "0.15s",
          }}
        />
        <span
          className="size-[3px] rounded-full bg-clay"
          style={{
            animation: "timeline-quiet-dot 1.9s infinite cubic-bezier(0.4, 0, 0.2, 1)",
            animationDelay: "0.3s",
          }}
        />
      </div>
      {label && (
        <span className="text-xs font-mono text-neutral-500 dark:text-neutral-400">
          {label}
        </span>
      )}
    </div>
  );
}

// ============================================================================
// 5. 骨架屏高级倾斜扫光条 (SkeletonSweep)
// ============================================================================

export function SkeletonSweep({
  className = "",
  rounded = "rounded-lg",
}: {
  className?: string;
  rounded?: string;
}) {
  return (
    <div
      className={`relative overflow-hidden bg-neutral-200/60 dark:bg-neutral-800 ${rounded} ${className}`}
    >
      <div
        className="cds-skel-sweep-band absolute inset-0 pointer-events-none"
        style={{
          background:
            "linear-gradient(105deg, transparent 35%, var(--cds-skeleton-sheen, rgba(255, 255, 255, 0.25)) 50%, transparent 65%)",
          animation: "cds-skeleton-sweep 2s linear infinite",
        }}
      />
    </div>
  );
}
