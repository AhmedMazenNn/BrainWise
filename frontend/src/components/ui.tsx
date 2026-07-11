import React from 'react'
import {
  AlertTriangleIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  LoaderCircleIcon,
  SearchIcon,
  XIcon,
} from 'lucide-react'
import { twMerge } from 'tailwind-merge'
export function Button({
  children,
  className,
  variant = 'primary',
  loading,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  loading?: boolean
}) {
  const variants = {
    primary: 'bg-[#175e58] text-white hover:bg-[#104b46]',
    secondary:
      'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
    danger: 'bg-red-600 text-white hover:bg-red-700',
    ghost: 'text-slate-600 hover:bg-slate-100',
  }
  return (
    <button
      {...props}
      disabled={loading || props.disabled}
      className={twMerge(
        'inline-flex h-10 items-center justify-center gap-2 rounded-lg px-3.5 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60',
        variants[variant],
        className,
      )}
    >
      {loading && <LoaderCircleIcon size={16} className="animate-spin" />}
      {children}
    </button>
  )
}
export function Card({
  children,
  className,
}: {
  children: React.ReactNode
  className?: string
}) {
  return (
    <section
      className={twMerge(
        'rounded-xl border border-slate-200 bg-white shadow-[0_1px_2px_rgba(16,24,40,0.03)]',
        className,
      )}
    >
      {children}
    </section>
  )
}
export function Badge({
  children,
  tone = 'slate',
}: {
  children: React.ReactNode
  tone?: 'slate' | 'green' | 'amber' | 'blue' | 'red' | 'purple'
}) {
  const tones = {
    slate: 'bg-slate-100 text-slate-600',
    green: 'bg-emerald-50 text-emerald-700',
    amber: 'bg-amber-50 text-amber-700',
    blue: 'bg-sky-50 text-sky-700',
    red: 'bg-red-50 text-red-700',
    purple: 'bg-violet-50 text-violet-700',
  }
  return (
    <span
      className={twMerge(
        'inline-flex items-center rounded-md px-2 py-1 text-xs font-semibold capitalize',
        tones[tone],
      )}
    >
      {children}
    </span>
  )
}
export function Field({
  label,
  error,
  children,
}: {
  label: string
  error?: string
  children: React.ReactNode
}) {
  return (
    <label className="block text-sm font-medium text-slate-700">
      <span className="mb-1.5 block">{label}</span>
      {children}
      {error && (
        <span className="mt-1 block text-xs font-medium text-red-600">
          {error}
        </span>
      )}
    </label>
  )
}
export const inputClass =
  'h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-800 shadow-sm placeholder:text-slate-400 focus:border-[#175e58] focus:outline-none'
export function Modal({
  title,
  children,
  onClose,
}: {
  title: string
  children: React.ReactNode
  onClose: () => void
}) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/30 p-4"
    >
      <div className="w-full max-w-lg rounded-xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 className="text-base font-bold text-slate-900">{title}</h2>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="rounded-md p-1 text-slate-400 hover:bg-slate-100"
          >
            <XIcon size={18} />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}
export function ConfirmDialog({
  title,
  description,
  confirmText = 'Confirm',
  onConfirm,
  onClose,
  loading,
}: {
  title: string
  description: string
  confirmText?: string
  onConfirm: () => void
  onClose: () => void
  loading?: boolean
}) {
  return (
    <Modal title={title} onClose={onClose}>
      <div className="p-5">
        <div className="flex gap-3">
          <div className="rounded-full bg-amber-50 p-2 text-amber-700">
            <AlertTriangleIcon size={19} />
          </div>
          <p className="pt-1 text-sm leading-6 text-slate-600">{description}</p>
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="danger" loading={loading} onClick={onConfirm}>
            {confirmText}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
export function SearchInput({
  value,
  onChange,
  placeholder = 'Search',
}: {
  value: string
  onChange: (value: string) => void
  placeholder?: string
}) {
  return (
    <div className="relative">
      <SearchIcon
        size={17}
        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
      />
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className={twMerge(inputClass, 'pl-9')}
      />
    </div>
  )
}
export function Pagination({
  page,
  total,
  perPage,
  onPageChange,
}: {
  page: number
  total: number
  perPage: number
  onPageChange: (page: number) => void
}) {
  const pages = Math.max(1, Math.ceil(total / perPage))
  return (
    <div className="flex items-center justify-between border-t border-slate-100 px-5 py-3">
      <span className="text-xs text-slate-500">
        Page {page} of {pages} · {total} results
      </span>
      <div className="flex gap-1">
        <Button
          aria-label="Previous page"
          variant="ghost"
          className="h-8 w-8 px-0"
          disabled={page === 1}
          onClick={() => onPageChange(page - 1)}
        >
          <ChevronLeftIcon size={16} />
        </Button>
        <Button
          aria-label="Next page"
          variant="ghost"
          className="h-8 w-8 px-0"
          disabled={page === pages}
          onClick={() => onPageChange(page + 1)}
        >
          <ChevronRightIcon size={16} />
        </Button>
      </div>
    </div>
  )
}
export function LoadingRows() {
  return (
    <div className="space-y-3 p-5" aria-label="Loading content">
      {[1, 2, 3, 4].map((item) => (
        <div
          className="h-10 animate-pulse rounded-md bg-slate-100"
          key={item}
        />
      ))}
    </div>
  )
}
export function EmptyState({
  title,
  description,
}: {
  title: string
  description: string
}) {
  return (
    <div className="px-5 py-14 text-center">
      <p className="font-semibold text-slate-700">{title}</p>
      <p className="mt-1 text-sm text-slate-500">{description}</p>
    </div>
  )
}
export function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="p-10 text-center">
      <p className="font-semibold text-slate-700">
        We couldn't load this data.
      </p>
      <Button variant="secondary" className="mt-4" onClick={onRetry}>
        Try again
      </Button>
    </div>
  )
}
