import Link from "next/link";
import { cn } from "@/lib/cn";

export function BrandMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={cn("h-7 w-7", className)} aria-hidden>
      <circle cx="16" cy="16" r="15" fill="#1d3a29" />
      <path d="M4 20.5c4-1.2 8-1.2 12 0s8 1.2 12 0" stroke="#c99a3e" strokeWidth="1.6" fill="none" strokeLinecap="round" />
      <path d="M5.5 24.5c3.5-1 7-1 10.5 0s7 1 10.5 0" stroke="#a3c19f" strokeWidth="1.4" fill="none" strokeLinecap="round" opacity=".8" />
      <path d="M16 19.5V10.5" stroke="#e3ecdd" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M16 14c-3.6.2-5.4-1.6-5.6-4.6 3.4-.2 5.3 1.4 5.6 4.6Z" fill="#a3c19f" />
      <path d="M16 12.4c.2-3.3 2.2-5 5.6-4.9-.1 3.1-2.1 4.9-5.6 4.9Z" fill="#e3ecdd" />
    </svg>
  );
}

export function Brand({ href = "/", light }: { href?: string; light?: boolean }) {
  return (
    <Link href={href} className="group inline-flex items-center gap-2.5">
      <BrandMark />
      <span className={cn("font-display text-[19px] font-semibold tracking-[0.04em]", light ? "text-paper" : "text-forest-900")}>
        SOILSTICE
      </span>
    </Link>
  );
}
