"""A5/A6: deterministic simulation of Pregel vertex partitioning vs PowerGraph vertex cut
on HUB-GRAPH = G_L + one hub movie (200000) connected to H synthetic users (300001..300000+H).
"""
import argparse
import csv
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from common import logical_edges, owner, read_ratings  # noqa: E402

HUB_ID = 200000
SYNTH_BASE = 300000


def hub_graph(base_edges, h):
    return list(base_edges) + [(SYNTH_BASE + i, HUB_ID) for i in range(1, h + 1)]


def simulate(edges, p):
    # ---- A5.2 Pregel-style vertex partition (edge-cut) ----
    deg = defaultdict(int)
    for a, b in edges:
        deg[a] += 1
        deg[b] += 1
    vwork = [0] * p
    for v, d in deg.items():
        vwork[owner(v, p)] += d
    assert sum(vwork) == 2 * len(edges)
    v_mean = sum(vwork) / p
    v_max = max(vwork)

    # ---- A5.3 PowerGraph-style edge partition (vertex-cut) ----
    pairs = sorted((min(a, b), max(a, b)) for a, b in edges)
    ework = [0] * p
    replicas = defaultdict(set)
    for edge_id, (a, b) in enumerate(pairs):
        w = edge_id % p
        ework[w] += 1
        replicas[a].add(w)
        replicas[b].add(w)
    e_mean = len(pairs) / p
    e_max = max(ework)
    replica_count = {v: len(ws) for v, ws in replicas.items()}
    # "original vertices" = the logical vertices of HUB-GRAPH (each counted once, not its replicas)
    replication_factor = sum(replica_count.values()) / len(deg)
    gas_sync = 2 * sum(c - 1 for c in replica_count.values())
    hub_owner = owner(HUB_ID, p)
    return {
        "workers": p,
        "hub_degree": deg[HUB_ID],
        "vertex_partition_max_work": v_max,
        "vertex_partition_mean_work": v_mean,
        "vertex_partition_imbalance": v_max / v_mean,
        "hub_owner": hub_owner,
        "hub_owner_work": vwork[hub_owner],
        "edge_partition_max_work": e_max,
        "edge_partition_mean_work": e_mean,
        "edge_partition_imbalance": e_max / e_mean,
        "replication_factor": replication_factor,
        "hub_replica_count": replica_count[HUB_ID],
        "gas_sync_messages": gas_sync,
        "hub_master": min(replicas[HUB_ID]),
    }


RESULT_COLS = ["workers", "hub_degree", "vertex_partition_max_work", "vertex_partition_mean_work",
               "vertex_partition_imbalance", "hub_owner", "hub_owner_work", "edge_partition_max_work",
               "edge_partition_mean_work", "edge_partition_imbalance", "replication_factor",
               "hub_replica_count", "gas_sync_messages"]
SCALING_COLS = ["hub_degree", "vertex_partition_imbalance", "edge_partition_imbalance",
                "replication_factor", "gas_sync_messages"]


def write_csv(path, cols, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--hub-degree", type=int, default=50000)
    ap.add_argument("--scaling-hub-degrees", type=int, nargs="+", default=[1000, 10000, 50000])
    ap.add_argument("--output-dir", default="partA/output")
    a = ap.parse_args()
    os.makedirs(a.output_dir, exist_ok=True)

    base = logical_edges(read_ratings(a.data_dir))

    res = simulate(hub_graph(base, a.hub_degree), a.workers)
    write_csv(os.path.join(a.output_dir, "powergraph_results.csv"), RESULT_COLS, [res])
    print(res)

    scaling = [simulate(hub_graph(base, h), a.workers) for h in a.scaling_hub_degrees]
    write_csv(os.path.join(a.output_dir, "powergraph_scaling.csv"), SCALING_COLS, scaling)

    xs = [r["hub_degree"] for r in scaling]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(xs, [r["vertex_partition_imbalance"] for r in scaling], marker="o",
            label="Pregel vertex partition (edge-cut) imbalance")
    ax.plot(xs, [r["edge_partition_imbalance"] for r in scaling], marker="s",
            label="PowerGraph edge partition (vertex-cut) imbalance")
    for r in scaling:
        ax.annotate(f'{r["vertex_partition_imbalance"]:.3f}', (r["hub_degree"], r["vertex_partition_imbalance"]),
                    textcoords="offset points", xytext=(0, 6), ha="center", fontsize=8)
        ax.annotate(f'{r["edge_partition_imbalance"]:.4f}', (r["hub_degree"], r["edge_partition_imbalance"]),
                    textcoords="offset points", xytext=(0, -14), ha="center", fontsize=8)
    top = max(r["vertex_partition_imbalance"] for r in scaling)
    ax.set_ylim(0.9, top + 0.1 * (top - 0.9) + 0.05)
    ax.set_xlabel("hub_degree H (linear scale)")
    ax.set_ylabel("load imbalance = max(work) / mean(work)")
    ax.set_title(f"Hub scaling, P = {a.workers} workers")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(a.output_dir, "powergraph_scaling.png"), dpi=150)
    for r in scaling:
        print({k: r[k] for k in SCALING_COLS})


if __name__ == "__main__":
    main()
