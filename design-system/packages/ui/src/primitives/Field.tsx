import { forwardRef, useId, type InputHTMLAttributes, type SelectHTMLAttributes, type ReactNode } from 'react';
import { cn } from '../lib/cn';

const control =
  'w-full rounded-sm border border-border bg-surface px-3 py-2 text-base text-ink ' +
  'font-sans transition-colors duration-[var(--dur-fast)] placeholder:text-ink-mute ' +
  'focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30 ' +
  'disabled:opacity-50';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, ...rest }, ref) => (
    <input ref={ref} className={cn(control, className)} {...rest} />
  ),
);
Input.displayName = 'Input';

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, ...rest }, ref) => (
    <select ref={ref} className={cn(control, 'cursor-pointer', className)} {...rest} />
  ),
);
Select.displayName = 'Select';

export interface FieldProps {
  label: string;
  htmlFor?: string;
  hint?: ReactNode;
  error?: ReactNode;
  required?: boolean;
  children: ReactNode;
  className?: string;
}

/**
 * Envoltura etiqueta + control + ayuda/error. Unifica `.fld`, `.frm` y `.campo`.
 * Validación inline (no popup), acorde al criterio de AgroField para campo.
 */
export function Field({ label, htmlFor, hint, error, required, children, className }: FieldProps) {
  const autoId = useId();
  const id = htmlFor ?? autoId;
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <label htmlFor={id} className="text-sm font-semibold text-ink">
        {label}
        {required && <span className="ml-1 text-danger">*</span>}
      </label>
      {children}
      {error ? (
        <span className="text-xs text-danger">{error}</span>
      ) : hint ? (
        <span className="text-xs text-ink-mute">{hint}</span>
      ) : null}
    </div>
  );
}
