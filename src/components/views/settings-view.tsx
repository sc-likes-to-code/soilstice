"use client";
import Link from "next/link";
import { useState } from "react";
import { Check, Loader2, MousePointerClick, Pencil, Plus, Trash2, Undo2, X } from "lucide-react";
import type { Farm, JobStatus } from "@/types/contracts";
import { useActiveFarm } from "@/hooks/active-farm";
import { useCreateField, useDeleteField, useFields, useJob, useUpdateFarm } from "@/hooks/queries";
import { usePrefs } from "@/hooks/preferences";
import { isApiError } from "@/services";
import { useDataMode } from "@/hooks/data-mode";
import { DataModeToggle } from "@/components/layout/data-mode-toggle";
import { apiBaseUrl } from "@/services/http/client";
import { AOI_BBOX, MAX_FIELD_HA } from "@/lib/aoi";
import { ringToMultiPolygon, validateFieldDraft, type FieldDraftIssue, type LngLat } from "@/lib/geo";
import { formatNumber, qText } from "@/lib/format";
import { DATASET_SHORT } from "@/lib/vocab";
import { cn } from "@/lib/cn";
import { Badge, Button, Card, CardBody, CardHeader, PageHeader, Segmented, Skeleton } from "@/components/ui/primitives";
import { ErrorState } from "@/components/shared/state";
import { FieldMap } from "@/components/shared/field-map";
import { SyntheticBadge } from "@/components/shared/provenance";

const ISSUE_TEXT: Record<FieldDraftIssue, string> = {
  TOO_FEW_VERTICES: "Click at least three points to outline the field.",
  SELF_INTERSECTING: "The outline crosses itself — undo the last point and try again.",
  OUTSIDE_AOI: "Every vertex must lie inside the farm’s county (dashed outline).",
  FIELD_TOO_LARGE: `Fields are limited to ${MAX_FIELD_HA} ha.`,
  FIELD_TOO_SMALL: "The outline is too small to be a field.",
};

export function SettingsView() {
  const { farm, isLoading, error, refetch } = useActiveFarm();
  if (error) return <ErrorState error={error} onRetry={refetch} />;
  return (
    <div>
      <PageHeader eyebrow="Farm & Settings" title="Farm & settings" description="Manage the demo farm and its fields, display preferences and data attribution." />
      {isLoading || !farm ? <Skeleton className="h-96" /> : <Settings farm={farm} />}
    </div>
  );
}

function Settings({ farm }: { farm: Farm }) {
  const { units, setUnits } = usePrefs();
  const { isApi } = useDataMode();
  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
      <div className="space-y-6">
        <FarmCard farm={farm} />
        <AddField farm={farm} />
        <FieldsCard farm={farm} />
      </div>
      <div className="space-y-6">
        <Card>
          <CardHeader eyebrow="Display" title="Units" description="Display only — the API always returns metric units." />
          <CardBody><Segmented label="Unit system" value={units} onChange={setUnits} options={[{ value: "metric", label: "Metric (ha, mm, °C)" }, { value: "us", label: "US customary (ac, in, °F)" }]} /></CardBody>
        </Card>
        <Card>
          <CardHeader eyebrow="Data" title="Data source mode" description="Switch between live backend observations and offline demonstration fixtures." />
          <CardBody className="space-y-3 text-[12.5px] text-ink-soft">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span className="font-semibold text-ink">Active mode:</span>
              <DataModeToggle />
            </div>
            <p>
              {isApi ? (
                <span className="font-medium text-forest-800">
                  Live API active. Connected to FastAPI backend on port 8000 for verified USDA (SSURGO, CDL) and NASA (POWER, SRTM) observations.
                </span>
              ) : (
                <span className="font-medium text-clay-600">
                  Mock Data active. Using offline synthetic demonstration world (Reno Demo Farm &amp; Finney Demo Farm, 14 parcels).
                </span>
              )}
            </p>
            <p>API base URL: <span className="font-mono text-[11.5px] text-ink">{apiBaseUrl()}</span></p>
          </CardBody>
        </Card>
        <Card>
          <CardHeader eyebrow="Attribution" title="Data & licences" />
          <CardBody className="space-y-2 text-[12px] leading-relaxed text-ink-soft">
            <p>Operational live sources: NASA POWER, USDA NRCS SSURGO, USDA NASS Cropland Data Layer (CDL), and NASA SRTM. Staged for Phase 3: NASA SMAP and NASA HLS.</p>
            <p>Map rendering: MapLibre GL JS with Esri World Imagery (satellite) and Carto Voyager (topographic basemap).</p>
            <p>Inspect dataset provenance and methods on the <Link href="/evidence" className="font-semibold text-forest-700 underline underline-offset-2">Evidence registry</Link>.</p>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}

function FarmCard({ farm }: { farm: Farm }) {
  const { units } = usePrefs();
  const update = useUpdateFarm();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(farm.name);
  return (
    <Card>
      <CardHeader eyebrow="Farm" title={farm.name} actions={!editing && <Button size="sm" variant="ghost" onClick={() => { setName(farm.name); setEditing(true); }}><Pencil className="h-3.5 w-3.5" /> Rename</Button>} />
      <CardBody className="space-y-4">
        {editing && (
          <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); update.mutate({ id: farm.farm_id, name }, { onSuccess: () => setEditing(false) }); }}>
            <input aria-label="Farm name" value={name} onChange={(e) => setName(e.target.value)} maxLength={80} className="h-10 min-w-[240px] flex-1 rounded-lg border border-line-strong bg-paper px-3 text-[13.5px]" />
            <Button variant="primary" type="submit" disabled={update.isPending}><Check className="h-4 w-4" /> Save</Button>
            <Button type="button" variant="ghost" onClick={() => setEditing(false)}>Cancel</Button>
          </form>
        )}
        {update.isError && <ErrorState error={update.error} compact />}
        <dl className="grid grid-cols-2 gap-4 text-[13px] sm:grid-cols-4">
          <div><dt className="text-[11px] font-semibold uppercase tracking-[0.1em] text-stone-500">Area of interest</dt><dd className="mt-1 font-semibold">{farm.aoi.label}</dd></div>
          <div><dt className="text-[11px] font-semibold uppercase tracking-[0.1em] text-stone-500">County FIPS</dt><dd className="mt-1 font-mono">{farm.aoi.county_fips.join(", ")}</dd></div>
          <div><dt className="text-[11px] font-semibold uppercase tracking-[0.1em] text-stone-500">Fields</dt><dd className="mt-1 font-semibold tabular">{farm.field_count}</dd></div>
          <div><dt className="text-[11px] font-semibold uppercase tracking-[0.1em] text-stone-500">Total area</dt><dd className="mt-1 font-semibold tabular">{qText(farm.total_area, units)}</dd></div>
        </dl>
      </CardBody>
    </Card>
  );
}

function AddField({ farm }: { farm: Farm }) {
  const { units } = usePrefs();
  const { isMock } = useDataMode();
  const fields = useFields(farm.farm_id);
  const create = useCreateField(farm.farm_id);
  const [drawing, setDrawing] = useState(false);
  const [pts, setPts] = useState<LngLat[]>([]);
  const [name, setName] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const bbox = AOI_BBOX[farm.aoi.aoi_id];
  const check = validateFieldDraft(pts, bbox, MAX_FIELD_HA);
  const apiErr = create.error;

  const submit = () => {
    if (!check.ok || !name.trim()) return;
    create.mutate({ name: name.trim(), geometry: ringToMultiPolygon(pts) }, {
      onSuccess: (r) => { setJobId(r.data.job.job_id); setPts([]); setName(""); setDrawing(false); },
    });
  };

  return (
    <Card>
      <CardHeader eyebrow="Add field" title="Draw a field boundary" description={`Click on the map to place vertices inside ${farm.aoi.label}. Fields up to ${MAX_FIELD_HA} ha.`} actions={isMock ? <SyntheticBadge /> : undefined} />
      <CardBody className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          {!drawing ? (
            <Button variant="primary" onClick={() => { setDrawing(true); setPts([]); create.reset(); }}><MousePointerClick className="h-4 w-4" /> Start drawing</Button>
          ) : (
            <>
              <Badge className="bg-wheat-100 text-wheat-600">Drawing · {pts.length} point{pts.length === 1 ? "" : "s"}</Badge>
              <Button size="sm" variant="secondary" onClick={() => setPts((p) => p.slice(0, -1))} disabled={!pts.length}><Undo2 className="h-3.5 w-3.5" /> Undo</Button>
              <Button size="sm" variant="ghost" onClick={() => setPts([])} disabled={!pts.length}><X className="h-3.5 w-3.5" /> Clear</Button>
              <Button size="sm" variant="ghost" onClick={() => { setDrawing(false); setPts([]); }}>Cancel</Button>
            </>
          )}
          {pts.length >= 3 && <span className="ml-auto text-[12.5px] tabular text-ink-soft">≈ {formatNumber(units === "us" ? check.areaHa * 2.47105 : check.areaHa, 1)} {units === "us" ? "ac" : "ha"} (approximate)</span>}
        </div>
        <FieldMap
          height={380}
          aoiBbox={bbox}
          fields={(fields.data?.data ?? []).map((f) => ({ field_id: f.field_id, name: f.name, geometry: f.geometry, muted: true }))}
          colorBy="none"
          drawing={drawing}
          draft={pts}
          onMapClick={(p) => setPts((x) => [...x, p])}
          caption="Dashed outline: approximate county extent"
        />
        {drawing && pts.length > 0 && !check.ok && (
          <ul className="space-y-1 text-[12.5px] text-wheat-600">{check.issues.map((i) => <li key={i}>• {ISSUE_TEXT[i]}</li>)}</ul>
        )}
        {drawing && (
          <div className="flex flex-wrap gap-2">
            <input aria-label="Field name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Field name" maxLength={80} className="h-10 min-w-[220px] flex-1 rounded-lg border border-line-strong bg-paper px-3 text-[13.5px]" />
            <Button variant="primary" onClick={submit} disabled={!check.ok || !name.trim() || create.isPending}>
              {create.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />} Create field
            </Button>
          </div>
        )}
        {apiErr && <ErrorState error={apiErr} compact title={isApiError(apiErr) && apiErr.code === "OUTSIDE_AOI" ? "Outside the area of interest" : isApiError(apiErr) && apiErr.code === "FIELD_TOO_LARGE" ? "Field too large" : "Could not create field"} />}
        {jobId && <JobProgress jobId={jobId} onClose={() => setJobId(null)} />}
      </CardBody>
    </Card>
  );
}

const JOB_STYLE: Record<JobStatus, string> = {
  queued: "bg-parchment text-stone-600",
  running: "bg-sky-100 text-sky-600",
  succeeded: "bg-forest-100 text-forest-800",
  partial: "bg-wheat-100 text-wheat-600",
  failed: "bg-clay-100 text-clay-600",
};

function JobProgress({ jobId, onClose }: { jobId: string; onClose: () => void }) {
  const job = useJob(jobId);
  if (job.isPending) return <Skeleton className="h-32" />;
  if (job.isError) return <ErrorState error={job.error} compact onRetry={() => void job.refetch()} />;
  const j = job.data.data;
  const done = j.status !== "queued" && j.status !== "running";
  return (
    <div className="rounded-xl border border-sky-100 bg-sky-100/30 p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <p className="flex items-center gap-2 text-[13px] font-semibold text-ink">
          {!done && <Loader2 className="h-4 w-4 animate-spin text-sky-600" />} Processing job <Badge className={JOB_STYLE[j.status]}>{j.status}</Badge>
        </p>
        <div className="flex gap-2">
          {done && <Link href={`/fields/${j.field_id}`} className="text-[12.5px] font-semibold text-forest-700">Open field →</Link>}
          <button onClick={onClose} aria-label="Dismiss" className="text-stone-400 hover:text-ink"><X className="h-4 w-4" /></button>
        </div>
      </div>
      <ul className="grid gap-1.5 sm:grid-cols-2">
        {j.steps.map((s) => (
          <li key={s.dataset_id} className="flex items-center justify-between gap-2 rounded-lg bg-paper px-3 py-2 text-[12px]">
            <span className="font-semibold">{DATASET_SHORT[s.dataset_id]}</span>
            <Badge className={JOB_STYLE[s.status]}>{s.status === "partial" ? "deferred" : s.status}</Badge>
          </li>
        ))}
      </ul>
      {done && j.status === "partial" && <p className="mt-3 text-[12px] text-ink-soft">Satellite datasets (HLS, SMAP) are deferred to the background batch; the field shows them as pending.</p>}
    </div>
  );
}

function FieldsCard({ farm }: { farm: Farm }) {
  const { units } = usePrefs();
  const fields = useFields(farm.farm_id);
  const del = useDeleteField();
  const [confirm, setConfirm] = useState<string | null>(null);
  return (
    <Card>
      <CardHeader eyebrow="Fields" title="Fields on this farm" description="Only user-drawn fields can be deleted." />
      <CardBody className="pt-2">
        {fields.isPending ? <Skeleton className="h-40" /> : fields.isError ? <ErrorState error={fields.error} onRetry={() => void fields.refetch()} /> : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-[12.5px]">
              <thead><tr className="border-b border-line text-[10.5px] uppercase tracking-[0.12em] text-stone-500"><th className="py-2 pr-3 font-semibold">Name</th><th className="py-2 pr-3 font-semibold">Source</th><th className="py-2 pr-3 font-semibold">Area</th><th className="py-2 pr-3 font-semibold">Status</th><th className="py-2 font-semibold" /></tr></thead>
              <tbody>
                {fields.data.data.map((f) => (
                  <tr key={f.field_id} className="border-b border-line/60 last:border-0">
                    <td className="py-2.5 pr-3"><Link href={`/fields/${f.field_id}`} className="font-semibold text-ink hover:text-forest-700">{f.name}</Link></td>
                    <td className="py-2.5 pr-3 text-ink-soft">{f.source === "user" ? "User-drawn" : f.source === "csb" ? "CSB" : "Synthetic"}</td>
                    <td className="py-2.5 pr-3 tabular text-ink-soft">{qText(f.area, units)}</td>
                    <td className="py-2.5 pr-3 text-ink-soft">{f.processing_status}</td>
                    <td className="py-2.5 text-right">
                      {f.source === "user" ? (
                        confirm === f.field_id ? (
                          <span className="inline-flex items-center gap-2">
                            <span className="text-[12px] text-clay-600">Delete permanently?</span>
                            <Button size="sm" variant="danger" onClick={() => del.mutate(f.field_id, { onSuccess: () => setConfirm(null) })} disabled={del.isPending}>Delete</Button>
                            <Button size="sm" variant="ghost" onClick={() => setConfirm(null)}>Keep</Button>
                          </span>
                        ) : (
                          <Button size="sm" variant="ghost" onClick={() => setConfirm(f.field_id)} aria-label={`Delete ${f.name}`}><Trash2 className="h-3.5 w-3.5" /></Button>
                        )
                      ) : <span className={cn("text-[11px] text-stone-400")}>—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {del.isError && <div className="mt-3"><ErrorState error={del.error} compact /></div>}
          </div>
        )}
      </CardBody>
    </Card>
  );
}
