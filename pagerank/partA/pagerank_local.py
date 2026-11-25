"""A3: PageRank on G_D implemented as explicit message passing (no library PageRank).

For t = 0..iterations-1:
    every directed edge u->v sends PR_t(u)/out_degree(u) to v
    PR_{t+1}(v) = (1-d)/N + d * SUM(messages received by v)
"""
import argparse
import csv
import math
import os
from collections import defaultdict

from common import directed_edges, original_id, read_ratings, vertex_type, vertices_of


def run_pagerank(gd, iterations, damping):
    """Return (final rank dict, trace rows). Uses double precision throughout."""
    verts = vertices_of(gd)
    n = len(verts)
    out_deg = defaultdict(int)
    for s, _ in gd:
        out_deg[s] += 1
    assert all(out_deg[v] > 0 for v in verts), "G_D should have no dangling vertices"

    pr = {v: 1.0 / n for v in verts}
    trace = [{"iteration": 0, "rank_sum": math.fsum(pr.values()), "l1_change": 0.0}]
    for t in range(iterations):
        # superstep: message generation along every directed edge
        inbox = defaultdict(list)
        for s, d in gd:
            inbox[d].append(pr[s] / out_deg[s])
        # message aggregation + vertex update
        new_pr = {v: (1.0 - damping) / n + damping * math.fsum(inbox.get(v, ())) for v in verts}
        l1 = math.fsum(abs(new_pr[v] - pr[v]) for v in verts)
        pr = new_pr
        trace.append({"iteration": t + 1, "rank_sum": math.fsum(pr.values()), "l1_change": l1})
    return pr, trace


def ranked_rows(pr):
    rows = [(v, vertex_type(v), original_id(v), r) for v, r in pr.items()]
    rows.sort(key=lambda x: (-x[3], x[0]))  # pagerank DESC, vertex_id ASC
    return rows


def write_rank_csv(path, pr):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["vertex_id", "vertex_type", "original_id", "pagerank"])
        for v, t, o, r in ranked_rows(pr):
            w.writerow([v, t, o, repr(r)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--iterations", type=int, default=10)
    ap.add_argument("--damping", type=float, default=0.85)
    ap.add_argument("--output-dir", default="partA/output")
    a = ap.parse_args()

    gd = directed_edges(read_ratings(a.data_dir))
    pr, trace = run_pagerank(gd, a.iterations, a.damping)
    os.makedirs(a.output_dir, exist_ok=True)
    write_rank_csv(os.path.join(a.output_dir, "pagerank_local.csv"), pr)
    with open(os.path.join(a.output_dir, "pagerank_trace.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["iteration", "rank_sum", "l1_change"])
        w.writeheader()
        for row in trace:
            w.writerow({k: (repr(v) if isinstance(v, float) else v) for k, v in row.items()})
    for row in trace:
        print(row)
    print("top 5:", ranked_rows(pr)[:5])


if __name__ == "__main__":
    main()
