"""Typed repositories for every stored entity."""

from __future__ import annotations

from dataclasses import dataclass

from app.contracts import (
    ClimateProfile,
    CropHistory,
    Field,
    ProcessingJob,
    RotationScenario,
    SoilMoistureProfile,
    SoilProfile,
    TerrainProfile,
    VegetationProfile,
)

from .records import AcquisitionRecord, DatasetState, FarmRecord
from .store import DocumentStore, ModelRepository, SqliteDocumentStore


@dataclass
class Repositories:
    store: DocumentStore
    farms: ModelRepository[FarmRecord]
    fields: ModelRepository[Field]
    jobs: ModelRepository[ProcessingJob]
    soil: ModelRepository[SoilProfile]
    terrain: ModelRepository[TerrainProfile]
    crop_history: ModelRepository[CropHistory]
    climate: ModelRepository[ClimateProfile]
    dataset_states: ModelRepository[DatasetState]
    acquisitions: ModelRepository[AcquisitionRecord]
    scenarios: ModelRepository[RotationScenario]
    vegetation: ModelRepository[VegetationProfile]
    soil_moisture: ModelRepository[SoilMoistureProfile]

    @classmethod
    def create(cls, store: DocumentStore) -> Repositories:
        return cls(
            store=store,
            farms=ModelRepository(store, "farms", FarmRecord),
            fields=ModelRepository(store, "fields", Field),
            jobs=ModelRepository(store, "jobs", ProcessingJob),
            soil=ModelRepository(store, "soil", SoilProfile),
            terrain=ModelRepository(store, "terrain", TerrainProfile),
            crop_history=ModelRepository(store, "crop_history", CropHistory),
            climate=ModelRepository(store, "climate", ClimateProfile),
            dataset_states=ModelRepository(store, "dataset_states", DatasetState),
            acquisitions=ModelRepository(store, "acquisitions", AcquisitionRecord),
            scenarios=ModelRepository(store, "scenarios", RotationScenario),
            vegetation=ModelRepository(store, "vegetation", VegetationProfile),
            soil_moisture=ModelRepository(store, "soil_moisture", SoilMoistureProfile),
        )

    def delete_field_data(self, field_id: str) -> None:
        """Cascade delete of everything keyed to a field (stored with parent=field_id or id=field_id)."""
        self.store.delete_children(str(field_id))
        for repo in (self.soil, self.terrain, self.crop_history, self.vegetation, self.soil_moisture):
            repo.delete(str(field_id))
        self.fields.delete(str(field_id))


__all__ = [
    "AcquisitionRecord", "DatasetState", "DocumentStore", "FarmRecord", "ModelRepository", "Repositories",
    "SqliteDocumentStore",
]
