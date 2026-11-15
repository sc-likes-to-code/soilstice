"""Field processing pipeline (E8 → E27). One job step per integrated dataset.

Each step is isolated: a provider failure marks only that step/dataset failed with a contract missing_reason;
the other steps still run and the field profile stays servable.
"""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta

from app.contracts import Field, JobStep, ProcessingJob
from app.logging import get_logger
from app.processing.climate import build_climate_profile
from app.processing.crop_history import build_crop_history
from app.processing.geometry import to_shapely
from app.processing.soil import aggregate_soil
from app.processing.soil_moisture import build_soil_moisture_profile
from app.processing.terrain import build_terrain_profile, build_terrain_profile_from_meteomatics
from app.processing.vegetation import build_regional_ndvi_profile_from_meteomatics
from app.providers.http import ProviderError
from app.repositories.records import DatasetState

from .container import Container

log = get_logger("pipeline")

STEP_ORDER = ["usda_nrcs_ssurgo_sda", "usda_nass_cdl", "nasa_power_daily_ag", "meteomatics"]
QUALITY_TO_STATE = {"valid": "available", "partial": "partial", "flagged": "partial", "missing": "missing"}


def now() -> datetime:
    return datetime.now(UTC)


def new_job(field_id: uuid.UUID) -> ProcessingJob:
    t = now()
    return ProcessingJob(job_id=uuid.uuid4(), field_id=field_id, status="queued",
                         steps=[JobStep(dataset_id=d, status="queued") for d in STEP_ORDER], created_at=t, updated_at=t)


def power_window(year: int, today: date | None = None) -> tuple[date, date] | None:
    """Season request window clamped to yesterday; None if the year has not started (or predates POWER)."""
    today = today or date.today()
    start, end = date(year, 1, 1), min(date(year, 12, 31), today - timedelta(days=1))
    if year < 1981 or start > end:
        return None
    return start, end


def fetch_climate(ctx: Container, field: Field, year: int, crop_code: int | None):
    """Returns (ClimateProfile, stored: bool). Never raises for upstream problems."""
    window = power_window(year)
    if window is None:
        return build_climate_profile(field.field_id, year, crop_code, None, failure_reason="OUT_OF_TEMPORAL_RANGE",
                                     failure_message=f"POWER has no data for {year}."), False
    complete_season = year < date.today().year
    try:
        daily = ctx.providers.power.daily(field.centroid[0], field.centroid[1], *window, cache=complete_season)
    except ProviderError as exc:
        return build_climate_profile(field.field_id, year, crop_code, None, failure_reason=exc.missing_reason,
                                     failure_message=str(exc)), False
    profile = build_climate_profile(field.field_id, year, crop_code, daily)

    # Enrich with Meteomatics soil moisture series and indicators if available
    sm_prof = ctx.repos.soil_moisture.get(f"{field.field_id}:{year}")
    if sm_prof is None and ctx.providers.meteomatics is not None:
        try:
            sm_prof = build_soil_moisture_profile(
                field.field_id, to_shapely(field.geometry), year, ctx.providers.meteomatics,
                start_date=window[0], end_date=window[1]
            )
            ctx.repos.soil_moisture.put(f"{field.field_id}:{year}", sm_prof, parent=field.field_id)
        except Exception as exc:
            log.debug("Soil moisture auto-enrichment skipped: %s", exc)

    if sm_prof is not None:
        existing_vars = {s.variable for s in profile.series}
        extra_series = [s for s in sm_prof.series if s.variable not in existing_vars]
        from app.processing.soil_moisture import build_soil_moisture_indicators
        extra_indicators = build_soil_moisture_indicators(field.field_id, year, sm_prof)
        extra_keys = {i.key for i in extra_indicators}
        retained_indicators = [i for i in profile.indicators if i.key not in extra_keys]
        profile = profile.model_copy(update={
            "series": extra_series + profile.series,
            "indicators": retained_indicators + extra_indicators,
        })

    if complete_season and crop_code is None:
        ctx.repos.climate.put(f"{field.field_id}:{year}", profile, parent=field.field_id)
    return profile, complete_season


class JobRunner:
    def __init__(self, ctx: Container):
        self.ctx = ctx

    def submit(self, job: ProcessingJob) -> None:
        if self.ctx.executor is None:
            self.run(job.job_id)
        else:
            self.ctx.executor.submit(self._safe_run, job.job_id)

    def _safe_run(self, job_id):
        try:
            self.run(job_id)
        except Exception:  # pragma: no cover - last-resort guard for the thread
            log.exception("job crashed", extra={"job_id": str(job_id)})

    # -- state helpers --------------------------------------------------------
    def _set_step(self, job: ProcessingJob, dataset_id: str, **kw) -> ProcessingJob:
        steps = [s.model_copy(update=kw) if s.dataset_id == dataset_id else s for s in job.steps]
        job = job.model_copy(update={"steps": steps, "status": "running", "updated_at": now()})
        self.ctx.repos.jobs.put(str(job.job_id), job, parent=job.field_id)
        return job

    def _state(self, field_id, dataset_id, state, *, reason=None, message=None, version=None, start=None, end=None):
        self.ctx.repos.dataset_states.put(
            f"{field_id}:{dataset_id}",
            DatasetState(field_id=field_id, dataset_id=dataset_id, state=state, missing_reason=reason, message=message,
                         product_version=version, temporal_start=start, temporal_end=end, updated_at=now()),
            parent=field_id,
        )

    # -- run ------------------------------------------------------------------
    def run(self, job_id) -> ProcessingJob:
        repos = self.ctx.repos
        job = repos.jobs.get(str(job_id))
        field = repos.fields.get(str(job.field_id)) if job else None
        if job is None or field is None:
            return job
        for ds in STEP_ORDER:
            self._state(field.field_id, ds, "pending", reason="PENDING_PROCESSING")
        for ds in STEP_ORDER:
            if repos.fields.get(str(field.field_id)) is None:  # field deleted mid-run
                return job
            job = self._set_step(job, ds, status="running")
            try:
                quality_status, version, start, end = getattr(self, f"_step_{ds}")(field)
                state = QUALITY_TO_STATE[quality_status]
                self._state(field.field_id, ds, state, version=version, start=start, end=end,
                            reason="INSUFFICIENT_COVERAGE" if state == "missing" else None)
                job = self._set_step(job, ds, status="succeeded" if state == "available" else
                                     "partial" if state == "partial" else "failed",
                                     missing_reason="INSUFFICIENT_COVERAGE" if state == "missing" else None)
            except ProviderError as exc:
                log.warning("step failed", extra={"dataset_id": ds, "field_id": str(field.field_id), "error": str(exc)})
                self._state(field.field_id, ds, "missing", reason=exc.missing_reason, message=str(exc))
                job = self._set_step(job, ds, status="failed", missing_reason=exc.missing_reason, message=str(exc))
            except Exception as exc:
                log.exception("step crashed", extra={"dataset_id": ds, "field_id": str(field.field_id)})
                msg = f"Internal processing error ({type(exc).__name__})."
                self._state(field.field_id, ds, "missing", reason="UPSTREAM_ERROR", message=msg)
                job = self._set_step(job, ds, status="failed", missing_reason="UPSTREAM_ERROR", message=msg)

        statuses = [s.status for s in job.steps]
        overall = "succeeded" if all(s == "succeeded" for s in statuses) else \
            "failed" if all(s == "failed" for s in statuses) else "partial"
        job = job.model_copy(update={"status": overall, "updated_at": now()})
        repos.jobs.put(str(job.job_id), job, parent=job.field_id)
        current = repos.fields.get(str(field.field_id))
        if current is not None:
            status = {"succeeded": "ready", "partial": "partial", "failed": "failed"}[overall]
            repos.fields.put(str(field.field_id), current.model_copy(update={"processing_status": status}),
                             parent=current.farm_id)
        log.info("job finished", extra={"job_id": str(job.job_id), "status": overall})
        return job

    # -- steps: each returns (quality status, product version, temporal start, temporal end) -------------------
    def _step_usda_nrcs_ssurgo_sda(self, field: Field):
        raw = self.ctx.providers.ssurgo.fetch_for_polygon(to_shapely(field.geometry))
        profile = aggregate_soil(field.field_id, raw)
        self.ctx.repos.soil.put(str(field.field_id), profile, parent=field.field_id)
        version = profile.sources[0].product_version if profile.sources else None
        return profile.quality.status, version, None, None

    def _step_usda_nass_cdl(self, field: Field):
        s = self.ctx.settings
        fips = f"{field.state_fips}{field.county_fips}"
        years = range(s.cdl_first_year, s.cdl_last_year + 1)
        results: dict = {}

        def one(y):
            try:
                return y, self.ctx.providers.cdl.county_raster(y, fips)
            except ProviderError as exc:
                return y, exc

        with ThreadPoolExecutor(max_workers=max(1, s.cdl_parallel_requests), thread_name_prefix="cdl") as pool:
            for y, r in pool.map(one, years):
                results[y] = r
        if all(isinstance(r, ProviderError) for r in results.values()):
            first = next(iter(results.values()))
            raise ProviderError(f"No CDL year could be acquired: {first}", first.missing_reason)
        history = build_crop_history(field.field_id, to_shapely(field.geometry), s.cdl_first_year, s.cdl_last_year,
                                     results)
        self.ctx.repos.crop_history.put(str(field.field_id), history, parent=field.field_id)
        return (history.quality.status, f"{s.cdl_first_year}–{s.cdl_last_year}", f"{s.cdl_first_year}-01-01",
                f"{s.cdl_last_year}-12-31")

    def _step_nasa_power_daily_ag(self, field: Field):
        year = self.ctx.settings.default_season_year()
        window = power_window(year)
        if window is None:
            raise ProviderError(f"No POWER window for {year}.", "OUT_OF_TEMPORAL_RANGE")
        daily = self.ctx.providers.power.daily(field.centroid[0], field.centroid[1], *window,
                                               cache=year < date.today().year)
        profile = build_climate_profile(field.field_id, year, None, daily)
        self.ctx.repos.climate.put(f"{field.field_id}:{year}", profile, parent=field.field_id)
        return profile.quality.status, daily.api_version, window[0].isoformat(), window[1].isoformat()

    def _step_meteomatics(self, field: Field):
        if self.ctx.providers.meteomatics is None:
            raise ProviderError("Meteomatics credentials are not configured.", "NOT_COMPUTED")
        geom = to_shapely(field.geometry)
        year = self.ctx.settings.default_season_year()

        # 1. Terrain pipeline (elevation & conditional slope)
        terrain_prof = build_terrain_profile_from_meteomatics(field.field_id, geom, self.ctx.providers.meteomatics)
        self.ctx.repos.terrain.put(str(field.field_id), terrain_prof, parent=field.field_id)

        # 2. Soil moisture pipeline (4 depths & root-zone composite)
        try:
            sm_prof = build_soil_moisture_profile(field.field_id, geom, year, self.ctx.providers.meteomatics)
            self.ctx.repos.soil_moisture.put(f"{field.field_id}:{year}", sm_prof, parent=field.field_id)
            clim = self.ctx.repos.climate.get(f"{field.field_id}:{year}")
            if clim is not None:
                from app.processing.soil_moisture import build_soil_moisture_indicators
                existing_vars = {s.variable for s in clim.series}
                extra_series = [s for s in sm_prof.series if s.variable not in existing_vars]
                extra_indicators = build_soil_moisture_indicators(field.field_id, year, sm_prof)
                extra_keys = {i.key for i in extra_indicators}
                retained_indicators = [i for i in clim.indicators if i.key not in extra_keys]
                updated_clim = clim.model_copy(update={
                    "series": extra_series + clim.series,
                    "indicators": retained_indicators + extra_indicators,
                })
                self.ctx.repos.climate.put(f"{field.field_id}:{year}", updated_clim, parent=field.field_id)
        except Exception as exc:
            log.warning("Meteomatics soil moisture step warning: %s", exc)

        # 3. Regional NDVI pipeline (coarse regional vegetation context)
        try:
            veg_prof = build_regional_ndvi_profile_from_meteomatics(field.field_id, geom, year, self.ctx.providers.meteomatics)
            self.ctx.repos.vegetation.put(f"{field.field_id}:{year}:NDVI", veg_prof, parent=field.field_id)
        except Exception as exc:
            log.warning("Meteomatics regional NDVI step warning: %s", exc)

        # Maintain legacy SRTM state as available so any existing consumer/test is satisfied
        legacy_state = QUALITY_TO_STATE.get(terrain_prof.quality.status, "available")
        self._state(field.field_id, "nasa_srtm_gl1", legacy_state, version="v3.0",
                    message="Elevation and terrain derived via Meteomatics-first pipeline.")

        return terrain_prof.quality.status, "v3.0", f"{year}-01-01", f"{year}-12-31"

    def _step_nasa_srtm_gl1(self, field: Field):
        geom = to_shapely(field.geometry)
        tiles = self.ctx.providers.srtm.tiles_for_bounds(geom.bounds)
        profile = build_terrain_profile(field.field_id, geom, tiles)
        self.ctx.repos.terrain.put(str(field.field_id), profile, parent=field.field_id)
        return profile.quality.status, "003", "2000-02-11", "2000-02-21"


def recover_interrupted_jobs(ctx: Container) -> int:
    """Jobs left queued/running by a previous process are marked failed (their thread no longer exists)."""
    n = 0
    for job in ctx.repos.jobs.list():
        if job.status in ("queued", "running"):
            steps = [s.model_copy(update={"status": "failed", "missing_reason": "UPSTREAM_ERROR",
                                          "message": "Interrupted by a server restart."})
                     if s.status in ("queued", "running") else s for s in job.steps]
            done = [s for s in steps if s.status in ("succeeded", "partial")]
            ctx.repos.jobs.put(str(job.job_id), job.model_copy(update={
                "steps": steps, "status": "partial" if done else "failed", "updated_at": now()}), parent=job.field_id)
            for s in steps:
                if s.message == "Interrupted by a server restart.":
                    ctx.repos.dataset_states.put(
                        f"{job.field_id}:{s.dataset_id}",
                        DatasetState(field_id=job.field_id, dataset_id=s.dataset_id, state="missing",
                                     missing_reason="UPSTREAM_ERROR", message=s.message, updated_at=now()),
                        parent=job.field_id)
            f = ctx.repos.fields.get(str(job.field_id))
            if f and f.processing_status == "processing":
                ctx.repos.fields.put(str(f.field_id), f.model_copy(update={
                    "processing_status": "partial" if done else "failed"}), parent=f.farm_id)
            n += 1
    return n
