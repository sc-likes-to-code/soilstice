-- SOILSTICE target PostGIS schema — DESIGN ONLY (DATA_ARCHITECTURE §6.9). Not applied in Phase 2.
-- Phase 2 runs on the SQLite document store (app/repositories/store.py). A PostGIS implementation of the
-- repository interfaces should map to these tables. JSONB columns hold contract sub-objects verbatim.

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE dataset_metadata (
  dataset_id          text PRIMARY KEY,
  title               text NOT NULL,
  publisher           text NOT NULL,
  product             text NOT NULL,
  product_version     text NOT NULL,
  doi                 text,
  documentation_url   text NOT NULL,
  verification_status text NOT NULL CHECK (verification_status IN ('LIVE','CMR','DOC','UNVERIFIED','SYNTHETIC')),
  last_verified       date NOT NULL
);

CREATE TABLE acquisition_log (
  acquisition_id          uuid PRIMARY KEY,
  dataset_id              text NOT NULL REFERENCES dataset_metadata,
  request_url             text NOT NULL,
  request_params_redacted jsonb,
  http_status             integer,
  sha256                  char(64),
  bytes                   bigint,
  retrieved_at            timestamptz NOT NULL,
  object_uri              text,
  error_class             text
);

CREATE TABLE farms (
  farm_id    uuid PRIMARY KEY,
  name       text NOT NULL CHECK (length(name) BETWEEN 1 AND 80),
  aoi_id     text NOT NULL CHECK (aoi_id IN ('ks_reno','ks_finney')),
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL
);

CREATE TABLE fields (
  field_id          uuid PRIMARY KEY,
  farm_id           uuid NOT NULL REFERENCES farms ON DELETE CASCADE,
  name              text NOT NULL CHECK (length(name) BETWEEN 1 AND 80),
  geom              geometry(MultiPolygon, 4326) NOT NULL,
  area_ha           double precision NOT NULL CHECK (area_ha > 0 AND area_ha <= 260),
  source            text NOT NULL CHECK (source IN ('csb','user','synthetic')),
  csb_id            text,
  state_fips        char(2) NOT NULL,
  county_fips       char(3) NOT NULL,
  processing_status text NOT NULL CHECK (processing_status IN ('ready','processing','partial','failed')),
  latest_job_id     uuid,
  created_at        timestamptz NOT NULL
);
CREATE INDEX fields_geom_gist ON fields USING gist (geom);
CREATE INDEX fields_farm ON fields (farm_id);

CREATE TABLE processing_jobs (
  job_id     uuid PRIMARY KEY,
  field_id   uuid NOT NULL REFERENCES fields ON DELETE CASCADE,
  status     text NOT NULL CHECK (status IN ('queued','running','succeeded','partial','failed')),
  steps      jsonb NOT NULL,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL
);
CREATE INDEX processing_jobs_field ON processing_jobs (field_id);

CREATE TABLE dataset_states (
  field_id       uuid NOT NULL REFERENCES fields ON DELETE CASCADE,
  dataset_id     text NOT NULL REFERENCES dataset_metadata,
  state          text NOT NULL CHECK (state IN ('available','partial','missing','pending')),
  missing_reason text,
  message        text,
  product_version text,
  temporal_start date,
  temporal_end   date,
  updated_at     timestamptz NOT NULL,
  PRIMARY KEY (field_id, dataset_id)
);

-- Profiles are stored as the contract JSON (SoilProfile, TerrainProfile, CropHistory, ClimateProfile).
CREATE TABLE soil_profiles    (field_id uuid PRIMARY KEY REFERENCES fields ON DELETE CASCADE, payload jsonb NOT NULL);
CREATE TABLE terrain_profiles (field_id uuid PRIMARY KEY REFERENCES fields ON DELETE CASCADE, payload jsonb NOT NULL);
CREATE TABLE crop_histories   (field_id uuid PRIMARY KEY REFERENCES fields ON DELETE CASCADE, payload jsonb NOT NULL);
CREATE TABLE climate_profiles (
  field_id    uuid NOT NULL REFERENCES fields ON DELETE CASCADE,
  season_year integer NOT NULL,
  payload     jsonb NOT NULL,
  PRIMARY KEY (field_id, season_year)
);

-- Row-level observations / indicators (DATA_ARCHITECTURE §6.9); populated when Phase 4 persists indicators.
CREATE TABLE env_observations (
  observation_id uuid PRIMARY KEY,
  field_id       uuid NOT NULL REFERENCES fields ON DELETE CASCADE,
  dataset_id     text NOT NULL REFERENCES dataset_metadata,
  variable       text NOT NULL,
  t_start        date NOT NULL,
  t_end          date NOT NULL,
  value          double precision,           -- NULL = missing; never 0 as a stand-in
  missing_reason text,
  unit           text NOT NULL,
  support_class  char(1) NOT NULL CHECK (support_class IN ('F','S','R')),
  quality        jsonb NOT NULL,
  acquisition_id uuid REFERENCES acquisition_log,
  CHECK ((value IS NULL) = (missing_reason IS NOT NULL)),
  UNIQUE (field_id, dataset_id, variable, t_start, t_end)
);
CREATE INDEX env_obs_lookup ON env_observations (field_id, variable, t_start);

CREATE TABLE indicators (
  indicator_id   text PRIMARY KEY,           -- field_id:key:period_start
  field_id       uuid NOT NULL REFERENCES fields ON DELETE CASCADE,
  key            text NOT NULL,
  value          double precision,
  missing_reason text,
  unit           text NOT NULL,
  support_class  char(1) NOT NULL,
  quality        jsonb NOT NULL,
  method_id      text NOT NULL,
  method_version text NOT NULL,
  input_ids      text[] NOT NULL DEFAULT '{}',
  CHECK ((value IS NULL) = (missing_reason IS NOT NULL))
);

CREATE TABLE rotation_scenarios (
  scenario_id uuid PRIMARY KEY,
  field_id    uuid NOT NULL REFERENCES fields ON DELETE CASCADE,
  name        text NOT NULL,
  start_year  integer NOT NULL,
  sequence    jsonb NOT NULL,
  evaluation  jsonb,
  created_at  timestamptz NOT NULL,
  updated_at  timestamptz NOT NULL
);
CREATE INDEX rotation_scenarios_field ON rotation_scenarios (field_id);

CREATE TABLE crop_kb (
  crop_code      integer PRIMARY KEY,
  name           text NOT NULL,
  family         text NOT NULL,
  is_double_crop boolean NOT NULL,
  kb_version     text NOT NULL,
  thresholds     jsonb NOT NULL                -- every threshold carries a citation (PHASE_0 T19)
);
