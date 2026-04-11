"""
interval_tds_solver.py
======================
Interval Vertex Deletion (IVD) modulator finder +
Minimum Total Dominating Set (TDS) FPT solver for Almost-Interval Graphs.

Used by pipeline.py for the "Almost Interval Graph" branch.
"""

import itertools
from collections import defaultdict, deque


# ===========================================================================
# SECTION 1: Graph Utilities
# ===========================================================================

def symmetrize(adj):
    """Ensure adjacency dict represents an undirected graph."""
    sym = defaultdict(set)
    for u, nbrs in adj.items():
        sym[u].update(nbrs)
        for v in nbrs:
            sym[v].add(u)
    return dict(sym)


def nx_to_adj(G_nx):
    """Convert a networkx.Graph to an adjacency dict {node: set(neighbours)}."""
    return {u: set(G_nx.neighbors(u)) for u in G_nx.nodes()}


# ===========================================================================
# SECTION 2: Interval Vertex Deletion (IVD) Modulator
# ===========================================================================

def _check_interval_and_get_obstruction(adj, vertices):
    """
    Check whether G[vertices] is an interval graph.

    Returns
    -------
    (True, None)       — G[vertices] is an interval graph
    (False, vertex)    — vertex is part of a chordality / AT obstruction
    """
    vlist = list(vertices)
    n = len(vlist)
    if n <= 2:
        return True, None

    vset = set(vertices)
    loc = {v: adj.get(v, set()) & vset for v in vlist}

    # ── Step 1: Lex-BFS chordality check ─────────────────────────────────────
    label    = {v: [] for v in vlist}
    visited  = set()
    order    = []
    remaining = set(vlist)

    for _ in range(n):
        v = max(remaining - visited, key=lambda x: label[x])
        visited.add(v)
        order.append(v)
        for u in loc[v] - visited:
            label[u] = label[u] + [n - len(order)]

    pos = {v: i for i, v in enumerate(order)}
    for i, v in enumerate(order):
        later_nbrs = [u for u in loc[v] if pos[u] > i]
        if later_nbrs:
            pivot = min(later_nbrs, key=lambda u: pos[u])
            for u in later_nbrs:
                if u != pivot and u not in loc[pivot]:
                    return False, v   # chordality violation

    # ── Step 2: Asteroidal Triple (AT) check ─────────────────────────────────
    def path_avoiding(src, dst, forbidden):
        if src in forbidden or dst in forbidden:
            return False
        queue, seen = deque([src]), {src}
        while queue:
            cur = queue.popleft()
            if cur == dst:
                return True
            for nb in loc[cur] - seen - forbidden:
                seen.add(nb)
                queue.append(nb)
        return False

    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                u, v, w = vlist[i], vlist[j], vlist[k]
                if (path_avoiding(v, w, loc[u] | {u}) and
                        path_avoiding(u, w, loc[v] | {v}) and
                        path_avoiding(u, v, loc[w] | {w})):
                    # AT found — return the highest-degree vertex as obstruction
                    return False, max([u, v, w], key=lambda x: len(loc[x]))

    return True, None


def extract_ivd_modulator(adj):
    """
    Find a minimal set S such that G - S is an interval graph
    (Interval Vertex Deletion modulator).

    Algorithm
    ---------
    1. Greedy: repeatedly find an obstruction vertex and remove it.
    2. Reverse-delete refinement: shrink S by removing redundant vertices.

    Returns
    -------
    set — the modulator S
    """
    remaining = set(adj.keys())
    S = set()

    # 1. Greedy approximation
    while True:
        is_int, obs = _check_interval_and_get_obstruction(adj, remaining)
        if is_int:
            break
        S.add(obs)
        remaining.remove(obs)

    # 2. Reverse-delete refinement
    improved = True
    while improved:
        improved = False
        for v in list(S):
            candidate = S - {v}
            is_int, _ = _check_interval_and_get_obstruction(
                adj, set(adj.keys()) - candidate
            )
            if is_int:
                S = candidate
                improved = True
                break

    return S


# ===========================================================================
# SECTION 3: Min Total Dominating Set on Almost-Interval Graph
# ===========================================================================

def solve_tds_almost_interval(adj, S_set):
    """
    FPT algorithm for Minimum Total Dominating Set parameterized by |IVD modulator|.

    Parameters
    ----------
    adj   : dict {node: set(neighbours)}  — full symmetrized adjacency
    S_set : set — the IVD modulator (G - S_set is an interval graph)

    Returns
    -------
    list of nodes forming the minimum TDS, or None if none exists.
    """
    V = list(adj.keys())
    S = list(S_set)
    I = [v for v in V if v not in S_set]
    k = len(S)

    # Sort interval vertices by their rightmost interval-neighbour index
    I_sorted = sorted(
        I,
        key=lambda v: max(
            [I.index(nb) for nb in adj.get(v, set()) if nb in I] + [0]
        )
    )
    n = len(I_sorted)
    best_overall_tds = None

    for r in range(k + 1):
        for S_prime in itertools.combinations(S, r):
            S_prime_set = set(S_prime)

            # Bitmask: which S-vertices are already dominated by S'
            initial_mask = sum(
                1 << i
                for i, x in enumerate(S)
                if any(nb in S_prime_set for nb in adj.get(x, set()))
            )

            # Advance coverage frontier past I-vertices already dominated by S'
            initial_cov_idx = 0
            while (initial_cov_idx < n and
                   any(nb in S_prime_set
                       for nb in adj.get(I_sorted[initial_cov_idx], set()))):
                initial_cov_idx += 1

            # DP state: (last_picked_idx, cov_idx, last_picked_satisfied, s_mask)
            dp = {(-1, initial_cov_idx, True, initial_mask): []}

            for i, v in enumerate(I_sorted):
                new_dp = {}

                for (last_p_idx, cov_idx, p_sat, mask), current_set in dp.items():
                    temp_set = S_prime_set | set(current_set)

                    # ── OPTION 1: SKIP v ─────────────────────────────────────
                    skip_cov = cov_idx
                    while skip_cov < n and (
                        I_sorted[skip_cov] in temp_set or
                        any(nb in temp_set
                            for nb in adj.get(I_sorted[skip_cov], set()))
                    ):
                        skip_cov += 1

                    state_skip = (last_p_idx, skip_cov, p_sat, mask)
                    if (state_skip not in new_dp or
                            len(current_set) < len(new_dp[state_skip])):
                        new_dp[state_skip] = current_set

                    # ── OPTION 2: PICK v ─────────────────────────────────────
                    prev_v = I_sorted[last_p_idx] if last_p_idx != -1 else None

                    new_p_sat = (
                        any(nb in S_prime_set for nb in adj.get(v, set())) or
                        (prev_v is not None and v in adj.get(prev_v, set()))
                    )

                    # Consecutive-overlap pruning (COP)
                    if (last_p_idx != -1 and not p_sat and
                            v not in adj.get(prev_v, set())):
                        continue

                    temp_pick = temp_set | {v}
                    new_cov = cov_idx
                    while new_cov < n and (
                        I_sorted[new_cov] in temp_pick or
                        any(nb in temp_pick
                            for nb in adj.get(I_sorted[new_cov], set()))
                    ):
                        new_cov += 1

                    new_mask = mask | sum(
                        1 << idx
                        for idx, x in enumerate(S)
                        if x in adj.get(v, set())
                    )

                    state_pick = (i, new_cov, new_p_sat, new_mask)
                    new_set    = current_set + [v]

                    if (state_pick not in new_dp or
                            len(new_set) < len(new_dp[state_pick])):
                        new_dp[state_pick] = new_set

                dp = new_dp

            # ── Terminal check ────────────────────────────────────────────────
            target_mask = (1 << k) - 1
            for (last_p_idx, cov_idx, p_sat, mask), final_I_set in dp.items():
                if mask == target_mask and cov_idx == n and p_sat:
                    full_tds = list(S_prime_set) + final_I_set
                    tds_set  = set(full_tds)
                    # Verify total domination: every node in TDS has a TDS-neighbour
                    if all(any(nb in tds_set for nb in adj.get(u, set()))
                           for u in full_tds):
                        if (best_overall_tds is None or
                                len(full_tds) < len(best_overall_tds)):
                            best_overall_tds = full_tds

    return best_overall_tds


# ===========================================================================
# SECTION 4: Convenience wrapper (used by pipeline.py)
# ===========================================================================

def run_interval_pipeline(adj, verbose=True):
    """
    Full almost-interval TDS pipeline:
      1. Symmetrize adjacency
      2. Find IVD modulator S
      3. Solve Min-TDS via FPT DP

    Parameters
    ----------
    adj     : dict {node: set(neighbours)}
    verbose : bool — print progress

    Returns
    -------
    (S, tds)
        S   : set — IVD modulator
        tds : list — minimum TDS nodes (or None)
    """
    adj = symmetrize(adj)

    if verbose:
        print("  Graph: {} vertices, {} edges.".format(
            len(adj),
            sum(len(nb) for nb in adj.values()) // 2
        ))

    S = extract_ivd_modulator(adj)

    if verbose:
        print("  IVD Modulator S = {} nodes  (k={})".format(len(S), len(S)))
        print("  Running Min-TDS (2^{} guesses) ...".format(len(S)))

    tds = solve_tds_almost_interval(adj, S)

    if verbose:
        if tds:
            tds_set   = set(tds)
            dominated = all(any(nb in tds_set for nb in adj.get(v, set()))
                            for v in adj)
            total     = all(any(nb in tds_set for nb in adj.get(u, set()))
                            for u in tds_set)
            print("  Min TDS = {} nodes".format(len(tds)))
            print("  Dominated: {}  |  Total: {}".format(dominated, total))
        else:
            print("  No TDS found (possible isolated vertices).")

    return S, tds
