"""Farm, field and coverage services (E3–E12, E27)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from app.catalog import AOIS, DATASETS, INTEGRATED, descriptor
from app.contracts import (
    AOI,
    CoverageCount,
    CreateFieldRequest,
    CreateFieldResponse,
    DataCoverage,
    DatasetCoverage,
    Farm,
    FarmOverview,
    Field,
    FieldProfile,
    FieldSummary,
    LatestCrop,
    ProcessingJob,
    QualityFlag,
    Quantity,
    TemporalRange,
)
from app.errors import NotEditable, NotFound
from app.processing.geometry import to_geojson, validate_field_geometry
from app.repositories.records import FarmRecord

from .container import Container
from .pipeline import JobRunner, new_job

FARM_NAMESPACE = uuid.UUID("8a4f2b6e-1c3d-4e5f-9a7b-3c2d1e0f9a8b")
COVERAGE_DATASETS = [
    "meteomatics", "nasa_power_daily_ag", "usda_nrcs_ssurgo_sda", "usda_nass_cdl", "usda_nass_csb", "nasa_hls_vi", "nasa_hls",
    "nasa_smap_spl4smgp", "nasa_srtm_gl1", "prism_daily", "openet", "usda_nass_quickstats", "nasa_smap_spl3smp_e",
]


def seed_farms(ctx: Container) -> None:
    """The MVP has one demo workspace with one farm per AOI (PHASE_0 D8). Ids are deterministic."""
    t = datetime.now(UTC)
    for aoi in AOIS.values():
        fid = uuid.uuid5(FARM_NAMESPACE, aoi.aoi_id)
        if ctx.repos.farms.get(str(fid)) is None:
            ctx.repos.farms.put(str(fid), FarmRecord(farm_id=fid, name=aoi.farm_name, aoi_id=aoi.aoi_id,
                                                     created_at=t, updated_at=t))


class FieldService:
    def __init__(self, ctx: Container):
        self.ctx = ctx
        self.repos = ctx.repos

    # ── farms ──────────────────────────────────────────────────────────────
    def _farm_record(self, farm_id) -> FarmRecord:
        rec = self.repos.farms.get(str(farm_id))
        if rec is None:
            raise NotFound(f"Farm {farm_id} not found.", details={"farm_id": str(farm_id)})
        return rec

    def _fields_of(self, farm_id) -> list[Field]:
        return self.repos.fields.list(parent=str(farm_id))

    def _farm(self, rec: FarmRecord) -> Farm:
        aoi = AOIS[rec.aoi_id]
        fields = self._fields_of(rec.farm_id)
        total = sum(f.area.value or 0.0 for f in fields)
        return Farm(farm_id=rec.farm_id, name=rec.name,
                    aoi=AOI(aoi_id=aoi.aoi_id, label=aoi.label, county_fips=[aoi.county_fips], state="KS"),
                    field_count=len(fields), total_area=Quantity(value=round(total, 2), unit="ha"),
                    created_at=rec.created_at, updated_at=rec.updated_at)

    def list_farms(self) -> list[Farm]:
        return [self._farm(r) for r in self.repos.farms.list()]

    def get_farm(self, farm_id) -> Farm:
        return self._farm(self._farm_record(farm_id))

    def rename_farm(self, farm_id, name: str) -> Farm:
        rec = self._farm_record(farm_id)
        rec = rec.model_copy(update={"name": name.strip(), "updated_at": datetime.now(UTC)})
        self.repos.farms.put(str(rec.farm_id), rec)
        return self._farm(rec)

    def overview(self, farm_id, season_year: int | None = None) -> FarmOverview:
        farm = self.get_farm(farm_id)
        fields = self._fields_of(farm_id)
        summaries = [self.summary(f) for f in fields]
        coverages = [self.coverage(f) for f in fields]
        counts = []
        for ds in COVERAGE_DATASETS:
            rows = [r for c in coverages for r in c.datasets if r.dataset_id == ds]
            counts.append(CoverageCount(dataset_id=ds, fields_total=len(fields),
                                        fields_available=sum(r.status in ("available", "partial") for r in rows)))
        alerts: list[QualityFlag] = []
        n_failed = sum(f.processing_status == "failed" for f in fields)
        n_partial = sum(f.processing_status == "partial" for f in fields)
        n_proc = sum(f.processing_status == "processing" for f in fields)
        if n_failed:
            alerts.append(QualityFlag(code="FIELDS_FAILED", severity="warning",
                                      message=f"{n_failed} field(s) failed processing for every dataset."))
        if n_partial:
            alerts.append(QualityFlag(code="FIELDS_PARTIAL", severity="info",
                                      message=f"{n_partial} field(s) have one or more datasets unavailable."))
        if n_proc:
            alerts.append(QualityFlag(code="FIELDS_PROCESSING", severity="info",
                                      message=f"{n_proc} field(s) are still processing."))
        if not self.ctx.settings.meteomatics_configured and not self.ctx.settings.earthdata_configured:
            alerts.append(QualityFlag(code="EARTHDATA_NOT_CONFIGURED", severity="warning",
                                      message="Neither Meteomatics nor NASA Earthdata credentials are configured; terrain elevation and soil moisture cannot be acquired."))
        if not fields:
            alerts.append(QualityFlag(code="NO_FIELDS", severity="info",
                                      message="No fields yet. Draw a field in Settings to start real-data processing."))
        return FarmOverview(farm=farm, fields=summaries, coverage_summary=counts, alerts=alerts, regional_context=[])

    # ── fields ─────────────────────────────────────────────────────────────
    def get_field(self, field_id) -> Field:
        f = self.repos.fields.get(str(field_id))
        if f is None:
            raise NotFound(f"Field {field_id} not found.", details={"field_id": str(field_id)})
        return f

    def list_fields(self, farm_id, source: str | None = None, status: str | None = None) -> list[FieldSummary]:
        self._farm_record(farm_id)
        fields = [f for f in self._fields_of(farm_id)
                  if (source is None or f.source == source) and (status is None or f.processing_status == status)]
        return [self.summary(f) for f in fields]

    def summary(self, f: Field) -> FieldSummary:
        latest = None
        hist = self.repos.crop_history.get(str(f.field_id))
        if hist:
            known = [y for y in hist.years if y.majority.crop_code is not None]
            if known:
                y = known[-1]
                latest = LatestCrop(year=y.year, crop_code=y.majority.crop_code, crop_name=y.majority.crop_name)
        return FieldSummary(field_id=f.field_id, name=f.name, centroid=f.centroid, geometry=f.geometry, area=f.area,
                            source=f.source, processing_status=f.processing_status, latest_crop=latest,
                            resilience_band="unknown", coverage_completeness=self.coverage(f).completeness)

    def create_field(self, farm_id, req: CreateFieldRequest) -> CreateFieldResponse:
        rec = self._farm_record(farm_id)
        vg = validate_field_geometry(req.geometry, rec.aoi_id)
        field_id = uuid.uuid4()
        job = new_job(field_id)
        field = Field(
            field_id=field_id, farm_id=rec.farm_id, name=req.name.strip(), geometry=to_geojson(vg.geom),
            centroid=vg.centroid, area=Quantity(value=round(vg.area_ha, 2), unit="ha"),
            state_fips=vg.aoi.county_fips[:2], county_fips=vg.aoi.county_fips[2:], source="user", source_ref=None,
            csb_id=None, editable=True, processing_status="processing", latest_job_id=job.job_id,
            created_at=datetime.now(UTC),
        )
        self.repos.fields.put(str(field_id), field, parent=rec.farm_id)
        self.repos.jobs.put(str(job.job_id), job, parent=field_id)
        JobRunner(self.ctx).submit(job)
        return CreateFieldResponse(field=self.repos.fields.get(str(field_id)) or field,
                                   job=self.repos.jobs.get(str(job.job_id)) or job)

    def reprocess_field(self, field_id) -> CreateFieldResponse:
        f = self.get_field(field_id)
        job = new_job(f.field_id)
        updated_field = f.model_copy(update={
            "processing_status": "processing",
            "latest_job_id": job.job_id,
        })
        self.repos.fields.put(str(f.field_id), updated_field, parent=f.farm_id)
        self.repos.jobs.put(str(job.job_id), job, parent=str(f.field_id))
        JobRunner(self.ctx).submit(job)
        return CreateFieldResponse(
            field=self.repos.fields.get(str(f.field_id)) or updated_field,
            job=self.repos.jobs.get(str(job.job_id)) or job,
        )

    def delete_field(self, field_id) -> None:
        f = self.get_field(field_id)
        if not f.editable or f.source != "user":
            raise NotEditable("Only user-drawn fields can be deleted.", details={"source": f.source})
        self.repos.delete_field_data(str(f.field_id))

    def get_job(self, job_id) -> ProcessingJob:
        j = self.repos.jobs.get(str(job_id))
        if j is None:
            raise NotFound(f"Job {job_id} not found.", details={"job_id": str(job_id)})
        return j

    # ── coverage ───────────────────────────────────────────────────────────
    def coverage(self, f: Field) -> DataCoverage:
        states = {s.dataset_id: s for s in self.repos.dataset_states.list(parent=str(f.field_id))}
        rows: list[DatasetCoverage] = []
        for ds in COVERAGE_DATASETS:
            d = descriptor(ds)
            base = dict(dataset_id=ds, label=d.title, priority=d.priority, support_class=d.support_class,
                        native_resolution_m=d.native_resolution_m)
            if ds == "usda_nass_csb" and f.source != "csb":
                rows.append(DatasetCoverage(**base, status="not_applicable", temporal_coverage=d.temporal_coverage,
                                            product_version=d.product_version,
                                            note="User-drawn field: CSB applies only to CSB-sourced fields."))
            elif ds not in INTEGRATED:
                rows.append(DatasetCoverage(**base, status="not_integrated", temporal_coverage=d.temporal_coverage,
                                            product_version=d.product_version, missing_reason="NO_DATA_SOURCE",
                                            note=f"{d.priority} dataset planned; not yet integrated."))
            else:
                st = states.get(ds)
                if st is None:
                    status, reason, note = ("pending", "PENDING_PROCESSING", "Not yet processed.") \
                        if f.processing_status == "processing" else ("missing", "NOT_COMPUTED", "Not processed.")
                    rows.append(DatasetCoverage(**base, status=status, temporal_coverage=d.temporal_coverage,
                                                product_version=d.product_version, missing_reason=reason, note=note))
                else:
                    rows.append(DatasetCoverage(
                        **base, status=st.state,
                        temporal_coverage=TemporalRange(
                            start=date.fromisoformat(st.temporal_start) if st.temporal_start else
                            d.temporal_coverage.start,
                            end=date.fromisoformat(st.temporal_end) if st.temporal_end else d.temporal_coverage.end),
                        product_version=st.product_version or d.product_version, last_updated=st.updated_at,
                        missing_reason=st.missing_reason if st.state != "available" else None,
                        note=st.message))
        p0 = [r for r in rows if r.priority == "P0" and r.status != "not_applicable"]
        done = sum(r.status in ("available", "partial") for r in p0)
        return DataCoverage(field_id=f.field_id, datasets=rows, completeness=round(done / len(p0), 4) if p0 else 0.0)

    def get_coverage(self, field_id) -> DataCoverage:
        return self.coverage(self.get_field(field_id))

    def profile(self, field_id, season_year: int | None, env) -> FieldProfile:
        f = self.get_field(field_id)
        year = season_year or self.ctx.settings.default_season_year()
        climate = self.repos.climate.get(f"{f.field_id}:{year}")
        veg = env.indicators(f.field_id, category="vegetation", season_year=year)
        return FieldProfile(
            field=f, coverage=self.coverage(f), soil=self.repos.soil.get(str(f.field_id)),
            terrain=self.repos.terrain.get(str(f.field_id)), crop_history=self.repos.crop_history.get(str(f.field_id)),
            climate_summary=[i for i in (climate.indicators if climate else []) if i.value.value is not None or
                             i.key in ("precip_total_season", "solar_total_season", "rh_mean_season")],
            vegetation_summary=veg, resilience=env.resilience(f.field_id),
        )


_ = DATASETS  # re-exported for tests
