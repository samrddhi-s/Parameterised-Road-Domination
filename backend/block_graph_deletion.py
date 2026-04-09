

from __future__ import annotations
from collections import defaultdict, deque
from itertools import combinations
from typing import Dict, FrozenSet, Optional, Set, List, Tuple


Graph = Dict[int, Set[int]]   




def copy_graph(G: Graph) -> Graph:
    return {v: set(nbrs) for v, nbrs in G.items()}


def subgraph(G: Graph, vertices: Set[int]) -> Graph:
    """Induced subgraph on *vertices*."""
    return {v: G[v] & vertices for v in vertices}


def remove_vertices(G: Graph, S: Set[int]) -> Graph:
    """Return G - S (induced subgraph on V(G) \\ S)."""
    keep = set(G) - S
    return subgraph(G, keep)


def connected_components(G: Graph) -> List[Set[int]]:
    visited: Set[int] = set()
    comps: List[Set[int]] = []
    for start in G:
        if start not in visited:
            comp: Set[int] = set()
            stack = [start]
            while stack:
                v = stack.pop()
                if v in visited:
                    continue
                visited.add(v)
                comp.add(v)
                for u in G.get(v, ()):
                    if u not in visited:
                        stack.append(u)
            comps.append(comp)
    return comps


def is_clique(G: Graph, vertices: Set[int]) -> bool:
    vlist = list(vertices)
    for i in range(len(vlist)):
        for j in range(i + 1, len(vlist)):
            if vlist[j] not in G.get(vlist[i], ()):
                return False
    return True



def get_blocks(G: Graph) -> Tuple[List[Set[int]], Set[int]]:
    
    index: Dict[int, int] = {}
    lowlink: Dict[int, int] = {}
    parent: Dict[int, Optional[int]] = {}
    counter = [0]
    stack: List[int] = []
    on_stack: Set[int] = set()
    blocks: List[Set[int]] = []
    cut_vertices: Set[int] = set()

    edge_stack: List[Tuple[int, int]] = []

    def dfs(v: int, par: Optional[int]):
        index[v] = lowlink[v] = counter[0]
        counter[0] += 1
        child_count = 0
        for u in G.get(v, ()):
            if u == par:
                continue
            if u not in index:
                child_count += 1
                parent[u] = v
                edge_stack.append((v, u))
                dfs(u, v)
                lowlink[v] = min(lowlink[v], lowlink[u])
                # articulation point / block detection
                if (par is None and child_count > 1) or \
                   (par is not None and lowlink[u] >= index[v]):
                    if par is not None:
                        cut_vertices.add(v)
                    # pop block
                    block_edges: List[Tuple[int, int]] = []
                    while edge_stack and edge_stack[-1] != (v, u):
                        block_edges.append(edge_stack.pop())
                    if edge_stack:
                        block_edges.append(edge_stack.pop())
                    block_verts = set()
                    for a, b in block_edges:
                        block_verts.add(a)
                        block_verts.add(b)
                    if block_verts:
                        blocks.append(block_verts)
            elif index[u] < index[v]:   # back edge
                lowlink[v] = min(lowlink[v], index[u])
                edge_stack.append((v, u))

    for start in G:
        if start not in index:
            parent[start] = None
            dfs(start, None)
            # flush remaining edges as one block
            if edge_stack:
                block_verts = set()
                while edge_stack:
                    a, b = edge_stack.pop()
                    block_verts.add(a)
                    block_verts.add(b)
                if block_verts:
                    blocks.append(block_verts)

    for v in G:
        if not G[v]:  # degree 0
            if not any(v in b for b in blocks):
                blocks.append({v})

    return blocks, cut_vertices


def is_block_graph(G: Graph) -> bool:
    if not G:
        return True
    blocks, _ = get_blocks(G)
    return all(is_clique(G, b) for b in blocks)



def _is_diamond(G: Graph, verts: Set[int]) -> bool:
    if len(verts) != 4:
        return False
    vlist = list(verts)
    edges = sum(1 for i in range(4) for j in range(i+1, 4)
                if vlist[j] in G.get(vlist[i], ()))
    return edges == 5


def find_obstruction(G: Graph) -> Optional[Set[int]]:
    """
    Return the vertex set of one obstruction (diamond or induced C_ℓ, ℓ≥4),
    or None if G is already a block graph.
    """
    blocks, _ = get_blocks(G)
    for b in blocks:
        if not is_clique(G, b):
            obs = _find_obstruction_in_nonclique_block(G, b)
            if obs:
                return obs
    return None


def _find_obstruction_in_nonclique_block(G: Graph, B: Set[int]) -> Optional[Set[int]]:
    """Find a diamond or induced cycle ≥4 inside the block B."""
    Blist = list(B)
    # Try diamond first (4 vertices, 5 edges)
    for combo in combinations(Blist, 4):
        s = set(combo)
        if _is_diamond(G, s):
            return s
    # Try induced cycle of length 4..len(B)
    for length in range(4, len(B) + 1):
        for combo in combinations(Blist, length):
            s = set(combo)
            if _is_induced_cycle(G, s):
                return s
    return None


def _is_induced_cycle(G: Graph, verts: Set[int]) -> bool:
    if len(verts) < 4:
        return False
    vlist = list(verts)
    n = len(vlist)
    from itertools import permutations
    first = vlist[0]
    for perm in permutations(vlist[1:]):
        cycle = [first] + list(perm)
        ok = True
        for i in range(n):
            u, v = cycle[i], cycle[(i+1) % n]
            if v not in G.get(u, ()):
                ok = False
                break
        if not ok:
            continue
        chord = False
        for i in range(n):
            for j in range(i+2, n):
                if (i == 0 and j == n-1):
                    continue
                u, v = cycle[i], cycle[j]
                if v in G.get(u, ()):
                    chord = True
                    break
            if chord:
                break
        if not chord:
            return True
    return False


def _disjoint_block_deletion(G: Graph, S: Set[int], k: int) -> Optional[Set[int]]:
   
    # Base cases
    if is_block_graph(G):
        return set()
    if k <= 0:
        return None

    V_minus_S = set(G) - S

    triple = _find_bad_triple(G, S, V_minus_S)
    if triple is not None:
        u, v, w = triple
        for branch_v in (u, v, w):
            G2 = remove_vertices(G, {branch_v})
            S2 = S - {branch_v}
            res = _disjoint_block_deletion(G2, S2, k - 1)
            if res is not None:
                return res | {branch_v}
        return None

    branch_info = _find_component_branch(G, S, V_minus_S)
    if branch_info is not None:
        u, v = branch_info
        G2 = remove_vertices(G, {u})
        res = _disjoint_block_deletion(G2, S - {u}, k - 1)
        if res is not None:
            return res | {u}
        G2 = remove_vertices(G, {v})
        res = _disjoint_block_deletion(G2, S - {v}, k - 1)
        if res is not None:
            return res | {v}
        res = _disjoint_block_deletion(G, S | {u, v}, k)
        return res

    G_minus_S = subgraph(G, V_minus_S)
    blocks_GS, _ = get_blocks(G_minus_S)

    leaf_block = _find_leaf_block(G_minus_S, blocks_GS)
    if leaf_block is None:
        if is_block_graph(G):
            return set()
        return None

    b_verts = leaf_block
    _, cut_verts_GS = get_blocks(G_minus_S)
    boundary = b_verts & cut_verts_GS   
    remove_set = b_verts - boundary
    G_prime = remove_vertices(G, remove_set)

    N_S_B = set()
    for bv in b_verts:
        N_S_B |= (G.get(bv, set()) & S)

    if boundary:
        b_cut = next(iter(boundary))
        for s_v in N_S_B:
            if s_v != b_cut:
                G_prime[b_cut].add(s_v)
                G_prime[s_v].add(b_cut)

    return _disjoint_block_deletion(G_prime, S, k)


def _find_bad_triple(G: Graph, S: Set[int], V_minus_S: Set[int]):
    vmS = list(V_minus_S)
    candidates = vmS if len(vmS) >= 3 else vmS + vmS  
    for combo in combinations(set(vmS), min(3, len(vmS))):
        test_verts = S | set(combo)
        H = subgraph(G, test_verts)
        if not is_block_graph(H):
            triple = list(combo)
            while len(triple) < 3:
                triple.append(triple[-1])
            return triple[0], triple[1], triple[2]
    if len(vmS) <= 2:
        for combo in [vmS]:
            test_verts = S | set(combo)
            H = subgraph(G, test_verts)
            if not is_block_graph(H):
                triple = combo + combo + combo
                return triple[0], triple[1], triple[2]
    return None


def _find_component_branch(G: Graph, S: Set[int], V_minus_S: Set[int]):
    
    if not S:
        return None
    G_S = subgraph(G, S)
    comp_id: Dict[int, int] = {}
    for cid, comp in enumerate(connected_components(G_S)):
        for v in comp:
            comp_id[v] = cid

    for u in V_minus_S:
        for v in G.get(u, set()) & V_minus_S:
            nbrs_S = (G.get(u, set()) | G.get(v, set())) & S
            comp_ids_seen = {comp_id[x] for x in nbrs_S}
            if len(comp_ids_seen) >= 2:
                return (u, v)
    return None


def _find_leaf_block(G_minus_S: Graph, blocks: List[Set[int]]) -> Optional[Set[int]]:
    
    _, cut_verts = get_blocks(G_minus_S)
    for b in blocks:
        if len(b) < 2:
            continue
        boundary = b & cut_verts
        if len(boundary) <= 1:
            return b
    return None


def _compression(G: Graph, S: Set[int], k: int) -> Optional[Set[int]]:
    
    for i in range(len(S) + 1):
        for I in combinations(S, i):
            I_set = set(I)
            remaining_k = k - len(I_set)
            if remaining_k < 0:
                continue
            G2 = remove_vertices(G, I_set)
            S2 = S - I_set
            res = _disjoint_block_deletion(G2, S2, remaining_k)
            if res is not None:
                return res | I_set
    return None



def block_graph_deletion(G_input: Graph, k: int) -> Optional[Set[int]]:
   
    G = copy_graph(G_input)
    vertices = list(G)
    n = len(vertices)

    if is_block_graph(G):
        return set()

    S_current: Set[int] = set()
    G_current: Graph = {}

    for i, v in enumerate(vertices):
        G_current[v] = set()
        for u in G[v]:
            if u in G_current:
                G_current[v].add(u)
                G_current[u].add(v)

        S_try = S_current | {v}

        if len(S_try) <= k + 1:
            result = _compression(G_current, S_try, k)
            if result is None:
                S_current = S_try
            else:
                S_current = result
        else:
            result = _compression(G_current, S_current | {v}, k)
            if result is None:
                return None 
            S_current = result

    G_check = remove_vertices(G, S_current)
    if is_block_graph(G_check):
        return S_current
    return None


def min_block_graph_deletion(G: Graph, max_k: int = 10) -> Optional[Set[int]]:
    
    for k in range(max_k + 1):
        result = block_graph_deletion(G, k)
        if result is not None:
            return result
    return None



def _make_cycle(n: int) -> Graph:
    G: Graph = {i: set() for i in range(n)}
    for i in range(n):
        G[i].add((i + 1) % n)
        G[(i + 1) % n].add(i)
    return G


def _make_diamond() -> Graph:
    return {0: {1, 2, 3}, 1: {0, 2, 3}, 2: {0, 1}, 3: {0, 1}}


def _make_complete(n: int) -> Graph:
    G: Graph = {i: set() for i in range(n)}
    for i in range(n):
        for j in range(n):
            if i != j:
                G[i].add(j)
    return G


if __name__ == "__main__":
    print("=" * 60)
    print("Block Graph Deletion  –  Demo & Tests")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Test 1: A single C4 (induced 4-cycle) -> delete 1 vertex
    # ------------------------------------------------------------------
    print("\n[Test 1] C4 (4-cycle) – need to delete 1 vertex")
    G1 = _make_cycle(4)
    sol = min_block_graph_deletion(G1)
    print(f"  Graph edges: {[(u,v) for u in G1 for v in G1[u] if u<v]}")
    print(f"  Solution: delete {sol}")
    G1_check = remove_vertices(G1, sol)
    print(f"  Is block graph after deletion? {is_block_graph(G1_check)}")

    # ------------------------------------------------------------------
    # Test 2: Diamond -> delete 1 vertex
    # ------------------------------------------------------------------
    print("\n[Test 2] Diamond – need to delete 1 vertex")
    G2 = _make_diamond()
    sol = min_block_graph_deletion(G2)
    print(f"  Graph edges: {[(u,v) for u in G2 for v in G2[u] if u<v]}")
    print(f"  Solution: delete {sol}")
    G2_check = remove_vertices(G2, sol)
    print(f"  Is block graph after deletion? {is_block_graph(G2_check)}")

    # ------------------------------------------------------------------
    # Test 3: C5 (5-cycle) -> delete 1 vertex
    # ------------------------------------------------------------------
    print("\n[Test 3] C5 (5-cycle) – need to delete 1 vertex")
    G3 = _make_cycle(5)
    sol = min_block_graph_deletion(G3)
    print(f"  Solution: delete {sol}")
    G3_check = remove_vertices(G3, sol)
    print(f"  Is block graph after deletion? {is_block_graph(G3_check)}")

    # ------------------------------------------------------------------
    # Test 4: Already a block graph (two triangles sharing a vertex)
    # ------------------------------------------------------------------
    print("\n[Test 4] Two triangles sharing a vertex (already block graph)")
    G4 = {0:{1,2}, 1:{0,2}, 2:{0,1,3,4}, 3:{2,4}, 4:{2,3}}
    sol = min_block_graph_deletion(G4)
    print(f"  Solution: delete {sol}  (should be empty set)")
    print(f"  Is block graph: {is_block_graph(G4)}")

    # ------------------------------------------------------------------
    # Test 5: Graph from the paper intro – block graph test
    # ------------------------------------------------------------------
    print("\n[Test 5] Custom graph: K4 with two extra vertices forming a C4")
    G5 = {
        0: {1, 2, 3},
        1: {0, 2, 3},
        2: {0, 1, 3},
        3: {0, 1, 2, 4},
        4: {3, 5, 6},
        5: {4, 6},
        6: {4, 5},
    }
    sol = min_block_graph_deletion(G5)
    print(f"  Solution: delete {sol}")
    if sol is not None:
        G5_check = remove_vertices(G5, sol)
        print(f"  Is block graph after deletion? {is_block_graph(G5_check)}")

    # ------------------------------------------------------------------
    # Test 6: K4 (complete graph on 4) – already a block graph (single clique block)
    # ------------------------------------------------------------------
    print("\n[Test 6] K4 – already a block graph (single clique)")
    G6 = _make_complete(4)
    sol = min_block_graph_deletion(G6)
    print(f"  Solution: delete {sol}  (should be empty set)")

    # ------------------------------------------------------------------
    # Test 7: Two C4s sharing an edge
    # ------------------------------------------------------------------
    print("\n[Test 7] Two C4s sharing an edge – need to delete 2 vertices")
    G7 = {
        0: {1, 3},
        1: {0, 2, 4},
        2: {1, 3, 5},
        3: {0, 2},
        4: {1, 5},
        5: {2, 4},
    }
    sol = min_block_graph_deletion(G7)
    print(f"  Solution: delete {sol}")
    if sol is not None:
        G7_check = remove_vertices(G7, sol)
        print(f"  Is block graph after deletion? {is_block_graph(G7_check)}")

    print("\n" + "=" * 60)
    print("All tests done.")
    print("=" * 60)
    print("""
API Summary
-----------
block_graph_deletion(G, k)
    Returns a deletion set S ⊆ V(G) with |S|≤k, or None.

min_block_graph_deletion(G, max_k=10)
    Tries k=0,1,...,max_k and returns the smallest deletion set found.

is_block_graph(G)
    Returns True iff G is already a block graph.

remove_vertices(G, S)
    Returns G - S (induced subgraph).

Graph format: dict mapping each vertex (int) to a set of neighbour ints.
""")
