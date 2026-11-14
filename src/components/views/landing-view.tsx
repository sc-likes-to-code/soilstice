"use client";
import Image from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  CheckCircle2,
  Clock,
  CloudRain,
  Compass,
  Database,
  Layers,
  RefreshCw,
  Satellite,
  ShieldCheck,
} from "lucide-react";
import { SUPPORT_STYLE } from "@/lib/vocab";
import { cn } from "@/lib/cn";
import { Brand } from "@/components/layout/brand";
import { CustomScroller } from "@/components/shared/custom-scroller";

const PIPELINE_STEPS = [
  {
    step: "01",
    icon: Layers,
    title: "Field Boundary",
    body: "Delineate exact field boundaries from USDA Crop Sequence Boundaries or draw custom parcels within the county area of interest.",
  },
  {
    step: "02",
    icon: Satellite,
    title: "Environmental Intelligence",
    body: "Extract NASA POWER solar and temperature dynamics, SMAP soil moisture regimes, HLS vegetation vigor, and SSURGO soil characteristics.",
  },
  {
    step: "03",
    icon: RefreshCw,
    title: "20-Year Crop History",
    body: "Mine continuous USDA Cropland Data Layer records from 2006 to 2025 to classify historical crop sequences and rotation frequency.",
  },
  {
    step: "04",
    icon: ShieldCheck,
    title: "Explainable Decisions",
    body: "Evaluate next-season crops against the most limiting agronomic factor, ensuring transparent and defensible rotation recommendations.",
  },
];

const DATASET_MATRIX = [
  {
    name: "NASA POWER Daily Agrometeorology",
    agency: "NASA Langley",
    resolution: "~55 km regional grid",
    coverage: "1981 – present",
    status: "live",
    statusLabel: "Integrated & Verified",
    role: "Precipitation, temperature extremes, reference ET₀, cumulative GDD",
  },
  {
    name: "USDA NRCS SSURGO",
    agency: "USDA NRCS",
    resolution: "Detailed vector survey (1:12k–1:24k)",
    coverage: "Standard survey",
    status: "live",
    statusLabel: "Integrated & Verified",
    role: "Available water storage 0–150 cm, texture, pH, organic matter, drainage class",
  },
  {
    name: "USDA NASS Cropland Data Layer (CDL)",
    agency: "USDA NASS",
    resolution: "30 m (56 m prior to 2010)",
    coverage: "2006 – 2025 (20 seasons)",
    status: "live",
    statusLabel: "Integrated & Verified",
    role: "Annual crop classification, sequence diversity, rotation purity",
  },
  {
    name: "NASA SRTM GL1",
    agency: "NASA JPL",
    resolution: "30 m elevation & slope",
    coverage: "Global static (Feb 2000)",
    status: "verified",
    statusLabel: "Pipeline Verified",
    role: "Field elevation profile, mean slope, 90th percentile slope risk",
  },
  {
    name: "NASA SMAP L4 Soil Moisture",
    agency: "NASA / NSIDC",
    resolution: "9 km assimilated grid",
    coverage: "2015 – present",
    status: "staged",
    statusLabel: "Phase 3 Ingestion",
    role: "Surface and root-zone volumetric soil moisture anomalies",
  },
  {
    name: "NASA Harmonized Landsat Sentinel-2 (HLS)",
    agency: "NASA LP DAAC",
    resolution: "30 m surface reflectance",
    coverage: "2013 – present",
    status: "staged",
    statusLabel: "Phase 3 Ingestion",
    role: "Time-series NDVI, EVI2, green-up and peak biomass phenology",
  },
];

export function LandingView() {
  return (
    <div className="flex min-h-full flex-col bg-cream text-ink">
      <CustomScroller />
      {/* ───────────────────────── 1. EDITORIAL HERO (FULL VIEWPORT) ───────────────────────── */}
      <section id="hero" className="relative flex min-h-[100dvh] flex-col justify-between overflow-hidden bg-forest-950 text-paper">
        {/* Background authentic farmer photography */}
        <div className="absolute inset-0">
          <Image
            src="/images/hero/kansas-wheat-hero.jpg"
            alt="Expansive golden wheat field in Kansas, American Great Plains"
            fill
            priority
            sizes="100vw"
            className="object-cover object-center opacity-75 brightness-95 contrast-105"
          />
          {/* Subtle controlled gradient so the photo is clearly visible while text stays 100% legible */}
          <div className="absolute inset-0 bg-gradient-to-r from-forest-950/85 via-forest-950/55 to-forest-950/20" />
          <div className="absolute inset-0 bg-gradient-to-t from-forest-950/85 via-transparent to-forest-950/40" />
        </div>

        {/* Hero Top Bar */}
        <div className="relative z-10 mx-auto flex w-full max-w-[1340px] shrink-0 items-center justify-between px-6 py-6 md:px-10">
          <Brand light />
          <nav className="flex items-center gap-2 text-[13px] font-semibold">
            <Link
              href="/evidence"
              className="rounded-lg px-3 py-2 text-forest-200 transition-colors hover:bg-white/10 hover:text-paper max-sm:hidden"
            >
              Data &amp; Evidence
            </Link>
            <Link
              href="/dashboard"
              className="rounded-xl bg-wheat-500 px-4 py-2 font-semibold text-forest-950 shadow-md transition-all hover:bg-wheat-200 hover:shadow-lg"
            >
              Launch Platform
            </Link>
          </nav>
        </div>

        {/* Hero Main Content (Centered Vertically) */}
        <div className="relative z-10 mx-auto my-auto w-full max-w-[1340px] px-6 py-12 md:px-10">
          <div className="max-w-3xl space-y-7">
            <div className="inline-flex items-center rounded-full border border-wheat-200/25 bg-wheat-500/10 px-3.5 py-1.5 text-[12px] font-semibold uppercase tracking-[0.16em] text-wheat-200 backdrop-blur-md">
              <span>NASA Space Apps Challenge 2026 · Field Shift</span>
            </div>

            <h1 className="font-display text-[48px] font-light leading-[1.02] text-paper drop-shadow-[0_2px_12px_rgba(0,0,0,0.6)] sm:text-[64px] lg:text-[76px]">
              Know the field <br />
              <em className="font-normal italic text-wheat-300">before</em> the season.
            </h1>

            <p className="max-w-2xl text-[18px] leading-relaxed text-forest-50 drop-shadow-[0_1px_4px_rgba(0,0,0,0.5)] md:text-[20px]">
              SOILSTICE combines soil survey information, satellite observations and regional climate records into a traceable field intelligence profile, twenty seasons of crop history, and explainable rotation intelligence.
            </p>

            <div className="flex flex-wrap items-center gap-3 pt-2">
              <Link
                href="/dashboard"
                className="inline-flex h-13 items-center gap-2.5 rounded-xl bg-wheat-500 px-7 text-[15px] font-semibold text-forest-950 shadow-xl shadow-black/30 transition-transform hover:-translate-y-0.5 hover:bg-wheat-200 active:translate-y-0"
              >
                <span>Explore Demo Farm</span>
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/fields"
                className="inline-flex h-13 items-center gap-2 rounded-xl border border-paper/25 bg-paper/10 px-6 text-[15px] font-semibold text-paper backdrop-blur transition-all hover:bg-paper/20"
              >
                <Compass className="h-4 w-4" />
                <span>Field Explorer</span>
              </Link>
            </div>

            {/* Live operational badge */}
            <div className="flex flex-wrap items-center gap-3 pt-3 text-[12px] text-forest-200/90">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-950/60 px-3 py-1 font-medium text-emerald-300">
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                Live Providers Operational
              </span>
              <span>Central Kansas test region (Reno &amp; Finney Counties) · USDA SSURGO &amp; CDL, NASA POWER</span>
            </div>
          </div>
        </div>
      </section>

      {/* ───────────────────────── 2. THE PROBLEM (FULL VIEWPORT) ───────────────────────── */}
      <section id="the-problem" className="relative flex min-h-[100dvh] flex-col justify-center border-b border-line bg-paper py-20 md:py-28">
        <div className="mx-auto w-full max-w-[1240px] px-6 md:px-10">
          <div className="max-w-2xl">
            <p className="text-[12px] font-semibold uppercase tracking-[0.16em] text-forest-700">The Problem</p>
            <h2 className="mt-2 font-display text-[34px] leading-tight text-ink md:text-[44px]">
              Fragmented agricultural data leaves farmers blind to shifting climate baselines.
            </h2>
            <p className="mt-4 text-[16px] leading-relaxed text-ink-soft">
              Every season, growers across the Great Plains and Midwest make rotational decisions worth hundreds of
              thousands of dollars. Yet critical environmental variables remain locked in disparate scientific archives:
            </p>
          </div>

          <div className="mt-12 grid gap-6 md:grid-cols-3">
            <div className="rounded-2xl border border-line bg-cream/50 p-6 shadow-sm">
              <div className="grid h-10 w-10 place-items-center rounded-xl bg-clay-100 text-clay-600">
                <CloudRain className="h-5 w-5" />
              </div>
              <h3 className="mt-4 font-display text-[19px] text-ink">Precipitation Volatility</h3>
              <p className="mt-2 text-[13.5px] leading-relaxed text-ink-soft">
                Multi-year drought spikes and flash droughts alter subsoil recharge rates, making single-year weather memory
                deceptive when planning high-water-demand rotations.
              </p>
            </div>

            <div className="rounded-2xl border border-line bg-cream/50 p-6 shadow-sm">
              <div className="grid h-10 w-10 place-items-center rounded-xl bg-forest-100 text-forest-700">
                <RefreshCw className="h-5 w-5" />
              </div>
              <h3 className="mt-4 font-display text-[19px] text-ink">Monoculture Vulnerability</h3>
              <p className="mt-2 text-[13.5px] leading-relaxed text-ink-soft">
                Continuous wheat or corn sequences deplete specific micronutrients, encourage stubborn weed seedbanks, and
                degrade soil organic matter over successive seasons.
              </p>
            </div>

            <div className="rounded-2xl border border-line bg-cream/50 p-6 shadow-sm">
              <div className="grid h-10 w-10 place-items-center rounded-xl bg-sky-100 text-sky-700">
                <Database className="h-5 w-5" />
              </div>
              <h3 className="mt-4 font-display text-[19px] text-ink">Siloed Earth Observations</h3>
              <p className="mt-2 text-[13.5px] leading-relaxed text-ink-soft">
                NASA satellite constellations and USDA soil surveys exist in complex scientific APIs, inaccessible to farmers
                without an agronomic translation engine.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ───────────────────────── 3. HOW IT WORKS (FULL VIEWPORT) ───────────────────────── */}
      <section id="how-it-works" className="relative flex min-h-[100dvh] flex-col justify-center py-20 md:py-28">
        <div className="mx-auto w-full max-w-[1240px] px-6 md:px-10">
          <div className="text-center">
            <p className="text-[12px] font-semibold uppercase tracking-[0.16em] text-forest-700">The SOILSTICE Solution</p>
            <h2 className="mt-2 font-display text-[34px] leading-tight text-ink md:text-[44px]">
              From satellite pixels to an explainable rotation decision.
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-[16px] text-ink-soft">
              A scientifically traceable 4-step pipeline that preserves provenance, respects spatial support, and explains every recommendation.
            </p>
          </div>

          <div className="mt-14 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            {PIPELINE_STEPS.map(({ step, icon: Icon, title, body }) => (
              <div
                key={title}
                className="group relative flex flex-col justify-between rounded-2xl border border-line bg-paper p-6 shadow-[var(--shadow-card)] transition-all duration-200 hover:-translate-y-1 hover:border-forest-300 hover:shadow-lg"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[13px] font-bold text-forest-600">{step}</span>
                    <div className="grid h-9 w-9 place-items-center rounded-lg bg-forest-50 text-forest-700 transition-colors group-hover:bg-forest-800 group-hover:text-paper">
                      <Icon className="h-4.5 w-4.5" />
                    </div>
                  </div>
                  <h3 className="mt-5 font-display text-[20px] text-ink">{title}</h3>
                  <p className="mt-2.5 text-[13.5px] leading-relaxed text-ink-soft">{body}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ───────────────────────── 4. AGRICULTURAL PHOTO & FEATURE SHOWCASE (FULL VIEWPORT) ───────────────────────── */}
      <section id="capabilities" className="relative flex min-h-[100dvh] flex-col justify-center border-y border-line bg-parchment/40 py-20 md:py-28">
        <div className="mx-auto w-full max-w-[1240px] px-6 md:px-10">
          <div className="mb-12 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-[12px] font-semibold uppercase tracking-[0.16em] text-forest-700">Agronomic Capabilities</p>
              <h2 className="mt-2 font-display text-[32px] leading-tight text-ink md:text-[38px]">
                Ground truth meets orbital monitoring.
              </h2>
            </div>
            <Link
              href="/fields"
              className="inline-flex items-center gap-1.5 text-[14px] font-semibold text-forest-800 transition-colors hover:text-forest-950"
            >
              <span>Explore all field capabilities</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            {/* Card 1: Soil */}
            <div className="overflow-hidden rounded-2xl border border-line bg-paper shadow-sm">
              <div className="relative aspect-[16/10] w-full">
                <Image
                  src="/images/soil/soil-sampling.jpg"
                  alt="Soil sampling and loam texture inspection"
                  fill
                  sizes="(max-width: 768px) 100vw, (max-width: 1200px) 33vw, 380px"
                  className="object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                <span className="absolute bottom-3 left-3 rounded-md bg-paper/90 px-2.5 py-1 text-[11px] font-semibold text-ink backdrop-blur">
                  SSURGO 150 cm Root Zone
                </span>
              </div>
              <div className="p-6">
                <h3 className="font-display text-[20px] text-ink">Soil Horizons &amp; Hydrology</h3>
                <p className="mt-2 text-[13.5px] leading-relaxed text-ink-soft">
                  Inspect available water storage (AWS), organic matter percentage, drainage classifications, and pH ranges
                  across map-unit components.
                </p>
              </div>
            </div>

            {/* Card 2: Crops & Rotation */}
            <div className="overflow-hidden rounded-2xl border border-line bg-paper shadow-sm">
              <div className="relative aspect-[16/10] w-full">
                <Image
                  src="/images/crops/wheat.jpg"
                  alt="Winter wheat harvest canopy"
                  fill
                  sizes="(max-width: 768px) 100vw, (max-width: 1200px) 33vw, 380px"
                  className="object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                <span className="absolute bottom-3 left-3 rounded-md bg-paper/90 px-2.5 py-1 text-[11px] font-semibold text-ink backdrop-blur">
                  USDA CDL 20-Season Matrix
                </span>
              </div>
              <div className="p-6">
                <h3 className="font-display text-[20px] text-ink">20-Year Rotation Lab</h3>
                <p className="mt-2 text-[13.5px] leading-relaxed text-ink-soft">
                  Evaluate suitability for Winter Wheat, Corn, Soybeans, Alfalfa, and Grain Sorghum based on consecutive years
                  and limiting physical factors.
                </p>
              </div>
            </div>

            {/* Card 3: Irrigation & Climate */}
            <div className="overflow-hidden rounded-2xl border border-line bg-paper shadow-sm">
              <div className="relative aspect-[16/10] w-full">
                <Image
                  src="/images/features/irrigation.jpg"
                  alt="Center pivot irrigation field geometry"
                  fill
                  sizes="(max-width: 768px) 100vw, (max-width: 1200px) 33vw, 380px"
                  className="object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                <span className="absolute bottom-3 left-3 rounded-md bg-paper/90 px-2.5 py-1 text-[11px] font-semibold text-ink backdrop-blur">
                  NASA POWER Agrometeorology
                </span>
              </div>
              <div className="p-6">
                <h3 className="font-display text-[20px] text-ink">Water Balance &amp; Climate Stress</h3>
                <p className="mt-2 text-[13.5px] leading-relaxed text-ink-soft">
                  Track cumulative GDD heat units, monthly precipitation deficits against 30-year normals, and reference ET₀
                  evaporative demand.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ───────────────────────── 5. SCIENTIFIC TRANSPARENCY (FULL VIEWPORT) ───────────────────────── */}
      <section id="transparency" className="relative flex min-h-[100dvh] flex-col justify-center py-20 md:py-28">
        <div className="mx-auto w-full max-w-[1240px] px-6 md:px-10">
          <div className="grid gap-12 lg:grid-cols-[1fr_1.3fr]">
            <div>
              <div className="inline-flex items-center gap-1.5 rounded-md bg-forest-100 px-2.5 py-1 text-[11.5px] font-semibold uppercase tracking-wider text-forest-800">
                <ShieldCheck className="h-3.5 w-3.5" />
                <span>Scientific Honesty</span>
              </div>
              <h2 className="mt-3 font-display text-[32px] leading-tight text-ink md:text-[38px]">
                A 9 km pixel is not a field measurement.
              </h2>
              <p className="mt-4 text-[15px] leading-relaxed text-ink-soft">
                Most platforms interpolate coarse regional grids down to field boundaries, pretending to offer centimeter-level
                accuracy. SOILSTICE firmly rejects this practice.
              </p>
              <p className="mt-3 text-[15px] leading-relaxed text-ink-soft">
                Every data point is explicitly tagged with its spatial support class, native resolution, and provenance.
                Field-resolved data represents the field; regional context describes the macroclimate around it. Missing data
                remains visibly missing.
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              {(["F", "S", "R"] as const).map((k) => {
                const s = SUPPORT_STYLE[k];
                const desc =
                  k === "F"
                    ? "Direct field boundary measurements. Vector soil polygons, 30 m satellite classifications, and terrain."
                    : k === "S"
                      ? "Sub-regional local grid. 4 km to 800 m gridded climate models (PRISM) covering multiple parcels."
                      : "Macro-regional context. ~55 km weather grids and 9 km satellite footprints describing the broad county climate.";
                const examples =
                  k === "F"
                    ? "USDA SSURGO, USDA CDL, NASA HLS, NASA SRTM"
                    : k === "S"
                      ? "PRISM Climate Grids (4 km)"
                      : "NASA POWER (~55 km), SMAP (9 km)";
                return (
                  <div key={k} className={cn("flex flex-col justify-between rounded-2xl border p-5 shadow-sm", s.bg, s.border)}>
                    <div>
                      <span className={cn("font-display text-[26px] font-bold", s.fg)}>{s.short}</span>
                      <p className="mt-1 text-[13px] font-semibold text-ink">{s.long}</p>
                      <p className="mt-3 text-[12.5px] leading-relaxed text-ink-soft">{desc}</p>
                    </div>
                    <p className="mt-4 border-t border-line/60 pt-3 font-mono text-[11px] text-stone-500">{examples}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* ───────────────────────── 6. LIVE DATASET REGISTRY MATRIX (FULL VIEWPORT) ───────────────────────── */}
      <section id="datasets" className="relative flex min-h-[100dvh] flex-col justify-center border-t border-line bg-paper py-20 md:py-28">
        <div className="mx-auto w-full max-w-[1240px] px-6 md:px-10">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-[12px] font-semibold uppercase tracking-[0.16em] text-forest-700">Earth Observation Sources</p>
              <h2 className="mt-2 font-display text-[32px] leading-tight text-ink md:text-[38px]">
                Essential Datasets &amp; Status
              </h2>
            </div>
            <Link
              href="/evidence"
              className="inline-flex items-center gap-1.5 text-[14px] font-semibold text-forest-800 hover:text-forest-950"
            >
              <span>View full evidence registry</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="mt-10 overflow-hidden rounded-2xl border border-line bg-paper shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-[13px]">
                <thead className="border-b border-line bg-cream/70 text-[11px] font-semibold uppercase tracking-wider text-stone-500">
                  <tr>
                    <th className="py-3 pl-6 pr-4">Dataset</th>
                    <th className="py-3 px-4">Provider / Resolution</th>
                    <th className="py-3 px-4">Agronomic Application</th>
                    <th className="py-3 pl-4 pr-6 text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line/70">
                  {DATASET_MATRIX.map((d) => (
                    <tr key={d.name} className="hover:bg-cream/30">
                      <td className="py-4 pl-6 pr-4">
                        <p className="font-semibold text-ink">{d.name}</p>
                        <p className="text-[11.5px] text-stone-500">{d.coverage}</p>
                      </td>
                      <td className="py-4 px-4">
                        <p className="text-ink">{d.agency}</p>
                        <p className="font-mono text-[11.5px] text-stone-500">{d.resolution}</p>
                      </td>
                      <td className="py-4 px-4 text-ink-soft">{d.role}</td>
                      <td className="py-4 pl-4 pr-6 text-right">
                        {d.status === "live" ? (
                          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-300 bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-800">
                            <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                            {d.statusLabel}
                          </span>
                        ) : d.status === "verified" ? (
                          <span className="inline-flex items-center gap-1.5 rounded-full border border-sky-300 bg-sky-50 px-2.5 py-1 text-[11px] font-semibold text-sky-800">
                            <CheckCircle2 className="h-3 w-3 text-sky-600" />
                            {d.statusLabel}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 rounded-full border border-line bg-parchment/60 px-2.5 py-1 text-[11px] font-semibold text-stone-600">
                            <Clock className="h-3 w-3 text-stone-400" />
                            {d.statusLabel}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      {/* ───────────────────────── 7. CLOSING CALL TO ACTION & FOOTER (FULL VIEWPORT) ───────────────────────── */}
      <section id="action" className="relative flex min-h-[100dvh] flex-col justify-between overflow-hidden bg-forest-900 text-paper">
        <div className="absolute inset-0">
          <Image
            src="/images/features/climate-drought.jpg"
            alt="Expansive wheat fields under dramatic sky"
            fill
            sizes="100vw"
            className="object-cover opacity-20 mix-blend-luminosity"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-forest-950 via-forest-900/90 to-forest-950" />
        </div>

        {/* Spacer to push content to vertical center */}
        <div className="h-12 shrink-0" />

        <div className="relative z-10 mx-auto w-full max-w-[900px] px-6 text-center md:px-10">
          <h2 className="font-display text-[40px] font-light leading-tight sm:text-[52px]">
            Equip your fields with scientific foresight.
          </h2>
          <p className="mx-auto mt-5 max-w-xl text-[16px] leading-relaxed text-forest-100/90">
            Explore live farm datasets across Kansas, evaluate crop rotation scenarios, and inspect full data provenance in the SOILSTICE platform.
          </p>
          <div className="mt-9 flex flex-wrap justify-center gap-4">
            <Link
              href="/dashboard"
              className="inline-flex h-13 items-center gap-2.5 rounded-xl bg-wheat-500 px-8 text-[15px] font-semibold text-forest-950 shadow-xl transition-transform hover:-translate-y-0.5 hover:bg-wheat-200"
            >
              <span>Launch SOILSTICE Dashboard</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/evidence"
              className="inline-flex h-13 items-center gap-2 rounded-xl border border-paper/25 bg-paper/10 px-6 text-[15px] font-semibold text-paper backdrop-blur hover:bg-paper/20"
            >
              <span>Inspect Evidence Register</span>
            </Link>
          </div>
        </div>

        {/* Integrated Footer as Bottom Screen Anchor */}
        <footer className="relative z-10 border-t border-line/20 bg-forest-950/60 py-8 text-center text-[12px] text-forest-200/80 backdrop-blur-sm">
          <div className="mx-auto max-w-[1240px] px-6 md:px-10">
            <p className="font-display text-[15px] font-semibold text-paper">SOILSTICE</p>
            <p className="mt-1">
              NASA Space Apps Challenge 2026 — Field Shift · Earth Observations &amp; Agricultural Records
            </p>
            <p className="mt-2 text-[11px] text-forest-300/60">
              Powered by NASA POWER, USDA NRCS SSURGO, USDA NASS CDL, and NASA SRTM. Developed with scientific transparency.
            </p>
          </div>
        </footer>
      </section>
    </div>
  );
}
