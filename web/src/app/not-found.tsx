import Link from "next/link";
import { Brand } from "@/components/layout/brand";

export default function NotFound() {
  return (
    <div className="grid flex-1 place-items-center px-6 py-24">
      <div className="max-w-md text-center">
        <Brand />
        <h1 className="mt-8 font-display text-[34px] text-ink">This page isn’t on the map</h1>
        <p className="mt-3 text-[14px] text-ink-soft">The address doesn’t match any SOILSTICE page.</p>
        <div className="mt-6 flex justify-center gap-3">
          <Link href="/dashboard" className="inline-flex h-10 items-center rounded-lg bg-forest-800 px-4 text-[13.5px] font-semibold text-paper">Go to dashboard</Link>
          <Link href="/fields" className="inline-flex h-10 items-center rounded-lg border border-line-strong px-4 text-[13.5px] font-semibold text-ink">Field Explorer</Link>
        </div>
      </div>
    </div>
  );
}
