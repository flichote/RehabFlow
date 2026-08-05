"use client";

/**
 * ConfirmDialog — 通用二次确认弹窗
 * docs/design/components.md §6 通用组件
 * 用于取消课程 / 强制替换等场景
 */

import { type ReactNode } from "react";

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "确认",
  cancelLabel = "取消",
  danger = false,
  onConfirm,
  onCancel,
  children,
}: {
  open: boolean;
  title: string;
  message?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  children?: ReactNode;
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 背景遮罩 */}
      <div
        className="absolute inset-0 bg-neutral-900/40"
        onClick={onCancel}
      />
      {/* 弹窗主体 */}
      <div
        className="relative bg-white rounded-lg shadow-pop p-6 w-full max-w-sm mx-4"
        role="dialog"
        aria-modal="true"
      >
        <h3 className="text-base font-semibold text-neutral-900 mb-2">
          {title}
        </h3>
        {message && (
          <p className="text-sm text-neutral-500 mb-4">{message}</p>
        )}
        {children}
        <div className="flex justify-end gap-2 mt-6">
          <button
            onClick={onCancel}
            className="rounded-md px-4 py-2 text-sm font-medium text-neutral-500 hover:bg-neutral-100 transition-colors"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            className={
              danger
                ? "rounded-md px-4 py-2 text-sm font-medium text-white bg-danger-500 hover:bg-danger-500/90 transition-colors"
                : "rounded-md px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 transition-colors"
            }
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
