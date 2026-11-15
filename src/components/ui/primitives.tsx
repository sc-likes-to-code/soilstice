"use client";
import Link from "next/link";
import { useId, useState, type ButtonHTMLAttributes, type ReactNode } from "react";
import { cn } from "@/lib/cn";

export function Card({ children, className, as: As = "section", ...rest }: { children: ReactNode; className?: string; as?: "section" | "div" | "article" } & React.HTMLAttributes<HTMLElement>) {
  return (
    <As className={cn("print-plain print-avoid min-w-0 rounded-[var(--radius-card)] border border-line bg-paper shadow-[var(--shadow-card)]", className)} {...rest}>
      {children}
    </As>
  );
}

export function CardHeader({ title, eyebrow, description, actions, className }: { title: ReactNode; eyebrow?: ReactNode; description?: ReactNode; actions?: ReactNode; className?: string }) {
  return (
    <header className={cn("flex flex-col sm:flex-row sm:items-start justify-between gap-3 px-5 pt-5", className)}>
      <div className="min-w-0 flex-1">
        {eyebrow && <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-stone-500">{eyebrow}</p>}
        <h3 className="font-display text-[17px] font-medium leading-snug text-ink">{title}</h3>
        {description && <p className="mt-1 max-w-prose text-[13px] leading-relaxed text-ink-soft">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center sm:justify-end gap-1.5 max-w-full">{actions}</div>}
    </header>
  );
}

export function CardBody({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("px-5 pb-5 pt-4", className)}>{children}</div>;
}

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
const BUTTON: Record<ButtonVariant, string> = {
  primary: "bg-forest-800 text-paper hover:bg-forest-700 shadow-sm",
  secondary: "border border-line-strong bg-paper text-ink hover:bg-parchment/60",
  ghost: "text-ink-soft hover:bg-parchment/70 hover:text-ink",
  danger: "border border-clay-100 bg-clay-100/60 text-clay-600 hover:bg-clay-100",
};

export function Button({ variant = "secondary", size = "md", className, children, ...rest }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; size?: "sm" | "md" }) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-1.5 rounded-lg font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        size === "sm" ? "h-8 px-3 text-[12.5px]" : "h-10 px-4 text-[13.5px]",
        BUTTON[variant],
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
}

export function ButtonLink({ href, variant = "secondary", size = "md", className, children }: { href: string; variant?: ButtonVariant; size?: "sm" | "md"; className?: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className={cn(
        "inline-flex items-center justify-center gap-1.5 rounded-lg font-semibold transition-colors",
        size === "sm" ? "h-8 px-3 text-[12.5px]" : "h-10 px-4 text-[13.5px]",
        BUTTON[variant],
        className,
      )}
    >
      {children}
    </Link>
  );
}

export function Badge({ children, className, title }: { children: ReactNode; className?: string; title?: string }) {
  return (
    <span title={title} className={cn("inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-semibold leading-4", className)}>
      {children}
    </span>
  );
}

export function Dot({ className }: { className?: string }) {
  return <span aria-hidden className={cn("inline-block h-2 w-2 shrink-0 rounded-full", className)} />;
}

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn("skeleton", className)} />;
}

/**
 * Accessible hover/focus popover with rich content. Rendered only while open, fixed-positioned and clamped
 * to the viewport so it never causes horizontal overflow or clips at screen edges.
 */
export function Tip({ content, children, className, side = "top" }: { content: ReactNode; children: ReactNode; className?: string; side?: "top" | "bottom" }) {
  const [pos, setPos] = useState<{ x: number; y: number; below: boolean } | null>(null);
  const id = useId();
  const show = (el: HTMLElement) => {
    const r = el.getBoundingClientRect();
    const vw = window.innerWidth;
    const below = side === "bottom" || r.top < 120;
    setPos({ x: Math.min(Math.max(r.left + r.width / 2, 150), vw - 150), y: below ? r.bottom + 8 : r.top - 8, below });
  };
  return (
    <span
      className={cn("relative", className || "inline-flex")}
      onMouseEnter={(e) => show(e.currentTarget)}
      onMouseLeave={() => setPos(null)}
    >
      <span tabIndex={0} aria-describedby={pos ? id : undefined} onFocus={(e) => show(e.currentTarget)} onBlur={() => setPos(null)} className="inline-flex h-full w-full cursor-help">
        {children}
      </span>
      {pos && (
        <span
          role="tooltip"
          id={id}
          style={{ left: pos.x, top: pos.y, transform: `translate(-50%, ${pos.below ? "0" : "-100%"})` }}
          className="pointer-events-none fixed z-[60] w-max max-w-[280px] rounded-lg border border-forest-900/10 bg-forest-950 px-3 py-2 text-left text-[12px] font-normal normal-case leading-relaxed tracking-normal text-forest-50 shadow-[var(--shadow-lift)] animate-[var(--animate-fade-up)]"
        >
          {content}
        </span>
      )}
    </span>
  );
}

export function Segmented<T extends string>({ value, onChange, options, size = "md", label }: { value: T; onChange: (v: T) => void; options: { value: T; label: ReactNode }[]; size?: "sm" | "md"; label: string }) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex rounded-lg border border-line bg-parchment/50 p-0.5">
      {options.map((o) => (
        <button
          key={o.value}
          role="radio"
          aria-checked={o.value === value}
          onClick={() => onChange(o.value)}
          className={cn(
            "rounded-md font-semibold transition-all",
            size === "sm" ? "px-2.5 py-1 text-[12px]" : "px-3 py-1.5 text-[13px]",
            o.value === value ? "bg-paper text-forest-800 shadow-sm" : "text-ink-soft hover:text-ink",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Select<T extends string | number>({ value, onChange, options, label, className }: { value: T; onChange: (v: T) => void; options: { value: T; label: string }[]; label: string; className?: string }) {
  return (
    <label className={cn("relative inline-flex items-center", className)}>
      <span className="sr-only">{label}</span>
      <select
        value={String(value)}
        onChange={(e) => {
          const raw = e.target.value;
          const opt = options.find((o) => String(o.value) === raw);
          if (opt) onChange(opt.value);
        }}
        className="h-9 appearance-none rounded-lg border border-line-strong bg-paper pl-3 pr-8 text-[13px] font-semibold text-ink hover:bg-parchment/40"
      >
        {options.map((o) => (
          <option key={String(o.value)} value={String(o.value)}>
            {o.label}
          </option>
        ))}
      </select>
      <svg aria-hidden viewBox="0 0 12 12" className="pointer-events-none absolute right-3 h-3 w-3 text-stone-500"><path d="M2 4l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.6" /></svg>
    </label>
  );
}

export function Stat({ label, value, sub, className }: { label: ReactNode; value: ReactNode; sub?: ReactNode; className?: string }) {
  return (
    <div className={cn("min-w-0", className)}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-stone-500">{label}</p>
      <div className="mt-1 font-display text-[26px] font-medium leading-none text-ink tabular">{value}</div>
      {sub && <div className="mt-1.5 text-[12px] text-ink-soft">{sub}</div>}
    </div>
  );
}

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow?: ReactNode; title: ReactNode; description?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4 animate-[var(--animate-fade-up)]">
      <div className="min-w-0">
        {eyebrow && <p className="mb-2 text-[11.5px] font-semibold uppercase tracking-[0.16em] text-forest-600">{eyebrow}</p>}
        <h1 className="font-display text-[32px] font-normal leading-[1.1] text-ink md:text-[38px]">{title}</h1>
        {description && <p className="mt-2 max-w-2xl text-[14.5px] leading-relaxed text-ink-soft">{description}</p>}
      </div>
      {actions && <div className="no-print flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
