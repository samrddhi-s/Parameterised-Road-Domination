"""
msds_solver.py
==============
Cluster Vertex Deletion (CVD) modulator finder +
Minimum Secure Dominating Set (MSDS) FPT solver.

Used by pipeline.py for the "Almost Cluster Graph" branch.
"""

import networkx as nx
from itertools import combinations


# ===========================================================================
# CVD — Cluster Vertex Deletion
# ===========================================================================

def find_p3(G):
    """Find an induced P3 (path of length 2) in G.  Returns (v1, v2, v3) or None."""
    for v2 in G.nodes():
        neighbors = list(G.neighbors(v2))
        for i in range(len(neighbors)):
            for j in range(i + 1, len(neighbors)):
                v1, v3 = neighbors[i], neighbors[j]
                if not G.has_edge(v1, v3):
                    return (v1, v2, v3)
    return None


def find_cvd_minimal(G):
    """
    Minimal Cluster Vertex Deletion set via P3-branching.
    Returns a list of node ids that form the CVD modulator S.
    """
    best_S = set(G.nodes())

    def branch(current_G, current_S):
        nonlocal best_S
        if len(current_S) >= len(best_S):
            return
        p3 = find_p3(current_G)
        if p3 is None:
            if len(current_S) < len(best_S):
                best_S = set(current_S)
            return
        for v in p3:
            next_G = current_G.copy()
            next_G.remove_node(v)
            current_S.add(v)
            branch(next_G, current_S)
            current_S.remove(v)

    branch(G.copy(), set())
    return list(best_S)


def get_cvd_and_cliques(G, S_nodes):
    """
    Given graph G and modulator S_nodes, partition G - S into cliques.
    Returns (S_frozenset, list_of_cliques).
    Each connected component of G[V-S] is either a clique (returned as one list)
    or broken into singleton lists if it is not a clique.
    """
    S = frozenset(S_nodes)
    cliques = []
    remaining_nodes = set(G.nodes()) - S
    for comp in nx.connected_components(G.subgraph(remaining_nodes)):
        sub = G.subgraph(comp)
        n = len(comp)
        if n > 1 and sub.number_of_edges() == n * (n - 1) // 2:
            cliques.append(list(comp))
        else:
            for v in comp:
                cliques.append([v])
    return S, cliques


# ===========================================================================
# SDS — Secure Dominating Set
# ===========================================================================

def is_secure_dominating(G, D):
    """
    Returns True iff D is a Secure Dominating Set of G.
      - Domination:  every v not in D has a neighbour in D.
      - Security:    for every u not in D, there exists v in N(u) ∩ D such that
                     (D - {v}) ∪ {u} is still a dominating set.
    """
    nodes = set(G.nodes())
    D = set(D)
    if not D:
        return False
    # Domination
    for v in nodes - D:
        if not (set(G.neighbors(v)) & D):
            return False
    # Security
    for u in nodes - D:
        can_swap = False
        for v in set(G.neighbors(u)) & D:
            D_prime = (D - {v}) | {u}
            if all((set(G.neighbors(w)) & D_prime) for w in nodes - D_prime):
                can_swap = True
                break
        if not can_swap:
            return False
    return True


def _get_pendant_info(G, S_nodes):
    """Map each non-S node v -> list of S-pendant neighbours of v."""
    v_to_pendants = {}
    for s in S_nodes:
        if G.degree(s) == 1:
            v = list(G.neighbors(s))[0]
            if v not in S_nodes:
                v_to_pendants.setdefault(v, []).append(s)
    return v_to_pendants


def _get_valid_S_subsets(G, S_nodes, active_s, fixed_in_D):
    """
    Enumerate subsets of S to include in D, with structural pruning.
    Returns a list of sets, sorted by size (smallest first).
    """
    S_set = set(S_nodes)
    C_nodes = set(G.nodes()) - S_set
    S_neighbors = {v: set(G.neighbors(v)) & S_set for v in G.nodes()}
    C_neighbors = {v: set(G.neighbors(v)) & C_nodes for v in G.nodes()}
    valid_subsets = []
    n = len(active_s)

    def backtrack(idx, current_D_S, current_S_out):
        # Prune: an S-node outside D with no C-neighbours and no D-S neighbour is undominated
        for s in current_S_out:
            if not C_neighbors[s] and not (S_neighbors[s] & current_D_S):
                if not (S_neighbors[s] - current_D_S - current_S_out):
                    return
        if idx == n:
            valid_subsets.append(set(current_D_S))
            return
        v = active_s[idx]
        current_D_S.add(v)
        backtrack(idx + 1, current_D_S, current_S_out)
        current_D_S.remove(v)
        current_S_out.add(v)
        backtrack(idx + 1, current_D_S, current_S_out)
        current_S_out.remove(v)

    backtrack(0, set(fixed_in_D), set())
    valid_subsets.sort(key=len)
    return valid_subsets


def solve_msds_fpt(G, S_nodes, cliques=None):
    """
    FPT algorithm for Minimum Secure Dominating Set,
    parameterized by the size of the CVD modulator S_nodes.

    Parameters
    ----------
    G        : networkx.Graph
    S_nodes  : list — the CVD modulator (G - S_nodes is a cluster graph)
    cliques  : list of lists (optional) — pre-computed clique partition of G - S

    Returns
    -------
    list of nodes forming the minimum SDS, or None if not found.
    """
    if cliques is None:
        _, cliques = get_cvd_and_cliques(G, S_nodes)

    k       = len(S_nodes)
    S_set   = set(S_nodes)
    v_to_pents  = _get_pendant_info(G, S_nodes)
    isolated_s  = [s for s in S_nodes if G.degree(s) == 0]
    fixed_in_D  = set(isolated_s)
    active_s    = [s for s in S_nodes if s not in fixed_in_D]
    min_size    = float('inf')
    best_msds   = None

    all_subsets = _get_valid_S_subsets(G, S_nodes, active_s, fixed_in_D)

    for D_S in all_subsets:
        if len(D_S) >= min_size:
            break

        s_needs_dom = [s for s in S_nodes
                       if s not in D_S and not (set(G.neighbors(s)) & D_S)]
        s_map = {node: i for i, node in enumerate(s_needs_dom)}
        n_s   = len(s_needs_dom)

        clique_ext_dom = [{v for v in c if set(G.neighbors(v)) & D_S} for c in cliques]
        dp = {0: [(0, [])]}

        for ci, clique in enumerate(cliques):
            ext_dom      = clique_ext_dom[ci]
            forced_nodes = {v for v in clique
                            if v in v_to_pents and
                            any(p not in D_S for p in v_to_pents[v])}

            groups = {}
            for v in clique:
                sig = tuple(sorted(set(G.neighbors(v)) & S_set))
                groups[sig] = groups.get(sig, []) + [v]
            reduced_nodes = []
            for sig, members in groups.items():
                reduced_nodes.extend(members[:k + 1])

            local_options = []
            for r in range(len(forced_nodes), min(len(reduced_nodes), k + 2) + 1):
                for picked in combinations(reduced_nodes, r):
                    p_set = set(picked)
                    if not forced_nodes.issubset(p_set):
                        continue
                    s_mask = 0
                    for s_node in s_needs_dom:
                        if set(G.neighbors(s_node)) & p_set:
                            s_mask |= (1 << s_map[s_node])
                    if all(v in p_set or v in ext_dom or (set(G.neighbors(v)) & p_set)
                           for v in clique):
                        local_options.append((r, list(picked), s_mask))

            if not local_options and set(clique) == ext_dom:
                local_options = [(0, [], 0)]

            new_dp = {}
            for m_old, candidates in dp.items():
                for r_loc, n_loc, m_loc in local_options:
                    comb_mask = m_old | m_loc
                    for r_old, n_old in candidates:
                        new_size  = r_old + r_loc
                        new_nodes = n_old + n_loc
                        if len(D_S) + new_size >= min_size:
                            continue
                        new_dp.setdefault(comb_mask, []).append((new_size, new_nodes))

            for m in new_dp:
                if not new_dp[m]:
                    continue
                best_sz = min(c[0] for c in new_dp[m])
                new_dp[m] = [c for c in new_dp[m] if c[0] <= best_sz + k]
                seen, deduped = {}, []
                for sz, nodes in new_dp[m]:
                    key = tuple(sorted(nodes))
                    if key not in seen:
                        seen[key] = True
                        deduped.append((sz, nodes))
                new_dp[m] = deduped
            dp = new_dp
            if not dp:
                break

        if not dp:
            continue

        target_mask = (1 << n_s) - 1
        current_local_best = None
        for m, candidates in dp.items():
            if m != target_mask:
                continue
            for size, nodes in candidates:
                candidate = list(D_S) + nodes
                if is_secure_dominating(G, candidate):
                    if current_local_best is None or len(candidate) < len(current_local_best):
                        current_local_best = candidate

        if current_local_best and len(current_local_best) < min_size:
            min_size, best_msds = len(current_local_best), current_local_best

    return best_msds
