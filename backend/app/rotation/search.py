"""Bounded beam search multi-year crop sequence generator (Phase 7 layer 4).

Generates Pareto-optimal, evidence-backed candidate crop rotations over horizons of 2–5 years.
Governed by bounded beam search (width W=50), deterministic tie-breaking, and early constraint pruning.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.contracts import (
    GenerateCandidate,
    ScenarioYear,
)
from app.rotation.evaluator import MultiYearEvaluator
from app.rotation.kb import CDL_TO_CROP_ID, CropKnowledgeBase

# Commercial crops commonly rotated in South-Central and Western Kansas
COMMERCIAL_CANDIDATE_CDL_CODES: list[int] = [
    24,  # Winter Wheat (CRP003)
    4,   # Grain Sorghum (CRP005)
    5,   # Soybean (CRP002)
    1,   # Corn (CRP001)
    27,  # Cereal Rye (CRP009)
    36,  # Alfalfa (CRP011)
    28,  # Oats (CRP010)
    21,  # Barley (CRP008)
    2,   # Cotton (CRP006)
    23,  # Spring Wheat (CRP004)
]


class BoundedBeamSearchGenerator:
    """Generates candidate crop sequences using deterministic bounded beam search."""

    def __init__(self, kb: CropKnowledgeBase, evaluator: MultiYearEvaluator | None = None):
        self.kb = kb
        self.evaluator = evaluator or MultiYearEvaluator(kb)

    def generate(
        self,
        field_id: uuid.UUID,
        horizon: int = 3,
        start_year: int = 2026,
        antecedent_crop_code: int | None = None,
        baseline_suitability: Any | None = None,
        include_cover_crops: bool = True,
        max_candidates: int = 10,
        beam_width: int = 50,
    ) -> list[GenerateCandidate]:
        if horizon < 2:
            horizon = 2
        elif horizon > 5:
            horizon = 5

        # Available crop pool
        candidate_codes = list(COMMERCIAL_CANDIDATE_CDL_CODES)

        # Baseline suitability lookup
        unsuitable_codes: set[int] = set()
        suitability_scores: dict[int, float] = {}
        if baseline_suitability and hasattr(baseline_suitability, "crops"):
            for crop_eval in baseline_suitability.crops:
                cdl = crop_eval.cdl_code
                if cdl is not None:
                    suitability_scores[cdl] = crop_eval.suitability_score or 50.0
                    if crop_eval.suitability_class == "unsuitable":
                        unsuitable_codes.add(cdl)

        # Antecedent crop ID
        antecedent_cid = CDL_TO_CROP_ID.get(antecedent_crop_code) if antecedent_crop_code else None

        # State in beam: (score, sequence_of_crop_codes)
        # Initialize beam at step 0
        beam: list[tuple[float, list[int]]] = [(0.0, [])]

        for step in range(horizon):
            candidates_next: list[tuple[float, list[int]]] = []

            for cum_score, prefix in beam:
                prev_code = prefix[-1] if prefix else antecedent_crop_code
                prev_cid = CDL_TO_CROP_ID.get(prev_code) if prev_code else None

                for code in candidate_codes:
                    # Constraint 1: Prune crops that are environmentally unsuitable on this field
                    if code in unsuitable_codes:
                        continue

                    cid = CDL_TO_CROP_ID.get(code)
                    if not cid:
                        continue

                    # Constraint 2: Prune prolonged monoculture (run >= 3)
                    # Check prefix run
                    run_len = 1
                    for p in reversed(prefix):
                        if p == code:
                            run_len += 1
                        else:
                            break
                    if run_len == 1 and not prefix and antecedent_crop_code == code:
                        run_len = 2

                    if run_len >= 3:
                        continue

                    # Transition scoring
                    step_score = 0.0

                    # 1. Base suitability score (0..100 -> normalized to 0..20)
                    base_suit = suitability_scores.get(code, 60.0)
                    step_score += base_suit * 0.2

                    # 2. Directed transition synergy
                    if prev_cid:
                        rot = self.kb.get_rotation(prev_cid, cid)
                        if rot:
                            if rot.compatibility_rating == "highly_compatible":
                                step_score += 15.0
                            elif rot.compatibility_rating == "compatible":
                                step_score += 8.0
                            elif rot.compatibility_rating == "caution_conditional":
                                step_score -= 10.0
                    elif prev_code is None and step == 0:
                        # Neutral antecedent
                        step_score += 5.0

                    # 3. Monoculture penalty (repeating immediately previous crop)
                    if prev_code == code:
                        step_score -= 25.0

                    # 4. Botanical family diversity bonus
                    profile = self.kb.get_crop_by_id(cid)
                    fam = profile.crop_identity.get("botanical_family") if profile else None
                    existing_families = {
                        self.kb.get_crop_by_id(CDL_TO_CROP_ID.get(p, "")).crop_identity.get("botanical_family")
                        for p in prefix
                        if CDL_TO_CROP_ID.get(p) and self.kb.get_crop_by_id(CDL_TO_CROP_ID.get(p, ""))
                    }
                    if fam and fam not in existing_families and prefix:
                        step_score += 12.0

                    # Consecutive same-family penalty (e.g. 3 consecutive Poaceae)
                    same_fam_run = 1
                    for p in reversed(prefix):
                        p_cid = CDL_TO_CROP_ID.get(p)
                        p_prof = self.kb.get_crop_by_id(p_cid) if p_cid else None
                        p_fam = p_prof.crop_identity.get("botanical_family") if p_prof else None
                        if p_fam == fam and fam is not None:
                            same_fam_run += 1
                        else:
                            break
                    if same_fam_run >= 3:
                        step_score -= 15.0

                    candidates_next.append((cum_score + step_score, prefix + [code]))

            # Prune to beam width with deterministic tie-breaking
            # Sort by: -score, distinct_crops, distinct_families, tuple of codes
            def _sort_key(item: tuple[float, list[int]]):
                score, seq = item
                distinct_crops = len(set(seq))
                fams = set()
                for c in seq:
                    c_id = CDL_TO_CROP_ID.get(c)
                    if c_id:
                        pr = self.kb.get_crop_by_id(c_id)
                        if pr:
                            fams.add(pr.crop_identity.get("botanical_family"))
                return (-score, -distinct_crops, -len(fams), seq)

            candidates_next.sort(key=_sort_key)
            beam = candidates_next[:beam_width]

        if not beam:
            # Fallback default sequence if all candidate combinations were pruned
            fallback_seq = [24, 4, 5][:horizon]
            beam = [(50.0, fallback_seq)]

        # Convert top K unique sequences to GenerateCandidate
        generated: list[GenerateCandidate] = []
        seen_seqs: set[tuple[int, ...]] = set()

        for score, crop_codes in beam:
            seq_tuple = tuple(crop_codes)
            if seq_tuple in seen_seqs:
                continue
            seen_seqs.add(seq_tuple)

            scenario_years = [
                ScenarioYear(
                    year=start_year + idx,
                    crop_code=code,
                    crop_name=self.kb.crop_name(code) or f"Crop {code}",
                )
                for idx, code in enumerate(crop_codes)
            ]

            evaluation = self.evaluator.evaluate(
                sequence=scenario_years,
                field_id=field_id,
                baseline_suitability=baseline_suitability,
                antecedent_crop=antecedent_crop_code,
            )

            # Build human-readable descriptive name (e.g. "Wheat – Sorghum – Soybean")
            names = [y.crop_name.split("(")[0].strip() for y in scenario_years]
            seq_name = " – ".join(names)

            generated.append(
                GenerateCandidate(
                    rank=len(generated) + 1,
                    name=seq_name,
                    sequence=scenario_years,
                    evaluation=evaluation,
                )
            )

            if len(generated) >= max_candidates:
                break

        return compute_pareto_dominance(generated)


def compute_pareto_dominance(
    candidates: list[GenerateCandidate],
) -> list[GenerateCandidate]:
    """Computes Pareto dominance frontiers across the 4 agronomic evaluation dimensions.

    Dimension scoring: suitable = 2, marginal = 1, unsuitable = 0, unknown = 0.
    A dominates B iff A >= B on all 4 dimensions and A > B on at least one.
    Assigns pareto_rank (1 = nondominated frontier, 2 = second frontier, etc.)
    and is_pareto_optimal = (pareto_rank == 1).
    """
    if not candidates:
        return candidates

    band_scores = {"suitable": 2, "marginal": 1, "unsuitable": 0, "unknown": 0}
    dim_keys = ["agronomic_fit", "rotation_benefit", "water_risk", "diversity"]
    vectors: list[tuple[int, tuple[int, ...]]] = []

    for idx, cand in enumerate(candidates):
        d_map = {d.key: band_scores.get(d.band, 0) for d in cand.evaluation.dimensions}
        v = tuple(d_map.get(k, 0) for k in dim_keys)
        vectors.append((idx, v))

    n = len(candidates)
    dominated_by = [0] * n
    dominates: list[list[int]] = [[] for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            vi = vectors[i][1]
            vj = vectors[j][1]
            ge = all(x >= y for x, y in zip(vi, vj))
            gt = any(x > y for x, y in zip(vi, vj))
            if ge and gt:
                dominates[i].append(j)
                dominated_by[j] += 1

    current_front = [i for i in range(n) if dominated_by[i] == 0]
    ranks = [1] * n
    front_num = 1

    while current_front:
        next_front = []
        for i in current_front:
            ranks[i] = front_num
            for j in dominates[i]:
                dominated_by[j] -= 1
                if dominated_by[j] == 0:
                    next_front.append(j)
        if next_front:
            front_num += 1
        current_front = next_front

    updated: list[GenerateCandidate] = []
    for idx, cand in enumerate(candidates):
        is_opt = (ranks[idx] == 1)
        rank_val = ranks[idx]

        if is_opt:
            v = vectors[idx][1]
            if all(x == 2 for x in v):
                explanation = "Pareto Nondominated (Frontier 1): Achieves maximum suitability across all 4 evaluation dimensions."
            else:
                explanation = "Pareto Nondominated (Frontier 1): Optimal multi-objective trade-off; no candidate dominates this sequence across all dimensions."
        else:
            dominators = [d_idx for d_idx in range(n) if idx in dominates[d_idx]]
            best_dom = dominators[0] if dominators else 0
            explanation = f"Pareto Dominated (Frontier {rank_val}): Outperformed across evaluated dimensions by sequence #{candidates[best_dom].rank}."

        updated.append(
            cand.model_copy(
                update={
                    "is_pareto_optimal": is_opt,
                    "pareto_rank": rank_val,
                    "pareto_explanation": explanation,
                }
            )
        )

    return updated
