"""A4: the same PageRank on G_D using the GraphFrames Pregel API (not graph.pageRank()).

Run (from the submission root):
  spark-submit --master "local[*]" --packages io.graphframes:graphframes-spark4_2.13:0.12.3 \
      partA/pregel_pagerank.py --data-dir <PATH_TO_ml-100k> --iterations 10 --damping 0.85 \
      --output partA/output/pregel_pagerank.csv

Also writes pagerank_compare.csv next to --output, comparing against pagerank_local.py
(run with identical vertex IDs, iteration count and damping).
"""
import argparse
import csv
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# graphframes-py 0.12.3 imports `typing_extensions.Self` but does not declare the dependency.
# On Python >= 3.11 `typing.Self` is identical, so provide a tiny shim instead of adding a 7th
# package to requirements.txt (the assignment fixes exactly six pinned packages).
try:
    import typing_extensions  # noqa: F401
except ModuleNotFoundError:
    import types
    import typing
    _te = types.ModuleType("typing_extensions")
    _te.Self = typing.Self
    sys.modules["typing_extensions"] = _te

from pyspark.sql import SparkSession  # noqa: E402
from pyspark.sql import functions as F  # noqa: E402
from graphframes import GraphFrame  # noqa: E402
from graphframes.lib import Pregel  # noqa: E402

from common import directed_edges, read_ratings  # noqa: E402
from pagerank_local import ranked_rows, run_pagerank, write_rank_csv  # noqa: E402


def pregel_pagerank(spark, gd, iterations, damping):
    out_deg = {}
    for s, _ in gd:
        out_deg[s] = out_deg.get(s, 0) + 1
    n = len(out_deg)  # every vertex of G_D has out-degree >= 1

    vertices = spark.createDataFrame([(v, d) for v, d in out_deg.items()], "id LONG, out_degree LONG")
    edges = spark.createDataFrame(gd, "src LONG, dst LONG")
    g = GraphFrame(vertices, edges)

    result = (
        g.pregel
        .setMaxIter(iterations)                       # superstep count (exactly `iterations` updates)
        .setEarlyStopping(False)
        .setUseLocalCheckpoints(True)
        .setCheckpointInterval(2)
        # VERTEX STATE: column `rank`, initial PR_0 = 1/N; VERTEX UPDATE: (1-d)/N + d * aggregated msg
        .withVertexColumn(
            "rank",
            F.lit(1.0 / n),
            F.lit((1.0 - damping) / n) + F.lit(damping) * F.coalesce(Pregel.msg(), F.lit(0.0)),
        )
        # MESSAGE GENERATION: along every directed edge src->dst send PR_t(src)/out_degree(src)
        .sendMsgToDst(Pregel.src("rank") / Pregel.src("out_degree"))
        # MESSAGE AGGREGATION: sum of incoming messages per destination vertex
        .aggMsgs(F.sum(Pregel.msg()))
        .run()
    )
    return {int(r["id"]): float(r["rank"]) for r in result.select("id", "rank").collect()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--iterations", type=int, default=10)
    ap.add_argument("--damping", type=float, default=0.85)
    ap.add_argument("--output", default="partA/output/pregel_pagerank.csv")
    ap.add_argument("--compare-output", default=None,
                    help="default: pagerank_compare.csv in the same folder as --output")
    a = ap.parse_args()

    out_dir = os.path.dirname(os.path.abspath(a.output))
    os.makedirs(out_dir, exist_ok=True)
    compare_path = a.compare_output or os.path.join(out_dir, "pagerank_compare.csv")

    gd = directed_edges(read_ratings(a.data_dir))

    spark = SparkSession.builder.appName("A3A-Pregel-PageRank").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    try:
        pregel_pr = pregel_pagerank(spark, gd, a.iterations, a.damping)
    finally:
        spark.stop()

    write_rank_csv(a.output, pregel_pr)

    local_pr, _ = run_pagerank(gd, a.iterations, a.damping)
    assert set(local_pr) == set(pregel_pr), "vertex sets differ"
    diffs = [abs(local_pr[v] - pregel_pr[v]) for v in local_pr]
    row = {
        "iterations": a.iterations,
        "max_abs_difference": max(diffs),
        "mean_abs_difference": math.fsum(diffs) / len(diffs),
        "local_rank_sum": math.fsum(local_pr.values()),
        "pregel_rank_sum": math.fsum(pregel_pr.values()),
    }
    with open(compare_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        w.writeheader()
        w.writerow({k: (repr(v) if isinstance(v, float) else v) for k, v in row.items()})
    print(row)
    print("top 5 (pregel):", ranked_rows(pregel_pr)[:5])
    if row["max_abs_difference"] > 1e-8:
        print("WARNING: max_abs_difference exceeds 1e-8", file=sys.stderr)


if __name__ == "__main__":
    main()
