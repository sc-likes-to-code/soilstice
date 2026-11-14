"use client";
import Link from "next/link";
import { ArrowRight, CloudRain, Layers, Leaf, RefreshCw, Satellite, ShieldCheck } from "lucide-react";
import { useDatasets } from "@/hooks/queries";
import { resolutionText } from "@/lib/format";
import { SUPPORT_STYLE } from "@/lib/vocab";
import { cn } from "@/lib/cn";
import { Brand } from "@/components/layout/brand";
import { Skeleton } from "@/components/ui/primitives";

const STEPS = [
  { icon: Layers, title: "Select a field", body: "Field polygons from USDA Crop Sequence Boundaries — or draw your own inside the area of interest." },
  { icon: Satellite, title: "Read its environment", body: "NASA POWER climate, SMAP soil moisture, HLS 30 m vegetation and SRTM terrain, each labelled by spatial support." },
  { icon: RefreshCw, title: "Understand crop history", body: "Twenty seasons of Cropland Data Layer classes reveal the rotation the field has actually followed." },
  { icon: ShieldCheck, title: "Weigh explainable options", body: "Resilience components and limiting-factor crop options — every number traceable to its source and method." },
];

function HeroArt() {
  const parcels = [
    [0, 0, 2, 1, "#9c6b37"], [2, 0, 1, 1, "#d9a92e"], [3, 0, 1, 2, "#4f7d3a"], [0, 1, 1, 1, "#b8642f"], [1, 1, 2, 1, "#7c8a3c"],
    [0, 2, 1, 2, "#4f7d3a"], [1, 2, 1, 1, "#d9a92e"], [2, 2, 2, 1, "#9c6b37"], [1, 3, 1, 1, "#8a6f9e"], [2, 3, 1, 1, "#bdb29b"], [3, 3, 1, 1, "#b8642f"],
  ] as const;
  return (
    <svg viewBox="0 0 520 440" className="h-full w-full" aria-hidden>
      <defs>
        <linearGradient id="sky" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#284e36" stopOpacity=".0" /><stop offset="1" stopColor="#0e1d15" stopOpacity=".35" /></linearGradient>
        <pattern id="rows" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(90)"><line x1="0" y1="0" x2="0" y2="6" stroke="rgba(255,255,255,.14)" strokeWidth="2" /></pattern>
      </defs>
      <g transform="translate(260 250) scale(1 .56) rotate(45) translate(-170 -170)">
        {parcels.map(([x, y, w, h, c], i) => (
          <g key={i}>
            <rect x={x * 85 + 3} y={y * 85 + 3} width={w * 85 - 6} height={h * 85 - 6} rx="4" fill={c} opacity=".92" />
            <rect x={x * 85 + 3} y={y * 85 + 3} width={w * 85 - 6} height={h * 85 - 6} rx="4" fill="url(#rows)" />
          </g>
        ))}
        <circle cx="297" cy="297" r="36" fill="#4f7d3a" stroke="#e3ecdd" strokeOpacity=".35" />
        <line x1="297" y1="297" x2="331" y2="285" stroke="#e3ecdd" strokeWidth="2" strokeOpacity=".6" />
        <rect x="88" y="88" width="164" height="79" rx="5" fill="none" stroke="#f6ecd4" strokeWidth="3" strokeDasharray="7 5" />
      </g>
      <rect width="520" height="440" fill="url(#sky)" />
      <path d="M30 90 C 170 20, 350 20, 490 90" fill="none" stroke="#c99a3e" strokeWidth="1.4" strokeDasharray="2 6" opacity=".9" />
      <g transform="translate(372 46)">
        <rect x="-14" y="-5" width="28" height="10" rx="2" fill="#f6ecd4" />
        <rect x="-38" y="-3" width="20" height="6" fill="#a3c19f" /><rect x="18" y="-3" width="20" height="6" fill="#a3c19f" />
      </g>
      <path d="M372 54 L 300 205 L 395 205 Z" fill="#f6ecd4" opacity=".08" />
    </svg>
  );
}

export function LandingView() {
  const datasets = useDatasets();
  return (
    <div className="flex min-h-full flex-col bg-cream">
      <section className="relative overflow-hidden bg-forest-900 text-paper">
        <div className="pointer-events-none absolute inset-0 opacity-[0.07] [background-image:radial-gradient(#f6ecd4_1px,transparent_1px)] [background-size:18px_18px]" />
        <div className="relative mx-auto flex max-w-[1240px] items-center justify-between px-6 py-5 md:px-10">
          <Brand light />
          <nav className="flex items-center gap-1 text-[13px] font-semibold">
            <Link href="/evidence" className="rounded-lg px-3 py-2 text-forest-200 hover:text-paper max-sm:hidden">Data & evidence</Link>
            <Link href="/dashboard" className="rounded-lg bg-paper/10 px-3.5 py-2 text-paper ring-1 ring-paper/20 hover:bg-paper/15">Open the app</Link>
          </nav>
        </div>
        <div className="relative mx-auto grid max-w-[1240px] items-center gap-10 px-6 pb-20 pt-10 md:px-10 lg:grid-cols-[1.05fr_1fr] lg:pb-28 lg:pt-16">
          <div className="animate-[var(--animate-fade-up)]">
            <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-paper/15 bg-paper/5 px-3 py-1 text-[11.5px] font-semibold uppercase tracking-[0.16em] text-wheat-200">
              NASA Space Apps 2026 · Field Shift
            </p>
            <h1 className="font-display text-[44px] font-light leading-[1.02] text-paper md:text-[64px]">
              Know the field<br /><em className="font-normal text-wheat-200">before</em> the season.
            </h1>
            <p className="mt-6 max-w-xl text-[16px] leading-relaxed text-forest-100/85">
              SOILSTICE turns NASA Earth observation and USDA soil and crop records into a field-level picture of environment, crop history and resilience — and explains which rotations fit, and why.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link href="/dashboard" className="inline-flex h-12 items-center gap-2 rounded-xl bg-wheat-500 px-6 text-[14.5px] font-semibold text-forest-950 shadow-lg shadow-black/20 transition-transform hover:-translate-y-0.5 hover:bg-wheat-200">
                Open demo farm <ArrowRight className="h-4 w-4" />
              </Link>
              <Link href="/fields" className="inline-flex h-12 items-center gap-2 rounded-xl px-5 text-[14.5px] font-semibold text-paper ring-1 ring-paper/25 hover:bg-paper/10">
                Explore fields
              </Link>
            </div>
            <p className="mt-6 text-[12px] text-forest-200/80">Demonstration region: central Kansas (Reno & Finney counties). This interface currently runs on synthetic data.</p>
          </div>
          <div className="relative mx-auto aspect-[52/44] w-full max-w-[560px]">
            <HeroArt />
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-[1240px] px-6 py-20 md:px-10">
        <p className="text-[11.5px] font-semibold uppercase tracking-[0.16em] text-forest-600">How it works</p>
        <h2 className="mt-2 max-w-2xl font-display text-[34px] leading-tight text-ink">From pixels and soil surveys to a decision you can explain.</h2>
        <ol className="mt-10 grid gap-5 md:grid-cols-2 lg:grid-cols-4">
          {STEPS.map(({ icon: Icon, title, body }, i) => (
            <li key={title} className="group relative rounded-2xl border border-line bg-paper p-6 shadow-[var(--shadow-card)] transition-transform hover:-translate-y-1">
              <span className="font-mono text-[11px] font-semibold text-stone-400">0{i + 1}</span>
              <Icon className="mt-4 h-6 w-6 text-forest-600" aria-hidden />
              <h3 className="mt-4 font-display text-[19px] text-ink">{title}</h3>
              <p className="mt-2 text-[13.5px] leading-relaxed text-ink-soft">{body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="border-y border-line bg-parchment/50">
        <div className="mx-auto grid max-w-[1240px] gap-10 px-6 py-16 md:px-10 lg:grid-cols-[1fr_1.3fr]">
          <div>
            <p className="text-[11.5px] font-semibold uppercase tracking-[0.16em] text-forest-600">Scientific honesty</p>
            <h2 className="mt-2 font-display text-[30px] leading-tight text-ink">A 9 km pixel is not a field measurement.</h2>
            <p className="mt-4 text-[14px] leading-relaxed text-ink-soft">Every value in SOILSTICE carries its spatial support. Field-resolved data describes this field; regional context describes the landscape around it. We never resample a coarse grid to make it look precise, and missing data stays visibly missing.</p>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            {(["F", "S", "R"] as const).map((k) => {
              const s = SUPPORT_STYLE[k];
              const ex = k === "F" ? "HLS 30 m vegetation, SSURGO soils, CDL crops, SRTM terrain" : k === "S" ? "PRISM 4 km / 800 m precipitation & temperature" : "SMAP 9 km soil moisture, NASA POWER ~55 km climate";
              return (
                <div key={k} className={cn("rounded-2xl border p-5", s.bg, s.border)}>
                  <p className={cn("font-display text-[22px]", s.fg)}>{s.short}</p>
                  <p className="mt-1 text-[12.5px] font-semibold text-ink">{s.long}</p>
                  <p className="mt-3 text-[12.5px] leading-relaxed text-ink-soft">{ex}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-[1240px] px-6 py-16 md:px-10">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-[11.5px] font-semibold uppercase tracking-[0.16em] text-forest-600">Data foundation</p>
            <h2 className="mt-2 font-display text-[30px] leading-tight text-ink">Essential datasets</h2>
          </div>
          <Link href="/evidence" className="inline-flex items-center gap-1 text-[13px] font-semibold text-forest-700">Full evidence registry <ArrowRight className="h-4 w-4" /></Link>
        </div>
        <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {datasets.isPending
            ? Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-24" />)
            : datasets.isError
              ? null
              : datasets.data.data.filter((d) => d.priority === "P0").map((d) => (
                  <div key={d.dataset_id} className="rounded-xl border border-line bg-paper p-4">
                    <p className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.1em] text-stone-500">
                      {d.dataset_id.startsWith("nasa") ? <Satellite className="h-3.5 w-3.5 text-forest-600" /> : d.dataset_id.includes("cdl") || d.dataset_id.includes("csb") ? <Leaf className="h-3.5 w-3.5 text-wheat-600" /> : <CloudRain className="h-3.5 w-3.5 text-sky-500" />}
                      {d.publisher}
                    </p>
                    <p className="mt-2 text-[14px] font-semibold leading-snug text-ink">{d.title}</p>
                    <p className="mt-1 font-mono text-[11px] text-stone-500">{d.product} · {d.product_version} · {resolutionText(d.native_resolution_m)}</p>
                  </div>
                ))}
        </div>
      </section>

      <footer className="mt-auto border-t border-line py-8 text-center text-[12px] text-stone-500">
        SOILSTICE · NASA Space Apps Challenge 2026 — Field Shift · Phase 1 interface
      </footer>
    </div>
  );
}
