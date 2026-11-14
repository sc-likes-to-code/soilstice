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
import { DATA_MODE } from "@/services";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, match: (p: string) => p.startsWith("/dashboard") },
  { href: "/fields", label: "Fields", icon: MapIcon, match: (p: string) => p.startsWith("/fields") },
  { href: "/evidence", label: "Evidence", icon: BookOpen, match: (p: string) => p.startsWith("/evidence") },
  { href: "/settings", label: "Farm & Settings", icon: Settings, match: (p: string) => p.startsWith("/settings") },
];

function NavLinks({ active }: { active: (m: (p: string) => boolean) => boolean }) {
  return (
    <nav aria-label="Primary" className="flex items-center gap-1 overflow-x-auto overflow-y-hidden [scrollbar-width:none]">
      {NAV.map(({ href, label, icon: Icon, match }) => {
        const on = active(match);
        return (
          <Link
            key={href}
            href={href}
            aria-current={on ? "page" : undefined}
            className={cn(
              "inline-flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-[13px] font-semibold transition-colors",
              on ? "bg-forest-800 text-paper" : "text-ink-soft hover:bg-parchment/80 hover:text-ink",
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
      <Select label="Active farm" value={farm.farm_id} onChange={(id) => setActiveFarmId(id)} options={farms.map((f) => ({ value: f.farm_id, label: `${f.name} · ${f.aoi.label.replace(", Kansas", ", KS")}` }))} />
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="canvas-grain flex min-h-full flex-1 flex-col">
      <header className="no-print sticky top-0 z-30 border-b border-line bg-cream/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 md:px-8">
          <Brand href="/" />
          <div className="order-3 w-full md:order-none md:w-auto md:flex-1">
            <Suspense fallback={<NavLinks active={() => false} />}>
              <ActiveNav />
            </Suspense>
          </div>
          <div className="ml-auto md:ml-0">
            <FarmSwitcher />
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 pb-16 pt-8 md:px-8">{children}</main>
      <footer className="no-print border-t border-line/80 py-6 text-center text-[11.5px] text-stone-500">
        SOILSTICE · NASA Space Apps Challenge 2026 — Field Shift · {DATA_MODE === "mock" ? "Phase 1 interface with synthetic data" : "Live API data (USDA / NASA sources; see Evidence)"}
      </footer>
    </div>
  );
}
