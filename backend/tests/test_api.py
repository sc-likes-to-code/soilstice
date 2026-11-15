"""API behaviour E1–E27 with synthetic fake providers (no network)."""

from __future__ import annotations

import uuid

from app.contracts import ApiErrorResponse, ApiResponse, FieldProfile
from app.providers.http import ProviderError
from app.services.container import Providers

from .conftest import FakeCdl, FakePower, FakeSrtm, FakeSsurgo, create_reno_field, reno_farm_id

API = "/api/v1"


def assert_error(resp, status, code):
    assert resp.status_code == status, resp.text
    body = ApiErrorResponse.model_validate(resp.json())
    assert body.error.code == code
    assert body.error.request_id.startswith("req_")
    return body


def test_health_and_envelope(client):
    r = client.get(f"{API}/health")
    assert r.status_code == 200
    body = r.json()
    assert body["data"] == {"status": "ok", "contract_version": "1.0.0-phase0"}
    assert body["meta"]["data_mode"] == "live" and body["meta"]["api_version"] == "v1"
    assert r.headers["X-Request-ID"] == body["meta"]["request_id"]


def test_datasets_register(client):
    data = client.get(f"{API}/datasets").json()["data"]
    integrated = {d["dataset_id"] for d in data if d["integration_status"] == "integrated"}
    assert integrated == {"nasa_power_daily_ag", "usda_nrcs_ssurgo_sda", "usda_nass_cdl", "nasa_srtm_gl1", "meteomatics"}
    assert len(data) == 15


def test_crops_fallback_without_kb(client):
    crops = client.get(f"{API}/crops").json()["data"]
    assert {c["crop_code"] for c in crops} == {1, 4, 5, 24, 26, 36, 61, 236}
    assert all(c["kb_version"] == "none" for c in crops)


def test_farms_seeded_and_rename(client):
    farms = client.get(f"{API}/farms").json()["data"]
    assert {f["aoi"]["aoi_id"] for f in farms} == {"ks_reno", "ks_finney"}
    fid = reno_farm_id(client)
    r = client.patch(f"{API}/farms/{fid}", json={"name": "Renamed"})
    assert r.status_code == 200 and r.json()["data"]["name"] == "Renamed"
    assert_error(client.patch(f"{API}/farms/{fid}", json={"name": ""}), 422, "VALIDATION_ERROR")
    assert_error(client.get(f"{API}/farms/{uuid.uuid4()}"), 404, "NOT_FOUND")


def test_create_field_runs_full_pipeline(client):
    r = create_reno_field(client)
    assert r.status_code == 202, r.text
    data = r.json()["data"]
    field, job = data["field"], data["job"]
    assert field["source"] == "user" and field["editable"] is True
    assert field["state_fips"] == "20" and field["county_fips"] == "155"
    assert 95 < field["area"]["value"] < 100 and field["area"]["unit"] == "ha"
    # inline execution => job finished before the response
    # CDL is partial because the fake provider reports 2006 as OUT_OF_TEMPORAL_RANGE
    assert [s["status"] for s in job["steps"]] == ["succeeded", "partial", "succeeded", "succeeded"], job
    assert job["status"] == "partial"
    fid = field["field_id"]

    assert client.get(f"{API}/jobs/{job['job_id']}").json()["data"]["status"] == "partial"
    assert client.get(f"{API}/fields/{fid}").json()["data"]["processing_status"] == "partial"

    profile = FieldProfile.model_validate(client.get(f"{API}/fields/{fid}/profile").json()["data"])
    assert profile.soil and profile.terrain and profile.crop_history
    assert profile.coverage.completeness == 0.625  # 8 applicable P0 rows (5 available/partial including meteomatics)
    statuses = {d.dataset_id: d.status for d in profile.coverage.datasets}
    assert statuses["usda_nass_csb"] == "not_applicable"
    assert statuses["nasa_hls_vi"] == "not_integrated" and statuses["nasa_smap_spl4smgp"] == "not_integrated"
    assert {statuses[k] for k in ("usda_nrcs_ssurgo_sda", "nasa_power_daily_ag", "nasa_srtm_gl1")} == {"available"}
    assert statuses["usda_nass_cdl"] == "partial"  # 2006 out of range in the fake
    assert profile.resilience.status == "computed" and profile.resilience.composite.score.value is not None

    summaries = client.get(f"{API}/farms/{reno_farm_id(client)}/fields").json()["data"]
    assert summaries[0]["latest_crop"]["year"] == 2010 and summaries[0]["resilience_band"] == "unknown"


def test_power_values_are_regional_context(client):
    fid = create_reno_field(client).json()["data"]["field"]["field_id"]
    climate = client.get(f"{API}/fields/{fid}/climate", params={"season_year": 2024}).json()["data"]
    assert climate["authoritative_source"] == {"precipitation": "nasa_power_daily_ag",
                                               "temperature": "nasa_power_daily_ag"}
    for s in climate["series"]:
        assert s["spatial"]["support_class"] == "R" and s["spatial"]["extraction_method"] == "api_point_query"
    precip = next(i for i in climate["indicators"] if i["key"] == "precip_total_season")
    assert precip["value"] == {"value": 732.0, "unit": "mm", "uncertainty": None, "missing_reason": None}  # 366 × 2
    gdd = next(i for i in climate["indicators"] if i["key"] == "gdd_season")
    assert gdd["value"]["value"] == 1464.0 and gdd["value"]["unit"] == "degC_day"
    anom = next(i for i in climate["indicators"] if i["key"] == "precip_anomaly_pct")
    assert anom["value"]["value"] == -3.75 and anom["value"]["unit"] == "percent"
    heat = next(i for i in climate["indicators"] if i["key"] == "heat_stress_days")
    assert heat["value"]["value"] == 0.0 and heat["value"]["unit"] == "day"
    frost = next(i for i in climate["indicators"] if i["key"] == "frost_free_days")
    assert frost["value"]["value"] == 366.0 and frost["value"]["unit"] == "day"
    sm = next(i for i in climate["indicators"] if i["key"] == "sm_rootzone_mean_season")
    assert sm["value"]["missing_reason"] in ("NO_DATA_SOURCE", None)


def test_climate_with_crop_code_flags_season_window(client):
    fid = create_reno_field(client).json()["data"]["field"]["field_id"]
    c = client.get(f"{API}/fields/{fid}/climate", params={"season_year": 2023, "crop_code": 24}).json()["data"]
    assert c["season"]["crop_code"] == 24
    assert "SEASON_WINDOW_UNAVAILABLE" in {f["code"] for f in c["quality"]["flags"]}
    assert_error(client.get(f"{API}/fields/{fid}/climate"), 422, "VALIDATION_ERROR")  # season_year required


def test_geometry_validation_errors(client):
    open_ring = [[[[-98.05, 37.95], [-98.04, 37.95], [-98.04, 37.96], [-98.05, 37.96]]]]
    assert_error(create_reno_field(client, coords=open_ring), 422, "GEOMETRY_INVALID")
    bowtie = [[[[-98.05, 37.95], [-98.04, 37.96], [-98.04, 37.95], [-98.05, 37.96], [-98.05, 37.95]]]]
    assert_error(create_reno_field(client, coords=bowtie), 422, "GEOMETRY_INVALID")
    finney = [[[[-100.7, 38.0], [-100.69, 38.0], [-100.69, 38.01], [-100.7, 38.01], [-100.7, 38.0]]]]
    assert_error(create_reno_field(client, coords=finney), 422, "OUTSIDE_AOI")
    huge = [[[[-98.1, 37.9], [-98.0, 37.9], [-98.0, 38.0], [-98.1, 38.0], [-98.1, 37.9]]]]
    body = assert_error(create_reno_field(client, coords=huge), 422, "FIELD_TOO_LARGE")
    assert body.error.details["max_ha"] == 260
    r = client.post(f"{API}/farms/{reno_farm_id(client)}/fields", json={"geometry": {"type": "Polygon"}})
    assert_error(r, 422, "VALIDATION_ERROR")


def test_provider_failure_is_isolated(client_factory, tmp_path):
    providers = Providers(power=FakePower(fail=ProviderError("POWER down", "UPSTREAM_ERROR")),
                          ssurgo=FakeSsurgo(fail=ProviderError("No map units", "NO_DATA_SOURCE")),
                          cdl=FakeCdl(tmp_path), srtm=FakeSrtm(tmp_path, configured=False))
    c, _ = client_factory(providers)
    with c:
        data = create_reno_field(c).json()["data"]
        job, fid = data["job"], data["field"]["field_id"]
        steps = {s["dataset_id"]: s for s in job["steps"]}
        assert job["status"] == "partial"
        assert steps["usda_nrcs_ssurgo_sda"]["missing_reason"] == "NO_DATA_SOURCE"
        assert steps["nasa_power_daily_ag"]["status"] == "failed"
        assert steps["meteomatics"]["missing_reason"] == "NOT_COMPUTED"
        assert steps["usda_nass_cdl"]["status"] == "partial"
        assert c.get(f"{API}/fields/{fid}").json()["data"]["processing_status"] == "partial"

        soil = c.get(f"{API}/fields/{fid}/soil").json()["data"]
        assert soil["quality"]["status"] == "missing" and soil["aws_0_150"]["missing_reason"] == "NO_DATA_SOURCE"
        assert all(layer["clay_pct"]["value"] is None for layer in soil["layers"])
        terrain = c.get(f"{API}/fields/{fid}/terrain").json()["data"]
        assert terrain["elevation_mean"] == {"value": None, "unit": "m", "uncertainty": None,
                                             "missing_reason": "NOT_COMPUTED"}
        climate = c.get(f"{API}/fields/{fid}/climate", params={"season_year": 2024}).json()["data"]
        assert climate["series"] == [] and climate["quality"]["status"] == "missing"
        profile = c.get(f"{API}/fields/{fid}/profile").json()["data"]
        assert profile["soil"] is None and profile["crop_history"] is not None
        cov = {d["dataset_id"]: d for d in profile["coverage"]["datasets"]}
        assert cov["meteomatics"]["status"] == "missing"
        overview = c.get(f"{API}/farms/{reno_farm_id(c)}/overview").json()["data"]
        assert "EARTHDATA_NOT_CONFIGURED" in {a["code"] for a in overview["alerts"]}


def test_delete_field_and_not_editable(client):
    data = create_reno_field(client).json()["data"]
    fid = data["field"]["field_id"]
    sc = client.post(f"{API}/fields/{fid}/scenarios", json={"name": "s", "start_year": 2026, "sequence": [
        {"year": 2026, "crop_code": 24}, {"year": 2027, "crop_code": 4}]})
    assert sc.status_code == 201
    r = client.delete(f"{API}/fields/{fid}")
    assert r.status_code == 200 and r.json()["data"] == {"deleted": True}
    assert_error(client.get(f"{API}/fields/{fid}"), 404, "NOT_FOUND")
    assert_error(client.get(f"{API}/jobs/{data['job']['job_id']}"), 404, "NOT_FOUND")
    upsert = {"name": "s", "start_year": 2026, "sequence": [{"year": 2026, "crop_code": 24}, {"year": 2027, "crop_code": 4}]}
    assert_error(client.put(f"{API}/scenarios/{sc.json()['data']['scenario_id']}", json=upsert), 404, "NOT_FOUND")

    # a non-user (CSB) field is not editable
    container = client.app.state.container
    fid2 = create_reno_field(client).json()["data"]["field"]["field_id"]
    f = container.repos.fields.get(fid2)
    container.repos.fields.put(fid2, f.model_copy(update={"source": "csb", "editable": False}), parent=f.farm_id)
    assert_error(client.delete(f"{API}/fields/{fid2}"), 409, "NOT_EDITABLE")


def test_scenarios_crud_and_validation(client):
    fid = create_reno_field(client).json()["data"]["field"]["field_id"]
    body = {"name": "Wheat-sorghum", "start_year": 2026,
            "sequence": [{"year": 2026, "crop_code": 24}, {"year": 2027, "crop_code": 4}]}
    sc = client.post(f"{API}/fields/{fid}/scenarios", json=body).json()["data"]
    assert sc["sequence"][1]["crop_name"] == "Sorghum"
    assert sc["evaluation"]["overall"] == "unknown" and sc["evaluation"]["kb_version"] == "none"
    assert {d["band"] for d in sc["evaluation"]["dimensions"]} == {"unknown"}

    body["sequence"].append({"year": 2028, "crop_code": 5})
    up = client.put(f"{API}/scenarios/{sc['scenario_id']}", json=body)
    assert up.status_code == 200 and len(up.json()["data"]["sequence"]) == 3
    assert len(client.get(f"{API}/fields/{fid}/scenarios").json()["data"]) == 1

    bad = assert_error(client.post(f"{API}/fields/{fid}/scenarios", json={
        "name": "x", "start_year": 2026, "sequence": [{"year": 2026, "crop_code": 999}, {"year": 2030, "crop_code": 1}]}),
        422, "VALIDATION_ERROR")
    kinds = {e["error"] for e in bad.error.details["errors"]}
    assert kinds == {"unknown crop code", "years must be consecutive starting at start_year"}

    assert client.delete(f"{API}/scenarios/{sc['scenario_id']}").json()["data"] == {"deleted": True}
    assert_error(client.delete(f"{API}/scenarios/{sc['scenario_id']}"), 404, "NOT_FOUND")


def test_recommendation_is_insufficient_data(client):
    fid = create_reno_field(client).json()["data"]["field"]["field_id"]
    rec = client.get(f"{API}/fields/{fid}/recommendations", params={"season_year": 2026}).json()["data"]
    assert rec["status"] == "insufficient_data" and rec["candidates"] == []
    assert "Not a yield or profit forecast." in rec["disclaimers"]


def test_soil_terrain_crop_history_values(client):
    fid = create_reno_field(client).json()["data"]["field"]["field_id"]
    soil = client.get(f"{API}/fields/{fid}/soil").json()["data"]
    assert soil["spatial"]["support_class"] == "F" and soil["method"]["method_id"] == "ssurgo_area_comppct_weighting"
    assert "PROVISIONAL_NULL_WEIGHT_RULE" in {f["code"] for f in soil["quality"]["flags"]}
    terrain = client.get(f"{API}/fields/{fid}/terrain").json()["data"]
    assert 1.5 < terrain["slope_mean_pct"]["value"] < 3.5
    hist = client.get(f"{API}/fields/{fid}/crop-history").json()["data"]
    assert [y["year"] for y in hist["years"]] == list(range(2006, 2011))
    assert hist["years"][0]["missing_reason"] == "OUT_OF_TEMPORAL_RANGE" and hist["years"][0]["histogram"] == []
    y2007 = hist["years"][1]
    assert y2007["majority"] == {"crop_code": 24, "crop_name": "Winter Wheat"} and 0.6 < y2007["purity"] < 1
    metrics = {m["key"]: m["value"]["value"] for m in hist["metrics"]}
    assert metrics["distinct_crops"] == 2
    assert metrics["max_monoculture_run"] == 1
    assert metrics["rotation_shannon"] == 0.693


def test_vegetation_indicators_resilience_evidence(client):
    fid = create_reno_field(client).json()["data"]["field"]["field_id"]
    veg = client.get(f"{API}/fields/{fid}/vegetation", params={"year": 2024}).json()["data"]
    assert len(veg["scenes"]) > 0 and veg["spatial"]["support_class"] == "R"
    assert_error(client.get(f"{API}/fields/{fid}/vegetation", params={"year": 2024, "index": "BAD"}), 422,
                 "VALIDATION_ERROR")

    soil_inds = client.get(f"{API}/fields/{fid}/indicators", params={"category": "soil"}).json()["data"]
    assert {i["key"] for i in soil_inds} == {"aws_0_150", "ph_0_30", "om_0_30", "clay_0_30"}
    all_inds = client.get(f"{API}/fields/{fid}/indicators").json()["data"]
    assert len({i["indicator_id"] for i in all_inds}) == len(all_inds)

    res = client.get(f"{API}/fields/{fid}/resilience").json()["data"]
    assert res["status"] == "computed" and len(res["components"]) == 5
    assert res["composite"]["components_used"] == 4
    assert res["composite"]["score"]["value"] is not None

    ev = client.get(f"{API}/fields/{fid}/evidence").json()["data"]
    assert {e["kind"] for e in ev} >= {"dataset", "method", "indicator"}
    only = client.get(f"{API}/fields/{fid}/evidence", params={"kind": "method"}).json()["data"]
    assert only and {e["kind"] for e in only} == {"method"}
    rel = client.get(f"{API}/fields/{fid}/evidence", params={"related_id": "usda_nass_cdl"}).json()["data"]
    assert rel and all("usda_nass_cdl" in e["related_ids"] for e in rel)


def test_every_response_validates_against_contract_models(client):
    """Round-trip each endpoint's payload through the Pydantic response model."""
    from app.main import create_app

    fid = create_reno_field(client).json()["data"]["field"]["field_id"]
    schema_paths = create_app().openapi()["paths"]
    gets = [p for p, v in schema_paths.items() if "get" in v]
    assert len(gets) == 31
    for path in [
        f"/fields/{fid}/profile",
        f"/fields/{fid}/coverage",
        f"/fields/{fid}/suitability",
        "/datasets",
        "/crops",
        "/canonical-crops",
        "/kb/metadata",
    ]:
        r = client.get(API + path)
        assert r.status_code == 200
        ApiResponse.model_validate(r.json())


def test_rate_limit(client_factory, fake_providers):
    c, _ = client_factory(fake_providers, rate_limit_writes_per_minute=2)
    with c:
        fid = reno_farm_id(c)
        assert c.patch(f"{API}/farms/{fid}", json={"name": "a"}).status_code == 200
        assert c.patch(f"{API}/farms/{fid}", json={"name": "b"}).status_code == 200
        assert_error(c.patch(f"{API}/farms/{fid}", json={"name": "c"}), 429, "RATE_LIMITED")
        assert c.get(f"{API}/farms").status_code == 200  # reads are not limited


def test_unknown_route_uses_error_envelope(client):
    assert_error(client.get(f"{API}/nope"), 404, "NOT_FOUND")
