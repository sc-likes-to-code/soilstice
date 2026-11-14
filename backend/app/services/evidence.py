"""Evidence service (E2, E26): dataset register, method notes and per-field acquisition/indicator lineage."""

from __future__ import annotations

import uuid

from app.analytics.resilience import RULE_PENDING
from app.catalog import DATASETS, INTEGRATED
from app.contracts import DatasetDescriptor, EvidenceItem
from app.processing.climate import METHOD_MEAN, METHOD_SUM
from app.processing.crop_history import METHOD_PENDING_ROTATION
from app.processing.soil import METHOD as SOIL_METHOD
from app.processing.terrain import METHOD as TERRAIN_METHOD

from .container import Container
from .environment import EnvironmentService

NS = uuid.UUID("3e9d8c7b-6a5f-4e3d-2c1b-0a9f8e7d6c5b")
METHODS = [SOIL_METHOD, TERRAIN_METHOD, METHOD_SUM, METHOD_MEAN, METHOD_PENDING_ROTATION, RULE_PENDING]


class EvidenceService:
    def __init__(self, ctx: Container):
        self.ctx = ctx
        self.env = EnvironmentService(ctx)

    def datasets(self) -> list[DatasetDescriptor]:
        return DATASETS

    def global_items(self) -> list[EvidenceItem]:
        items = [
            EvidenceItem(
                evidence_id=uuid.uuid5(NS, f"dataset:{d.dataset_id}"), kind="dataset", title=d.title,
                summary=f"{d.publisher} · {d.product} {d.product_version} · {d.priority} · support {d.support_class}. "
                        + ("Integrated in the backend." if d.dataset_id in INTEGRATED else "Planned; not integrated."),
                dataset_id=d.dataset_id, product_version=d.product_version,
                citation=f"{d.publisher}. {d.title} ({d.product}, version {d.product_version}).",
                url=d.documentation_url, doi=d.doi, accessed_at=d.last_verified,
                verification_status=d.verification_status, related_ids=[d.dataset_id],
            )
            for d in DATASETS
        ]
        items += [
            EvidenceItem(
                evidence_id=uuid.uuid5(NS, f"method:{m.method_id}:{m.version}"), kind="method", title=m.name,
                summary=m.description, dataset_id="soilstice_derived", product_version=m.version,
                citation="SOILSTICE Phase 0 architecture documents (2026-11-14).", url=m.reference_url,
                verification_status="DOC", related_ids=[m.method_id],
            )
            for m in METHODS
        ]
        return items

    def field_items(self, field_id) -> list[EvidenceItem]:
        f = self.env.fields.get_field(field_id)
        repos = self.ctx.repos
        acq_ids: dict[str, str] = {}
        for prof in (repos.soil.get(str(f.field_id)), repos.terrain.get(str(f.field_id))):
            for s in (prof.sources if prof else []):
                if s.acquisition_id:
                    acq_ids[str(s.acquisition_id)] = s.dataset_id
        hist = repos.crop_history.get(str(f.field_id))
        for y in (hist.years if hist else []):
            if y.source.acquisition_id:
                acq_ids[str(y.source.acquisition_id)] = y.source.dataset_id
        for c in repos.climate.list(parent=str(f.field_id)):
            for s in (c.series[0].sources if c.series else []):
                if s.acquisition_id:
                    acq_ids[str(s.acquisition_id)] = s.dataset_id
        items: list[EvidenceItem] = []
        for aid, ds in acq_ids.items():
            rec = repos.acquisitions.get(aid)
            if rec is None:
                continue
            items.append(EvidenceItem(
                evidence_id=uuid.uuid5(NS, f"acq:{f.field_id}:{aid}"), kind="dataset",
                title=f"Acquisition: {ds}", summary=f"HTTP {rec.http_status}, {rec.bytes or 0} bytes, sha256 "
                                                     f"{(rec.sha256 or '')[:16]}…",
                field_id=f.field_id, dataset_id=ds, url=rec.request_url, accessed_at=rec.retrieved_at.date(),
                verification_status="LIVE", related_ids=[ds, aid],
            ))
        for ind in self.env.indicators(f.field_id):
            if ind.value.value is None:
                continue
            items.append(EvidenceItem(
                evidence_id=uuid.uuid5(NS, f"ind:{ind.indicator_id}"), kind="indicator", title=ind.label,
                summary=f"{ind.value.value} {ind.value.unit} · support {ind.spatial.support_class} · method "
                        f"{ind.method.method_id} v{ind.method.version}",
                field_id=f.field_id, dataset_id=ind.sources[0].dataset_id if ind.sources else None,
                product_version=ind.sources[0].product_version if ind.sources else None,
                verification_status="LIVE", spatial=ind.spatial, temporal=ind.temporal,
                related_ids=[ind.indicator_id, ind.key, *ind.input_ids],
            ))
        return items

    def evidence(self, field_id, kind: str | None = None, related_id: str | None = None) -> list[EvidenceItem]:
        items = self.global_items() + self.field_items(field_id)
        return [i for i in items if (kind is None or i.kind == kind) and
                (related_id is None or related_id in i.related_ids)]
