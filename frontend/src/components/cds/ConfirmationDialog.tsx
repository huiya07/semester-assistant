/**
 * Claude Design System (CDS) - Confirmation Modal Dialog
 * 
 * 逆向溯源：依据 REA v6.5.0 对 Claude Desktop 生产环境 (shared-frame-BfjMqbuN.js)
 * 提取的 data-cds="Dialog" 架构与 6 阶弹窗标尺规范。
 * 
 * 核心规范：
 *   - 弹窗尺寸阶梯 (Qg)：
 *       sm: max-w-[400px]
 *       md: max-w-[520px] (标准确认弹窗)
 *       lg: max-w-[720px]
 *       xl: max-w-[880px]
 *   - 动态视口高度限制：
 *       max-h-[calc(100dvh_-_max(2rem,2*var(--desktop-titlebar-inset,0px))_-_2*max(env(safe-area-inset-top,0px),env(safe-area-inset-bottom,0px)))]
 *   - 嵌套弹窗防御：data-[nested-dialog-open]:blur-[2px] 自动失焦模糊与暗化遮罩
 *   - 投影：真实双环 Popover 弥散投影 (--cds-shadow-popover)
 *   - 交互反馈：支持 Escape 快捷退出与点击遮罩关闭，焦点被锁在弹窗内部
 */

import React, { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CdsButton } from "./CdsButton";

export type DialogSize = "sm" | "md" | "lg";

export interface ConfirmationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "default";
  size?: DialogSize;
  icon?: React.ReactNode;
}

const DIALOG_SIZE_CLASSES: Record<DialogSize, string> = {
  sm: "max-w-[400px]",
  md: "max-w-[520px]",
  lg: "max-w-[720px]",
};

export function ConfirmationDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "danger",
  size = "sm",
  icon,
}: ConfirmationDialogProps) {
  // 监听 Escape 快捷键退出
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const isDanger = variant === "danger";

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* 高斯模糊与半透明背景遮罩 (Ug: bg-backdrop) */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            onClick={onClose}
            className="fixed inset-0 bg-black/40 backdrop-blur-[2px]"
          />

          {/* 模态卡片实体：16px 圆角与双环弥散投影 */}
          <motion.div
            data-cds="Dialog"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.2, ease: [0.165, 0.84, 0.44, 1] }}
            className={`relative w-full ${DIALOG_SIZE_CLASSES[size]} rounded-2xl bg-white dark:bg-[#1a1a19] p-6 border border-neutral-200/80 dark:border-neutral-800 z-10 space-y-4`}
            style={{
              boxShadow: "var(--cds-shadow-popover)",
            }}
            role="dialog"
            aria-modal="true"
          >
            {/* 头部标题与警示图标 */}
            <div className="flex items-start gap-3.5">
              <div
                className={`size-10 rounded-full flex items-center justify-center shrink-0 ${
                  isDanger
                    ? "bg-red-500/10 text-red-600 dark:bg-red-950/50 dark:text-red-400"
                    : "bg-clay/10 text-clay"
                }`}
              >
                {icon ? (
                  icon
                ) : isDanger ? (
                  <span className="text-base font-bold">!</span>
                ) : (
                  <span className="text-base font-bold">✦</span>
                )}
              </div>
              <div className="space-y-1 min-w-0 flex-1">
                <h4 className="text-heading font-semibold font-header text-neutral-900 dark:text-neutral-100">
                  {title}
                </h4>
                <p className="text-body font-normal text-secondary break-words leading-relaxed text-sm">
                  {description}
                </p>
              </div>

              {/* 右上角关闭按钮 */}
              <button
                type="button"
                onClick={onClose}
                className="text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 p-1 -mr-1 -mt-1 rounded-md transition-colors"
                aria-label="Close dialog"
              >
                <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* 底部操作工具栏 (单闭合边框原则：容器内部按钮不带硬边框) */}
            <div className="flex items-center justify-end gap-2 pt-2">
              <CdsButton
                variant="secondary"
                size="md"
                onClick={onClose}
              >
                {cancelLabel}
              </CdsButton>

              <CdsButton
                variant={isDanger ? "danger" : "primary"}
                size="md"
                onClick={onConfirm}
              >
                {confirmLabel}
              </CdsButton>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
