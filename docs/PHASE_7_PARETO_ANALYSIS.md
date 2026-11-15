# SOILSTICE — Phase 7 Genuine Pareto Nondominated Candidate Analysis

**Author**: Antigravity Autonomous Agent (Google DeepMind)  
**Date**: November 15, 2026  
**Status**: COMPLETE / VERIFIED  
**Workspaces**: `C:\My D Drive\My_Projects\Soilstice_Updated`  
**Applicable Architecture**: Phase 7 Layer 4 Multi-Year Rotation Intelligence (`search.py`, `evaluator.py`, `rotation-view.tsx`).

---

## 1. Overview & Problem Definition

In agricultural multi-year crop rotation planning, growers face multiple competing objectives that cannot be collapsed into a single scalar score without imposing subjective trade-offs. 

SOILSTICE evaluates multi-year sequences along four orthogonal agronomic dimensions:
1. **Agronomic Fit ($d_1$)**: Biophysical suitability on the specific soil, terrain, and climate.
2. **Rotation Benefit ($d_2$)**: Directed pairwise compatibility (EV0001–EV0212), disease break potential, and weed suppression.
3. **Water Risk ($d_3$)**: Subsoil moisture conservation and avoidance of excessive consecutive high-water demand crops.
4. **Diversity ($d_4$)**: Taxonomic family richness and functional complementarity over time.

While the existing `BoundedBeamSearchGenerator` ranks candidate sequences using a composite heuristic score ($Score(S) = 0.2 \cdot \text{base\_suit} + \text{synergy} + \text{diversity\_bonus} - \text{penalties}$), agricultural decision-makers need to know **which candidates are Pareto optimal (nondominated)**—meaning no other candidate performs better across all four dimensions simultaneously.

---

## 2. Mathematical Formulation of Multi-Objective Pareto Dominance

Let each generated candidate $i \in \{1, \dots, N\}$ be evaluated by `MultiYearEvaluator` to produce an objective vector $\mathbf{V}_i = (v_{i, 1}, v_{i, 2}, v_{i, 3}, v_{i, 4}) \in \mathbb{R}^4$, mapped from qualitative fit bands:

$$\text{score}(band) = \begin{cases} 
2 & \text{if } band = \text{"suitable"} \\ 
1 & \text{if } band = \text{"marginal"} \\ 
0 & \text{if } band \in \{\text{"unsuitable"}, \text{"unknown"}\} 
\end{cases}$$

### 2.1 Pareto Dominance Relation
Candidate $A$ **strictly dominates** candidate $B$ (denoted $A \succ B$) if and only if:
$$\forall d \in \{1, 2, 3, 4\}: v_{A, d} \ge v_{B, d} \quad \land \quad \exists d \in \{1, 2, 3, 4\}: v_{A, d} > v_{B, d}$$

In plain terms: $A$ is at least as good as $B$ in every evaluation dimension, and strictly better than $B$ in at least one dimension.

### 2.2 Pareto Nondominated Frontier (Rank 1)
A candidate $A$ is **Pareto nondominated** (Pareto optimal) within the candidate pool $\mathcal{C}$ if no candidate in $\mathcal{C}$ dominates it:
$$A \in \mathcal{P} \iff \nexists B \in \mathcal{C}: B \succ A$$

### 2.3 Fast Non-dominated Sorting Algorithm
Following the standard NSGA-II sorting algorithm (Deb et al., 2002):
1. For each candidate $i$, maintain:
   - $n_i$: Domination count (number of candidates that dominate $i$).
   - $S_i$: Set of candidates that $i$ dominates.
2. All candidates with $n_i = 0$ belong to **Frontier 1** (`pareto_rank = 1`, `is_pareto_optimal = True`).
3. For each candidate $i$ in Frontier 1, decrement $n_j$ for each $j \in S_i$. If $n_j$ reaches 0, $j$ enters **Frontier 2** (`pareto_rank = 2`, `is_pareto_optimal = False`).
4. This iteration repeats until all candidates are assigned to discrete Pareto frontiers.

---

## 3. Implementation in Bounded Beam Search

The Pareto analysis was integrated directly into `backend/app/rotation/search.py` via `compute_pareto_dominance`:

```python
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
            vi, vj = vectors[i][1], vectors[j][1]
            if all(x >= y for x, y in zip(vi, vj)) and any(x > y for x, y in zip(vi, vj)):
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
...
```

### 3.1 Explainability
Each candidate receives a deterministic, human-readable `pareto_explanation`:
- For **Pareto Nondominated** sequences:
  - *Frontier 1 (Full Suite)*: `"Pareto Nondominated (Frontier 1): Achieves maximum suitability across all 4 evaluation dimensions."`
  - *Frontier 1 (Trade-off)*: `"Pareto Nondominated (Frontier 1): Optimal multi-objective trade-off; no candidate dominates this sequence across all dimensions."`
- For **Dominated** sequences:
  - *Frontier 2+*: `"Pareto Dominated (Frontier {rank}): Outperformed across evaluated dimensions by sequence #{dominator_rank}."`

---

## 4. Empirical Results on Real Field: Audit Reno Field

Executing `POST /api/v1/fields/4e0f055e-12f1-427b-97ff-d8815be858fb/rotations/generate` with `horizon = 3`, `max_candidates = 15` produced the following empirical Pareto distribution:

| Rank | Sequence Name | Agronomic Fit | Rotation Benefit | Water Risk | Diversity | Pareto Status | Frontier | Dominator |
|---|---|---|---|---|---|---|---|---|
| **#1** | Soybean – Grain Sorghum – Cotton | suitable | suitable | suitable | suitable | **Nondominated** | 1 | — |
| **#2** | Soybean – Cereal Rye – Cotton | suitable | suitable | suitable | suitable | **Nondominated** | 1 | — |
| **#3** | Soybean – Winter Wheat – Cotton | suitable | suitable | suitable | suitable | **Nondominated** | 1 | — |
| **#4** | Cotton – Grain Sorghum – Soybean | suitable | suitable | suitable | suitable | **Nondominated** | 1 | — |
| **#5** | Cereal Rye – Cotton – Soybean | suitable | suitable | suitable | suitable | **Nondominated** | 1 | — |
| **#6** | Cotton – Cereal Rye – Soybean | suitable | suitable | suitable | suitable | **Nondominated** | 1 | — |
| **#7** | Cotton – Corn – Soybean | **marginal** | suitable | suitable | suitable | **Dominated** | 2 | #1 |
| **#8** | Soybean – Corn – Cotton | **marginal** | suitable | suitable | suitable | **Dominated** | 2 | #1 |
| **#9** | Alfalfa – Cotton – Grain Sorghum | **marginal** | suitable | suitable | suitable | **Dominated** | 2 | #1 |
| **#10** | Alfalfa – Grain Sorghum – Cotton | **marginal** | suitable | suitable | suitable | **Dominated** | 2 | #1 |
| **#11** | Alfalfa – Cotton – Cereal Rye | **marginal** | suitable | suitable | suitable | **Dominated** | 2 | #1 |
| **#12** | Oats – Alfalfa – Cotton | **marginal** | suitable | suitable | suitable | **Dominated** | 2 | #1 |
| **#13** | Soybean – Winter Wheat – Sorghum | suitable | suitable | suitable | suitable | **Nondominated** | 1 | — |
| **#14** | Soybean – Winter Wheat – Rye | suitable | suitable | suitable | suitable | **Nondominated** | 1 | — |
| **#15** | Cereal Rye – Soybean – Wheat | suitable | suitable | suitable | suitable | **Nondominated** | 1 | — |

### Agronomic Analysis of Dominance
- Candidate #7 (`Cotton – Corn – Soybean`) is dominated by Candidate #1 (`Soybean – Grain Sorghum – Cotton`). Why?
  Because Candidate #1 achieves `suitable` on **all 4 dimensions**, while Candidate #7 has `marginal` agronomic fit due to Corn's sensitivity to antecedent rotation conditions and thermal stress on this field.
  Candidate #1 is strictly superior in Agronomic Fit while matching Candidate #7 in Rotation Benefit, Water Risk, and Diversity.
- Candidates featuring Alfalfa (e.g. #9–#12) enter Frontier 2 because Alfalfa is conditionally suitable on this parcel and requires deep rooting moisture recharge.

---

## 5. UI Integration & Visual Presentation

In `src/components/views/rotation-view.tsx`, the Pareto frontier status is surfaced through:
1. **Frontier Badges**:
   - `★ Pareto Nondominated`: Highlighted with an emerald pill badge (`bg-emerald-50 text-emerald-800 border-emerald-300`).
   - `Frontier #2`: Neutral gray pill badge indicating secondary frontier status.
2. **Contextual Trade-off Tooltip & Callout**:
   - The card displays the precise mathematical explanation explaining why the sequence is optimal or which higher-ranking candidate outperforms it.
3. **Total Frontier Count**:
   - The generator summary header indicates `pareto_optimal_count` (e.g., *"9 of 15 candidates are Pareto nondominated"*), guiding growers towards high-value multi-objective options.

---

## 6. Verification & Change Control Invariants

- **Non-disruptive**: Bounded beam search ranking ($Score(S)$) and candidate ordering remain 100% preserved. Pareto dominance is evaluated post-generation to enrich candidates with objective frontier labels.
- **Contract Compliant**: Both backend Pydantic models and frontend TypeScript interfaces match OpenAPI 3.1 specifications validated by `npm run contract:check`.
- **Zero Hallucination**: Dominance is computed strictly over the four evaluated dimensions without fabricated economic or yield claims.
