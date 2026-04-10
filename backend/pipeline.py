"""
pipeline.py
===========
Full Pipeline: OSM -> Graph Type Choice -> Min Dominating Set
=============================================================
Choice 1: Almost Block Graph     -> Block Graph Deletion (BGD) -> Min TDS  (C++ solver)
Choice 2: Almost Cluster Graph   -> Cluster Vertex Deletion (CVD) -> Min SDS  (Python FPT)
Choice 3: Almost Interval Graph  -> Interval Vertex Deletion (IVD) -> Min TDS  (Python FPT)
"""

import sys
import os
import subprocess
import argparse
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── CVD + MSDS solver (cluster branch) ───────────────────────────────────────
from msds_solver import (
    find_cvd_minimal,
    get_cvd_and_cliques,
    solve_msds_fpt,
    is_secure_dominating,
)

# ── IVD + TDS solver (interval branch) ───────────────────────────────────────
from interval_tds_solver import (
    nx_to_adj,
    extract_ivd_modulator,
    solve_tds_almost_interval,
    run_interval_pipeline,
)

try:
    import osmnx as ox
except ImportError:
    print("osmnx not installed. Run: pip install osmnx")
    sys.exit(1)

try:
    import contextily as ctx
    from pyproj import Transformer
    _HAS_CONTEXTILY = True
except ImportError:
    _HAS_CONTEXTILY = False
    print("  [info] contextily/pyproj not installed - satellite image will be skipped.")

try:
    from block_graph_deletion import block_graph_deletion, is_block_graph, remove_vertices
    _HAS_BGD = True
except ImportError:
    _HAS_BGD = False
    print("  [info] block_graph_deletion.py not found - Almost Block Graph mode unavailable.")


# ===========================================================================
# SECTION A: SHARED OSM UTILITIES
# ===========================================================================

def reverse_geocode(lat, lon):
    try:
        import urllib.request, json
        url = (
            "https://nominatim.openstreetmap.org/reverse"
            "?format=json&lat={}&lon={}&zoom=16&addressdetails=1".format(lat, lon)
        )
        req = urllib.request.Request(url, headers={"User-Agent": "tds-pipeline/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        addr = data.get("address", {})
        fine   = (addr.get("neighbourhood") or addr.get("suburb")
                  or addr.get("quarter")    or addr.get("village") or "")
        coarse = (addr.get("city_district") or addr.get("town")
                  or addr.get("city")       or addr.get("county") or "")
        if fine and coarse and fine.lower() != coarse.lower():
            return "{}, {}".format(fine, coarse)
        return fine or coarse or data.get("display_name", "").split(",")[0]
    except Exception:
        return "{}, {}".format(round(lat, 4), round(lon, 4))


def _to_undirected(G_osm):
    try:
        return ox.utils_graph.get_undirected(G_osm)
    except AttributeError:
        pass
    try:
        return ox.convert.to_undirected(G_osm)
    except AttributeError:
        pass
    return G_osm.to_undirected()


def fetch_osm(args, st_status=None):
    if st_status:
        st_status.update(label="Fetching OSM data...", state="running")
    if args.point:
        lat, lon = args.point
        area_name = reverse_geocode(lat, lon)
        label = "{} ({}, {}) r={}m".format(area_name, lat, lon, args.radius)
        print("  Fetching: point {} radius {}m".format(args.point, args.radius))
        G_osm = ox.graph_from_point((lat, lon), dist=args.radius, network_type=args.network)
    elif args.bbox:
        n, s, e, w = args.bbox
        label = "bbox"
        print("  Fetching: bbox")
        try:
            G_osm = ox.graph_from_bbox(n, s, e, w, network_type=args.network)
        except TypeError:
            G_osm = ox.graph_from_bbox(bbox=(n, s, e, w), network_type=args.network)
    else:
        label = args.place
        print("  Fetching: place -- {}".format(args.place))
        G_osm = ox.graph_from_place(args.place, network_type=args.network)

    G_osm = _to_undirected(G_osm)
    G_nx = nx.Graph()
    for u, v in G_osm.edges():
        G_nx.add_edge(u, v)
    for node, data in G_osm.nodes(data=True):
        if node in G_nx.nodes:
            G_nx.nodes[node]["x"] = data.get("x", 0)
            G_nx.nodes[node]["y"] = data.get("y", 0)

    n, e = G_nx.number_of_nodes(), G_nx.number_of_edges()
    print("  Graph: {} nodes, {} edges".format(n, e))
    if n > args.maxnodes:
        raise ValueError("{} nodes exceeds --maxnodes {}.".format(n, args.maxnodes))
    return G_nx, label


def compress(G_nx):
    """Iteratively remove leaf (degree-1) nodes."""
    G = G_nx.copy()
    changed = True
    while changed:
        changed = False
        leaves = [v for v in G.nodes() if G.degree(v) == 1]
        if leaves:
            G.remove_nodes_from(leaves)
            changed = True
    print("  After compression: {} nodes, {} edges".format(
        G.number_of_nodes(), G.number_of_edges()))
    return G


def nx_to_bgd(G_nx):
    nodes = list(G_nx.nodes())
    n2i = {n: i for i, n in enumerate(nodes)}
    i2n = {i: n for i, n in enumerate(nodes)}
    G_bgd = {i: set() for i in range(len(nodes))}
    for u, v in G_nx.edges():
        G_bgd[n2i[u]].add(n2i[v])
        G_bgd[n2i[v]].add(n2i[u])
    return G_bgd, n2i, i2n


def annotate_corner_leaves(ax, G_nx):
    """Annotate the 4 extreme leaf nodes with coordinates."""
    leaf_nodes = [n for n in G_nx.nodes() if G_nx.degree(n) == 1]
    if not leaf_nodes:
        return
    corner_leaves = {}
    for n in leaf_nodes:
        x = G_nx.nodes[n]["x"]
        y = G_nx.nodes[n]["y"]
        if "top"    not in corner_leaves or y > G_nx.nodes[corner_leaves["top"]]["y"]:
            corner_leaves["top"]    = n
        if "bottom" not in corner_leaves or y < G_nx.nodes[corner_leaves["bottom"]]["y"]:
            corner_leaves["bottom"] = n
        if "left"   not in corner_leaves or x < G_nx.nodes[corner_leaves["left"]]["x"]:
            corner_leaves["left"]   = n
        if "right"  not in corner_leaves or x > G_nx.nodes[corner_leaves["right"]]["x"]:
            corner_leaves["right"]  = n
    offsets = {
        "top":    (0,   9, "center", "bottom"),
        "bottom": (0,  -9, "center", "top"),
        "left":   (-6,  0, "right",  "center"),
        "right":  ( 6,  0, "left",   "center"),
    }
    labelled = set()
    for side, n in corner_leaves.items():
        if n in labelled:
            continue
        labelled.add(n)
        nx_val = G_nx.nodes[n]["x"]
        ny_val = G_nx.nodes[n]["y"]
        dx, dy, ha, va = offsets[side]
        ax.annotate(
            "({:.4f}, {:.4f})".format(ny_val, nx_val),
            xy=(nx_val, ny_val), xytext=(dx, dy),
            textcoords="offset points", fontsize=7, color="#444444", ha=ha, va=va,
            bbox=dict(boxstyle="round,pad=0.2", fc="white",
                      ec="#aaaaaa", alpha=0.85, linewidth=0.6),
        )


# ===========================================================================
# SECTION B: VISUALIZATIONS — CLUSTER BRANCH (CVD + SDS)
# ===========================================================================

def visualize_cvd_modulator(G_nx, modulator_osm, label):
    pos    = {n: (G_nx.nodes[n]["x"], G_nx.nodes[n]["y"]) for n in G_nx.nodes()}
    colors = ["#e74c3c" if n in modulator_osm else "#111111" for n in G_nx.nodes()]
    sizes  = [140 if n in modulator_osm else 25 for n in G_nx.nodes()]

    fig, ax = plt.subplots(figsize=(12, 9))
    nx.draw_networkx_edges(G_nx, pos, ax=ax, edge_color="#111111", width=0.8, alpha=0.6)
    nx.draw_networkx_nodes(G_nx, pos, ax=ax, node_color=colors, node_size=sizes)
    annotate_corner_leaves(ax, G_nx)
    ax.legend(handles=[
        mpatches.Patch(color="#111111", label="Regular nodes (G-S)"),
        mpatches.Patch(color="#e74c3c",
                       label="CVD Modulator S ({} nodes)".format(len(modulator_osm))),
    ], fontsize=10, loc="lower right", frameon=True, framealpha=0.92, edgecolor="#aaaaaa")
    ax.set_title(
        "OSM Road Network — {}\nCVD Modulator S  |S| = {}".format(label, len(modulator_osm)),
        fontsize=13, fontweight="bold")
    ax.axis("off")
    plt.tight_layout()
    plt.savefig("sds_modulator.png", dpi=150, bbox_inches="tight")
    print("  Image 1 saved -> sds_modulator.png  (CVD modulator)")
    plt.close(fig)
    return "sds_modulator.png"


def visualize_sds(G_nx, modulator_osm, sds_osm, label, sds_size):
    pos = {n: (G_nx.nodes[n]["x"], G_nx.nodes[n]["y"]) for n in G_nx.nodes()}
    node_colors, node_sizes = [], []
    for n in G_nx.nodes():
        in_sds = n in sds_osm
        in_mod = n in modulator_osm
        if in_sds and in_mod:
            node_colors.append("#c0392b"); node_sizes.append(200)
        elif in_sds:
            node_colors.append("#27ae60"); node_sizes.append(80)
        elif in_mod:
            node_colors.append("#e67e22"); node_sizes.append(150)
        else:
            node_colors.append("#111111"); node_sizes.append(20)

    fig, ax = plt.subplots(figsize=(12, 9))
    nx.draw_networkx_edges(G_nx, pos, ax=ax, edge_color="#111111", width=0.8, alpha=0.6)
    nx.draw_networkx_nodes(G_nx, pos, ax=ax, node_color=node_colors, node_size=node_sizes)
    annotate_corner_leaves(ax, G_nx)
    ax.legend(handles=[
        mpatches.Patch(color="#27ae60", label="In SDS — regular vertex"),
        mpatches.Patch(color="#c0392b", label="In SDS — modulator vertex"),
        mpatches.Patch(color="#e67e22", label="Modulator — NOT in SDS"),
        mpatches.Patch(color="#111111", label="Not in SDS"),
    ], fontsize=10, loc="lower right", frameon=True, framealpha=0.92, edgecolor="#aaaaaa")
    ax.set_title(
        "Minimum Secure Dominating Set — {}\nMin SDS size = {}".format(label, sds_size),
        fontsize=13, fontweight="bold")
    ax.axis("off")
    plt.tight_layout()
    plt.savefig("sds_result.png", dpi=150, bbox_inches="tight")
    print("  Image 2 saved -> sds_result.png  (SDS placement)")
    plt.close(fig)
    return "sds_result.png"


def save_satellite_sds(lat, lon, radius, label, G_nx, modulator_osm, sds_osm):
    if not _HAS_CONTEXTILY:
        print("  Skipping satellite image (contextily not installed).")
        return None
    fwd = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    pos_merc = {n: fwd.transform(G_nx.nodes[n]["x"], G_nx.nodes[n]["y"]) for n in G_nx.nodes()}
    xs = [p[0] for p in pos_merc.values()]
    ys = [p[1] for p in pos_merc.values()]
    pad = radius * 0.25
    west, east   = min(xs) - pad, max(xs) + pad
    south, north = min(ys) - pad, max(ys) + pad

    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_xlim(west, east); ax.set_ylim(south, north)
    try:
        ctx.add_basemap(ax, crs="EPSG:3857",
                        source=ctx.providers.Esri.WorldImagery,
                        zoom="auto", attribution=False)
    except Exception as e:
        print("  Could not fetch satellite tiles:", e)
        plt.close(fig); return None

    for u, v in G_nx.edges():
        x0, y0 = pos_merc[u]; x1, y1 = pos_merc[v]
        ax.plot([x0, x1], [y0, y1], color="white", linewidth=1.2, alpha=0.75, zorder=2)
    for n in G_nx.nodes():
        x, y = pos_merc[n]
        in_sds = n in sds_osm; in_mod = n in modulator_osm
        if in_sds and in_mod:   color, size, zorder = "#c0392b", 60, 5
        elif in_sds:            color, size, zorder = "#27ae60", 35, 4
        elif in_mod:            color, size, zorder = "#e67e22", 50, 5
        else:                   color, size, zorder = "#ffffff", 15, 3
        ax.scatter(x, y, s=size, c=color, zorder=zorder, edgecolors="black", linewidths=0.4)

    cx, cy = fwd.transform(lon, lat)
    ax.add_patch(plt.Circle((cx, cy), radius, color="cyan",
                             fill=False, linewidth=1.5, linestyle="--", alpha=0.8, zorder=6))
    ax.plot(cx, cy, "c+", markersize=10, markeredgewidth=1.5, zorder=7)
    ax.legend(handles=[
        mpatches.Patch(color="#27ae60", label="In SDS — regular"),
        mpatches.Patch(color="#c0392b", label="In SDS — modulator"),
        mpatches.Patch(color="#e67e22", label="Modulator — NOT in SDS"),
        mpatches.Patch(color="#ffffff", label="Not in SDS", edgecolor="black", linewidth=0.5),
    ], fontsize=9, loc="lower right", frameon=True, framealpha=0.85, edgecolor="#aaaaaa")
    ax.set_axis_off()
    ax.set_title("Satellite View (SDS) — {}\n({}, {})  r={}m".format(label, lat, lon, radius),
                 fontsize=13, fontweight="bold", pad=10)
    plt.tight_layout()
    plt.savefig("sds_satellite.png", dpi=150, bbox_inches="tight")
    print("  Image 3 saved -> sds_satellite.png")
    plt.close(fig)
    return "sds_satellite.png"


# ===========================================================================
# SECTION C: VISUALIZATIONS — BLOCK BRANCH (BGD + TDS)
# ===========================================================================

def visualize_modulator(G_nx, modulator_osm, label, tds_size):
    pos    = {n: (G_nx.nodes[n]["x"], G_nx.nodes[n]["y"]) for n in G_nx.nodes()}
    colors = ["#e74c3c" if n in modulator_osm else "#111111" for n in G_nx.nodes()]
    sizes  = [140 if n in modulator_osm else 25 for n in G_nx.nodes()]
    fig, ax = plt.subplots(figsize=(12, 9))
    nx.draw_networkx_edges(G_nx, pos, ax=ax, edge_color="#111111", width=0.8, alpha=0.6)
    nx.draw_networkx_nodes(G_nx, pos, ax=ax, node_color=colors, node_size=sizes)
    annotate_corner_leaves(ax, G_nx)
    ax.legend(handles=[
        mpatches.Patch(color="#111111", label="Regular nodes (G-S)"),
        mpatches.Patch(color="#e74c3c",
                       label="BGD Modulator S ({} nodes)".format(len(modulator_osm))),
    ], fontsize=10, loc="lower right", frameon=True, framealpha=0.92, edgecolor="#aaaaaa")
    ax.set_title(
        "OSM Road Network — {}\nBGD Modulator S  |S|={}  |  Min TDS={}".format(
            label, len(modulator_osm), tds_size),
        fontsize=13, fontweight="bold")
    ax.axis("off"); plt.tight_layout()
    plt.savefig("tds_modulator.png", dpi=150, bbox_inches="tight")
    print("  Image 1 saved -> tds_modulator.png"); plt.close(fig)
    return "tds_modulator.png"


def visualize_tds(G_nx, modulator_osm, tds_osm, label, tds_size):
    pos = {n: (G_nx.nodes[n]["x"], G_nx.nodes[n]["y"]) for n in G_nx.nodes()}
    node_colors, node_sizes = [], []
    for n in G_nx.nodes():
        in_tds = n in tds_osm; in_mod = n in modulator_osm
        if in_tds and in_mod:  node_colors.append("#c0392b"); node_sizes.append(200)
        elif in_tds:           node_colors.append("#27ae60"); node_sizes.append(80)
        elif in_mod:           node_colors.append("#e67e22"); node_sizes.append(150)
        else:                  node_colors.append("#111111"); node_sizes.append(20)
    fig, ax = plt.subplots(figsize=(12, 9))
    nx.draw_networkx_edges(G_nx, pos, ax=ax, edge_color="#111111", width=0.8, alpha=0.6)
    nx.draw_networkx_nodes(G_nx, pos, ax=ax, node_color=node_colors, node_size=node_sizes)
    annotate_corner_leaves(ax, G_nx)
    ax.legend(handles=[
        mpatches.Patch(color="#27ae60", label="In TDS — regular vertex"),
        mpatches.Patch(color="#c0392b", label="In TDS — modulator vertex"),
        mpatches.Patch(color="#e67e22", label="Modulator — NOT in TDS"),
        mpatches.Patch(color="#111111", label="Not in TDS"),
    ], fontsize=10, loc="lower right", frameon=True, framealpha=0.92, edgecolor="#aaaaaa")
    ax.set_title(
        "Minimum Total Dominating Set — {}\nMin TDS size = {}".format(label, tds_size),
        fontsize=13, fontweight="bold")
    ax.axis("off"); plt.tight_layout()
    plt.savefig("tds_result.png", dpi=150, bbox_inches="tight")
    print("  Image 2 saved -> tds_result.png"); plt.close(fig)
    return "tds_result.png"


def save_satellite_image(lat, lon, radius, label, G_nx, modulator_osm, tds_osm):
    if not _HAS_CONTEXTILY:
        print("  Skipping satellite image (contextily not installed)."); return None
    fwd = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    pos_merc = {n: fwd.transform(G_nx.nodes[n]["x"], G_nx.nodes[n]["y"]) for n in G_nx.nodes()}
    xs = [p[0] for p in pos_merc.values()]; ys = [p[1] for p in pos_merc.values()]
    pad = radius * 0.25
    west, east = min(xs) - pad, max(xs) + pad
    south, north = min(ys) - pad, max(ys) + pad
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_xlim(west, east); ax.set_ylim(south, north)
    try:
        ctx.add_basemap(ax, crs="EPSG:3857", source=ctx.providers.Esri.WorldImagery,
                        zoom="auto", attribution=False)
    except Exception as e:
        print("  Could not fetch satellite tiles:", e); plt.close(fig); return None
    for u, v in G_nx.edges():
        x0, y0 = pos_merc[u]; x1, y1 = pos_merc[v]
        ax.plot([x0, x1], [y0, y1], color="white", linewidth=1.2, alpha=0.75, zorder=2)
    for n in G_nx.nodes():
        x, y = pos_merc[n]; in_tds = n in tds_osm; in_mod = n in modulator_osm
        if in_tds and in_mod:  color, size, zorder = "#c0392b", 60, 5
        elif in_tds:           color, size, zorder = "#27ae60", 35, 4
        elif in_mod:           color, size, zorder = "#e67e22", 50, 5
        else:                  color, size, zorder = "#ffffff", 15, 3
        ax.scatter(x, y, s=size, c=color, zorder=zorder, edgecolors="black", linewidths=0.4)
    cx, cy = fwd.transform(lon, lat)
    ax.add_patch(plt.Circle((cx, cy), radius, color="red",
                             fill=False, linewidth=1.5, linestyle="--", alpha=0.8, zorder=6))
    ax.plot(cx, cy, "r+", markersize=10, markeredgewidth=1.5, zorder=7)
    ax.legend(handles=[
        mpatches.Patch(color="#27ae60", label="In TDS — regular"),
        mpatches.Patch(color="#c0392b", label="In TDS — modulator"),
        mpatches.Patch(color="#e67e22", label="Modulator — NOT in TDS"),
        mpatches.Patch(color="#ffffff", label="Not in TDS", edgecolor="black", linewidth=0.5),
    ], fontsize=9, loc="lower right", frameon=True, framealpha=0.85, edgecolor="#aaaaaa")
    ax.set_axis_off()
    ax.set_title("Satellite View — {}\n({}, {})  r={}m  |  Graph overlaid".format(
        label, lat, lon, radius), fontsize=13, fontweight="bold", pad=10)
    plt.tight_layout()
    plt.savefig("tds_satellite.png", dpi=150, bbox_inches="tight")
    print("  Image 3 saved -> tds_satellite.png"); plt.close(fig)
    return "tds_satellite.png"


# ===========================================================================
# SECTION D: VISUALIZATIONS — INTERVAL BRANCH (IVD + TDS)
# ===========================================================================

def visualize_ivd_modulator(G_nx, modulator_osm, label, tds_size):
    pos    = {n: (G_nx.nodes[n]["x"], G_nx.nodes[n]["y"]) for n in G_nx.nodes()}
    colors = ["#8e44ad" if n in modulator_osm else "#111111" for n in G_nx.nodes()]
    sizes  = [140 if n in modulator_osm else 25 for n in G_nx.nodes()]

    fig, ax = plt.subplots(figsize=(12, 9))
    nx.draw_networkx_edges(G_nx, pos, ax=ax, edge_color="#111111", width=0.8, alpha=0.6)
    nx.draw_networkx_nodes(G_nx, pos, ax=ax, node_color=colors, node_size=sizes)
    annotate_corner_leaves(ax, G_nx)
    ax.legend(handles=[
        mpatches.Patch(color="#111111", label="Regular nodes (G-S)"),
        mpatches.Patch(color="#8e44ad",
                       label="IVD Modulator S ({} nodes)".format(len(modulator_osm))),
    ], fontsize=10, loc="lower right", frameon=True, framealpha=0.92, edgecolor="#aaaaaa")
    ax.set_title(
        "OSM Road Network — {}\nIVD Modulator S  |S|={}  |  Min TDS={}".format(
            label, len(modulator_osm), tds_size),
        fontsize=13, fontweight="bold")
    ax.axis("off")
    plt.tight_layout()
    plt.savefig("itds_modulator.png", dpi=150, bbox_inches="tight")
    print("  Image 1 saved -> itds_modulator.png  (IVD modulator)")
    plt.close(fig)
    return "itds_modulator.png"


def visualize_interval_tds(G_nx, modulator_osm, tds_osm, label, tds_size):
    pos = {n: (G_nx.nodes[n]["x"], G_nx.nodes[n]["y"]) for n in G_nx.nodes()}
    node_colors, node_sizes = [], []
    for n in G_nx.nodes():
        in_tds = n in tds_osm
        in_mod = n in modulator_osm
        if in_tds and in_mod:
            node_colors.append("#6c3483"); node_sizes.append(200)   # dark purple
        elif in_tds:
            node_colors.append("#27ae60"); node_sizes.append(80)    # green
        elif in_mod:
            node_colors.append("#a569bd"); node_sizes.append(150)   # light purple
        else:
            node_colors.append("#111111"); node_sizes.append(20)

    fig, ax = plt.subplots(figsize=(12, 9))
    nx.draw_networkx_edges(G_nx, pos, ax=ax, edge_color="#111111", width=0.8, alpha=0.6)
    nx.draw_networkx_nodes(G_nx, pos, ax=ax, node_color=node_colors, node_size=node_sizes)
    annotate_corner_leaves(ax, G_nx)
    ax.legend(handles=[
        mpatches.Patch(color="#27ae60", label="In TDS — interval vertex"),
        mpatches.Patch(color="#6c3483", label="In TDS — modulator vertex"),
        mpatches.Patch(color="#a569bd", label="Modulator — NOT in TDS"),
        mpatches.Patch(color="#111111", label="Not in TDS"),
    ], fontsize=10, loc="lower right", frameon=True, framealpha=0.92, edgecolor="#aaaaaa")
    ax.set_title(
        "Minimum Total Dominating Set (Interval) — {}\nMin TDS size = {}".format(
            label, tds_size),
        fontsize=13, fontweight="bold")
    ax.axis("off")
    plt.tight_layout()
    plt.savefig("itds_result.png", dpi=150, bbox_inches="tight")
    print("  Image 2 saved -> itds_result.png  (Interval TDS placement)")
    plt.close(fig)
    return "itds_result.png"


def save_satellite_interval_tds(lat, lon, radius, label, G_nx, modulator_osm, tds_osm):
    if not _HAS_CONTEXTILY:
        print("  Skipping satellite image (contextily not installed).")
        return None
    fwd = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    pos_merc = {n: fwd.transform(G_nx.nodes[n]["x"], G_nx.nodes[n]["y"]) for n in G_nx.nodes()}
    xs = [p[0] for p in pos_merc.values()]
    ys = [p[1] for p in pos_merc.values()]
    pad = radius * 0.25
    west, east   = min(xs) - pad, max(xs) + pad
    south, north = min(ys) - pad, max(ys) + pad

    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_xlim(west, east); ax.set_ylim(south, north)
    try:
        ctx.add_basemap(ax, crs="EPSG:3857",
                        source=ctx.providers.Esri.WorldImagery,
                        zoom="auto", attribution=False)
    except Exception as e:
        print("  Could not fetch satellite tiles:", e)
        plt.close(fig); return None

    for u, v in G_nx.edges():
        x0, y0 = pos_merc[u]; x1, y1 = pos_merc[v]
        ax.plot([x0, x1], [y0, y1], color="white", linewidth=1.2, alpha=0.75, zorder=2)
    for n in G_nx.nodes():
        x, y = pos_merc[n]
        in_tds = n in tds_osm; in_mod = n in modulator_osm
        if in_tds and in_mod:   color, size, zorder = "#6c3483", 60, 5
        elif in_tds:            color, size, zorder = "#27ae60", 35, 4
        elif in_mod:            color, size, zorder = "#a569bd", 50, 5
        else:                   color, size, zorder = "#ffffff", 15, 3
        ax.scatter(x, y, s=size, c=color, zorder=zorder, edgecolors="black", linewidths=0.4)

    cx, cy = fwd.transform(lon, lat)
    ax.add_patch(plt.Circle((cx, cy), radius, color="violet",
                             fill=False, linewidth=1.5, linestyle="--", alpha=0.8, zorder=6))
    ax.plot(cx, cy, "m+", markersize=10, markeredgewidth=1.5, zorder=7)
    ax.legend(handles=[
        mpatches.Patch(color="#27ae60", label="In TDS — interval"),
        mpatches.Patch(color="#6c3483", label="In TDS — modulator"),
        mpatches.Patch(color="#a569bd", label="Modulator — NOT in TDS"),
        mpatches.Patch(color="#ffffff", label="Not in TDS", edgecolor="black", linewidth=0.5),
    ], fontsize=9, loc="lower right", frameon=True, framealpha=0.85, edgecolor="#aaaaaa")
    ax.set_axis_off()
    ax.set_title(
        "Satellite View (Interval TDS) — {}\n({}, {})  r={}m".format(label, lat, lon, radius),
        fontsize=13, fontweight="bold", pad=10)
    plt.tight_layout()
    plt.savefig("itds_satellite.png", dpi=150, bbox_inches="tight")
    print("  Image 3 saved -> itds_satellite.png")
    plt.close(fig)
    return "itds_satellite.png"


# ===========================================================================
# SECTION E: BRANCH RUNNERS
# ===========================================================================

def run_cluster_branch(G_nx, label, args, results, st_status=None):
    """Almost Cluster Graph: CVD modulator -> Min Secure Dominating Set."""
    print("\n  [Cluster Branch] Compressing graph ...")
    if st_status: st_status.update(label="Compressing graph...", state="running")
    G_small = compress(G_nx)

    print("  [Cluster Branch] Finding CVD modulator ...")
    if st_status: st_status.update(label="Finding CVD Modulator...", state="running")
    modulator_osm = set(find_cvd_minimal(G_small)) if G_small.number_of_nodes() > 0 else set()

    results['modulator_size'] = len(modulator_osm)
    print("  CVD Modulator S ({} nodes)".format(len(modulator_osm)))

    print("\n  [Cluster Branch] Running FPT SDS solver ...")
    if st_status: st_status.update(label="Running SDS solver...", state="running")

    S_nodes = list(modulator_osm)
    _, cliques = get_cvd_and_cliques(G_nx, S_nodes)
    sds_result = solve_msds_fpt(G_nx, S_nodes, cliques)

    if sds_result is None:
        raise ValueError("No valid SDS found.")

    sds_osm = set(sds_result)
    results['ds_size'] = len(sds_osm)
    results['ds_type'] = 'SDS'

    print("\n" + "=" * 50)
    print("  RESULT: Minimum SDS size: {}".format(len(sds_osm)))
    valid = is_secure_dominating(G_nx, sds_result)
    print("  Verification: {}".format("Valid ✓" if valid else "INVALID ✗"))
    print("=" * 50)

    if st_status: st_status.update(label="Generating visualizations...", state="running")
    results['img_modulator'] = visualize_cvd_modulator(G_nx, modulator_osm, label)
    results['img_ds']        = visualize_sds(G_nx, modulator_osm, sds_osm, label, len(sds_osm))

    img3 = None
    if args.point:
        img3 = save_satellite_sds(args.point[0], args.point[1], args.radius,
                                   label, G_nx, modulator_osm, sds_osm)
    elif args.bbox:
        mid_lat = (args.bbox[0] + args.bbox[1]) / 2
        mid_lon = (args.bbox[2] + args.bbox[3]) / 2
        approx_r = int(((args.bbox[0] - args.bbox[1])**2 +
                         (args.bbox[2] - args.bbox[3])**2)**0.5 * 55000)
        img3 = save_satellite_sds(mid_lat, mid_lon, approx_r,
                                   label, G_nx, modulator_osm, sds_osm)
    if img3:
        results['img_satellite'] = img3
    return results


def run_block_branch(G_nx, label, args, results, st_status=None):
    """Almost Block Graph: BGD modulator -> Min Total Dominating Set (C++ solver)."""
    if not _HAS_BGD:
        raise ImportError("block_graph_deletion.py not found. Cannot run Almost Block Graph mode.")

    print("\n  [Block Branch] Compressing graph ...")
    if st_status: st_status.update(label="Compressing graph...", state="running")
    G_small = compress(G_nx)

    G_bgd, n2i, i2n = nx_to_bgd(G_small)
    if is_block_graph(G_bgd):
        print("  Already a block graph — modulator is empty.")
        modulator_osm = set()
    else:
        if st_status: st_status.update(label="Finding BGD Modulator...", state="running")
        sol = _find_bgd_modulator(G_bgd, args.k)
        if sol is None:
            raise ValueError("No BGD modulator found with k<={}".format(args.k))
        modulator_osm = {i2n[i] for i in sol}

    results['modulator_size'] = len(modulator_osm)
    print("  BGD Modulator S ({} nodes)".format(len(modulator_osm)))

    print("\n  [Block Branch] Building C++ solver input ...")
    if st_status: st_status.update(label="Running TDS solver...", state="running")
    cpp_input, osm2idx = _build_cpp_input(G_nx, modulator_osm)
    with open("tds_input.txt", "w") as f:
        f.write(cpp_input)

    exe = _find_cpp_exe()
    tds_size, tds_vertices_idx = _run_cpp(exe, cpp_input)
    if tds_size is None:
        raise ValueError("No valid TDS found.")

    results['ds_size'] = tds_size
    results['ds_type'] = 'TDS'
    print("\n" + "=" * 50)
    print("  RESULT: Minimum TDS size: {}".format(tds_size))
    print("=" * 50)

    tds_osm = _reconstruct_tds(G_nx, osm2idx, tds_vertices_idx)

    if st_status: st_status.update(label="Generating visualizations...", state="running")
    results['img_modulator'] = visualize_modulator(G_nx, modulator_osm, label, tds_size)
    results['img_ds']        = visualize_tds(G_nx, modulator_osm, tds_osm, label, tds_size)

    img3 = None
    if args.point:
        img3 = save_satellite_image(args.point[0], args.point[1], args.radius,
                                     label, G_nx, modulator_osm, tds_osm)
    elif args.bbox:
        mid_lat = (args.bbox[0] + args.bbox[1]) / 2
        mid_lon = (args.bbox[2] + args.bbox[3]) / 2
        approx_r = int(((args.bbox[0] - args.bbox[1])**2 +
                         (args.bbox[2] - args.bbox[3])**2)**0.5 * 55000)
        img3 = save_satellite_image(mid_lat, mid_lon, approx_r,
                                     label, G_nx, modulator_osm, tds_osm)
    if img3:
        results['img_satellite'] = img3
    return results


def run_interval_branch(G_nx, label, args, results, st_status=None):
    """Almost Interval Graph: IVD modulator -> Min Total Dominating Set (Python FPT)."""
    print("\n  [Interval Branch] Compressing graph ...")
    if st_status: st_status.update(label="Compressing graph...", state="running")
    G_small = compress(G_nx)

    print("  [Interval Branch] Finding IVD modulator ...")
    if st_status: st_status.update(label="Finding IVD Modulator...", state="running")

    # Convert compressed graph to adjacency dict for interval solver
    adj_small = nx_to_adj(G_small) if G_small.number_of_nodes() > 0 else {}
    modulator_osm = extract_ivd_modulator(adj_small) if adj_small else set()

    results['modulator_size'] = len(modulator_osm)
    print("  IVD Modulator S ({} nodes)".format(len(modulator_osm)))

    print("\n  [Interval Branch] Running FPT TDS solver ...")
    if st_status: st_status.update(label="Running Interval TDS solver...", state="running")

    # Solve on the full graph using the modulator found on compressed graph
    adj_full = nx_to_adj(G_nx)
    tds_result = solve_tds_almost_interval(adj_full, modulator_osm)

    if tds_result is None:
        raise ValueError("No valid TDS found for almost-interval graph.")

    tds_osm = set(tds_result)
    results['ds_size'] = len(tds_osm)
    results['ds_type'] = 'TDS (Interval)'

    # Verify result
    tds_set   = set(tds_result)
    dominated = all(any(nb in tds_set for nb in adj_full.get(v, set())) for v in adj_full)
    total     = all(any(nb in tds_set for nb in adj_full.get(u, set())) for u in tds_set)

    print("\n" + "=" * 50)
    print("  RESULT: Minimum TDS size: {}".format(len(tds_osm)))
    print("  Dominated: {}  |  Total: {}".format(
        "✓" if dominated else "✗",
        "✓" if total     else "✗"
    ))
    print("=" * 50)

    if st_status: st_status.update(label="Generating visualizations...", state="running")
    results['img_modulator'] = visualize_ivd_modulator(
        G_nx, modulator_osm, label, len(tds_osm))
    results['img_ds'] = visualize_interval_tds(
        G_nx, modulator_osm, tds_osm, label, len(tds_osm))

    img3 = None
    if args.point:
        img3 = save_satellite_interval_tds(
            args.point[0], args.point[1], args.radius,
            label, G_nx, modulator_osm, tds_osm)
    elif args.bbox:
        mid_lat = (args.bbox[0] + args.bbox[1]) / 2
        mid_lon = (args.bbox[2] + args.bbox[3]) / 2
        approx_r = int(((args.bbox[0] - args.bbox[1])**2 +
                         (args.bbox[2] - args.bbox[3])**2)**0.5 * 55000)
        img3 = save_satellite_interval_tds(
            mid_lat, mid_lon, approx_r,
            label, G_nx, modulator_osm, tds_osm)
    if img3:
        results['img_satellite'] = img3
    return results


# ===========================================================================
# SECTION F: BLOCK BRANCH — INTERNAL HELPERS
# ===========================================================================

def _find_bgd_modulator(G_bgd, max_k):
    print("  Finding BGD modulator (trying k=1,2,...) ...")
    for k in range(1, max_k + 1):
        print("    k={} ...".format(k), end=" ", flush=True)
        sol = block_graph_deletion(G_bgd, k)
        if sol is not None:
            print("found! |S|={}".format(len(sol)))
            return sol
        print("no")
    print("  No modulator found with k<={}".format(max_k))
    return None


def _build_cpp_input(G_nx_full, modulator_osm_ids):
    nodes = list(G_nx_full.nodes())
    osm2idx = {osm: i + 1 for i, osm in enumerate(nodes)}
    N = len(nodes); edges = list(G_nx_full.edges()); M = len(edges)
    S = [osm2idx[osm] for osm in modulator_osm_ids if osm in osm2idx]; K = len(S)
    lines = ["{} {}".format(N, M)]
    for u, v in edges:
        lines.append("{} {}".format(osm2idx[u], osm2idx[v]))
    lines.append(str(K))
    lines.append(" ".join(str(s) for s in S))
    return "\n".join(lines), osm2idx


def _find_cpp_exe():
    folder = os.path.dirname(os.path.abspath(__file__))
    for name in ["mintds_opt_new.exe", "mintds_opt_new"]:
        exe_path = os.path.join(folder, name)
        if os.path.exists(exe_path):
            print("  Found solver: {}".format(exe_path))
            return exe_path
    raise RuntimeError("mintds_opt executable not found in " + folder)


def _run_cpp(exe_path, input_str):
    print("  Running TDS solver ...")
    result = subprocess.run([exe_path], input=input_str,
                            capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print("  Solver error:", result.stderr); return None, None
    tds_size = None; tds_vertices_idx = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("Minimum TDS size:"):
            tds_size = int(line.split("Minimum TDS size:")[1].strip())
        elif line.startswith("TDS vertices:"):
            parts = line.split("TDS vertices:")[1].strip().split()
            tds_vertices_idx = list(map(int, parts)) if parts else []
    return tds_size, tds_vertices_idx


def _reconstruct_tds(G_nx, osm2idx, tds_vertices_idx):
    idx2osm = {v: osm for osm, v in osm2idx.items()}
    if tds_vertices_idx:
        return {idx2osm[i] for i in tds_vertices_idx if i in idx2osm}
    print("  Solver did not output TDS vertices — using greedy for visualisation")
    adj = {n: list(G_nx.neighbors(n)) for n in G_nx.nodes()}
    uncovered = set(G_nx.nodes()); D = set()
    while uncovered:
        best = max(G_nx.nodes(), key=lambda v: sum(1 for u in adj[v] if u in uncovered))
        D.add(best)
        for u in adj[best]: uncovered.discard(u)
    changed = True
    while changed:
        changed = False
        for v in list(D):
            if not any(u in D for u in adj[v]):
                D.add(max(adj[v], key=lambda u: G_nx.degree(u))); changed = True
    return D


# ===========================================================================
# SECTION G: UNIFIED PIPELINE ENTRY POINT  (called by app.py / Streamlit)
# ===========================================================================

class PipelineArgs:
    def __init__(self, point=None, bbox=None, place=None,
                 radius=200, k=10, maxnodes=500,
                 network="drive", graph_type="cluster"):
        self.point      = point
        self.bbox       = bbox
        self.place      = place
        self.radius     = radius
        self.k          = k
        self.maxnodes   = maxnodes
        self.network    = network
        # "cluster"   ->  CVD  + Min SDS  (msds_solver.py)
        # "block"     ->  BGD  + Min TDS  (C++ solver)
        # "interval"  ->  IVD  + Min TDS  (interval_tds_solver.py)
        self.graph_type = graph_type


def run_pipeline_for_ui(args, st_status=None):
    results = {}
    mode_labels = {
        "cluster":  "Almost Cluster Graph   (CVD + Min SDS)",
        "block":    "Almost Block Graph     (BGD + Min TDS)",
        "interval": "Almost Interval Graph  (IVD + Min TDS)",
    }
    print("\n=== OSM Pipeline: {} ===\n".format(
        mode_labels.get(args.graph_type, args.graph_type)))

    G_nx, label = fetch_osm(args, st_status)
    results['nodes']      = G_nx.number_of_nodes()
    results['edges']      = G_nx.number_of_edges()
    results['graph_type'] = args.graph_type

    if args.graph_type == "cluster":
        results = run_cluster_branch(G_nx, label, args, results, st_status)
    elif args.graph_type == "block":
        results = run_block_branch(G_nx, label, args, results, st_status)
    elif args.graph_type == "interval":
        results = run_interval_branch(G_nx, label, args, results, st_status)
    else:
        raise ValueError("Unknown graph_type: {}".format(args.graph_type))

    if st_status: st_status.update(label="Complete!", state="complete")
    return results


# ===========================================================================
# SECTION H: CLI ENTRY POINT
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(
        description="OSM -> Graph Deletion -> Min Dominating Set Pipeline",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--graph-type", choices=["cluster", "block", "interval"], default="cluster",
        help=(
            "Graph structure assumption:\n"
            "  cluster   ->  Almost Cluster Graph:  CVD modulator + Min Secure DS   (msds_solver.py)\n"
            "  block     ->  Almost Block Graph:    BGD modulator + Min Total DS    (C++ solver)\n"
            "  interval  ->  Almost Interval Graph: IVD modulator + Min Total DS    (interval_tds_solver.py)"
        )
    )
    area = parser.add_mutually_exclusive_group(required=True)
    area.add_argument("--point", nargs=2, type=float, metavar=("LAT", "LON"),
                      help="Centre lat/lon + radius. E.g.: --point 13.08 80.27")
    area.add_argument("--bbox",  nargs=4, type=float, metavar=("N", "S", "E", "W"),
                      help="Bounding box. E.g.: --bbox 13.09 13.07 80.28 80.26")
    area.add_argument("--place", type=str,
                      help="Place name. E.g.: --place 'Mylapore, Chennai'")

    parser.add_argument("--radius",   type=int, default=300,
                        help="Radius in metres around --point (default 300)")
    parser.add_argument("--k",        type=int, default=10,
                        help="Max BGD modulator size to try (default 10, block branch only)")
    parser.add_argument("--maxnodes", type=int, default=500,
                        help="Abort if graph exceeds this many nodes (default 500)")
    parser.add_argument("--network",  type=str, default="drive",
                        choices=["drive", "walk", "bike", "all"],
                        help="OSM network type (default: drive)")

    a = parser.parse_args()
    run_pipeline_for_ui(PipelineArgs(
        point      = tuple(a.point) if a.point else None,
        bbox       = tuple(a.bbox)  if a.bbox  else None,
        place      = a.place,
        radius     = a.radius,
        k          = a.k,
        maxnodes   = a.maxnodes,
        network    = a.network,
        graph_type = a.graph_type,
    ))


if __name__ == "__main__":
    main()
