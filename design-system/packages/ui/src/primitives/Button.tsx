import { forwardRef, type ButtonHTMLAttributes } from 'react';
import { cn } from '../lib/cn';

export type ButtonVariant = 'primary' | 'ghost' | 'subtle' | 'whatsapp';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** Ocupa todo el ancho del contenedor. */
  block?: boolean;
}

const base =
  'inline-flex items-center justify-center gap-2 rounded-pill font-semibold ' +
  'transition-[transform,box-shadow,background,border-color] duration-[var(--dur)] ease-out ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 ' +
  'focus-visible:ring-offset-bg disabled:pointer-events-none disabled:opacity-50';

const variants: Record<ButtonVariant, string> = {
  primary:
    'bg-accent text-accent-contrast hover:-translate-y-0.5 ' +
    'hover:shadow-[0_12px_30px_rgba(var(--color-accent-rgb),0.4)]',
  ghost:
    'border border-border-strong text-ink hover:border-accent hover:text-accent',
  subtle: 'bg-surface text-ink border border-border hover:bg-bg-soft',
  whatsapp:
    'bg-[#25D366] text-white hover:-translate-y-0.5 ' +
    'hover:shadow-[0_12px_30px_rgba(37,211,102,0.4)]',
};

const sizes: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-6 py-3 text-md',
  lg: 'px-8 py-3.5 text-lg',
};

/**
 * Botón base del DS. Unifica `.btn` / `.btn-primario` / `.btn-ghost` / `.btn-wa`
 * de las tres fuentes previas en una sola API.
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', block, className, type = 'button', ...rest }, ref) => (
    <button
      ref={ref}
      type={type}
      className={cn(base, variants[variant], sizes[size], block && 'w-full', className)}
      {...rest}
    />
  ),
);

Button.displayName = 'Button';
