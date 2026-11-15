"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense, type ReactNode } from "react";
import { BookOpen, LayoutDashboard, Map as MapIcon, Settings } from "lucide-react";
import { cn } from "@/lib/cn";
import { useActiveFarm } from "@/hooks/active-farm";
import { usePrefs } from "@/hooks/preferences";
import { Select, Skeleton } from "@/components/ui/primitives";
import { Brand } from "./brand";
import { DataModeToggle } from "./data-mode-toggle";
import { useDataMode } from "@/hooks/data-mode";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, match: (p: string) => p.startsWith("/dashboard") },
  { href: "/fields", label: "Fields", icon: MapIcon, match: (p: string) => p.startsWith("/fields") },
  { href: "/evidence", label: "Evidence", icon: BookOpen, match: (p: string) => p.startsWith("/evidence") },
  { href: "/settings", label: "Farm & Settings", icon: Settings, match: (p: string) => p.startsWith("/settings") },
];

function NavLinks({ active }: { active: (m: (p: string) => boolean) => boolean }) {
  return (
    <nav aria-label="Primary" className="flex items-center gap-1 overflow-x-auto overflow-y-hidden py-1 [scrollbar-width:none]">
      {NAV.map(({ href, label, icon: Icon, match }) => {
        const on = active(match);
        return (
          <Link
            key={href}
            href={href}
            aria-current={on ? "page" : undefined}
            className={cn(
              "inline-flex shrink-0 items-center gap-2 rounded-lg px-3 py-1.5 text-[13px] font-semibold transition-all duration-150",
              on
                ? "bg-forest-800 text-paper shadow-sm"
                : "text-ink-soft hover:bg-parchment/80 hover:text-ink active:scale-[0.98]",
            )}
          >
            <Icon className="h-4 w-4" aria-hidden />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

function ActiveNav() {
  const pathname = usePathname();
  return <NavLinks active={(m) => m(pathname)} />;
}

function FarmSwitcher() {
  const { farm, farms, isLoading } = useActiveFarm();
  const { setActiveFarmId } = usePrefs();
  if (isLoading) return <Skeleton className="h-9 w-48" />;
  if (!farm) return null;
  return (
    <div className="flex items-center gap-2">
      <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-stone-500 max-lg:hidden">Farm</span>
      <Select
        label="Active farm"
        value={farm.farm_id}
        onChange={(id) => setActiveFarmId(id)}
        options={farms.map((f) => ({
          value: f.farm_id,
          label: `${f.name} · ${f.aoi.label.replace(", Kansas", ", KS")}`,
        }))}
      />
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const { isMock } = useDataMode();

  return (
    <div className="canvas-grain flex min-h-full flex-1 flex-col">
      <header className="no-print sticky top-0 z-30 border-b border-line/90 bg-cream/92 shadow-[0_1px_3px_rgba(0,0,0,0.03)] backdrop-blur-md">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-x-6 gap-y-2 px-4 py-2.5 md:px-8">
          <Brand href="/" />

          <div className="order-3 w-full md:order-none md:w-auto md:flex-1">
            <Suspense fallback={<NavLinks active={() => false} />}>
              <ActiveNav />
            </Suspense>
          </div>

          <div className="ml-auto flex items-center gap-3 md:ml-0">
            <DataModeToggle />
            <FarmSwitcher />
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 pb-16 pt-7 md:px-8">{children}</main>

      <footer className="no-print border-t border-line/80 bg-paper/40 py-6 text-center text-[12px] text-stone-500 backdrop-blur-sm">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-4 px-4 md:px-8">
          <p>
            <span className="font-display font-semibold text-forest-900">SOILSTICE</span> · NASA Space Apps Challenge 2026 — Field Shift
          </p>
          <p className="text-[11.5px] text-stone-500">
            {isMock
              ? "Phase 1 interface · Synthetic data demo"
              : "Live API operational · USDA NRCS SSURGO · USDA NASS CDL · NASA POWER"}
          </p>
        </div>
      </footer>
    </div>
  );
}
