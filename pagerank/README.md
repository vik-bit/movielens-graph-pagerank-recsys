# Assignment 3A — Graph Processing, PageRank, Pregel and PowerGraph

## 1. Course

IIIT Delhi, Big Data Analytics (Autumn 2026), Assignment 3A. Submitted by Bikram Mohanty.

## 2. Hardware

| Item | Value |
|---|---|
| Operating system | Microsoft Windows 11 Home Single Language (build 26300), x64 |
| CPU model | 12th Gen Intel(R) Core(TM) i7-1255U |
| Logical CPUs | 12 |
| RAM | 16 GB (15.7 GB usable) |

## 3. Software versions (exact output)

Every submitted output was produced in a Linux container that pins the required versions
([Dockerfile.spark](Dockerfile.spark); full capture in [environment.txt](environment.txt)):

```
$ python --version
Python 3.14.10
$ java -version
openjdk version "21.0.13" 2026-10-20
OpenJDK Runtime Environment (build 21.0.13+9-1-deb13u2-Debian)
OpenJDK 64-Bit Server VM (build 21.0.13+9-1-deb13u2-Debian, mixed mode, sharing)
$ pip freeze   (required packages)
graphframes-py==0.12.3
matplotlib==3.11.2
neo4j==6.4.1
networkx==3.7
pandas==3.1.0
pyspark==4.2.0
$ docker --version   (host)
Docker version 29.2.1, build a5c7197
```

GraphFrames JVM package: `io.graphframes:graphframes-spark4_2.13:0.12.3` (via `--packages`).

## 4. Dataset

* Programs take `--data-dir <PATH_TO_ml-100k>`; nothing is hard-coded. The final run used
  `../../data/ml-100k` (the archive extracted **outside** the submission folder; the dataset is
  not included in this ZIP).
* `ml-100k.zip` MD5 = `0e33842e24a9c977be4e0107933c0723` (matches the expected value).
* Checks: `u.data` = 100,000 rows, users 1..943, movies 1..1682, ratings 1..5
  (confirmed by `graph_stats.csv`).

## 5. Commands used to produce every output file

These are the commands the assignment requires. Run them from the submission root
(`pagerank/`) in an environment with the pinned versions:

```bash
python partA/graph_stats.py --data-dir <PATH_TO_ml-100k> --output partA/output/graph_stats.csv
python partA/partition_messages.py --data-dir <PATH_TO_ml-100k> --workers 4 8 16 32 --message-bytes 16 --iterations 10 --output partA/output/partition_messages.csv
python partA/pagerank_local.py --data-dir <PATH_TO_ml-100k> --iterations 10 --damping 0.85 --output-dir partA/output
spark-submit --master "local[*]" --packages io.graphframes:graphframes-spark4_2.13:0.12.3 partA/pregel_pagerank.py --data-dir <PATH_TO_ml-100k> --iterations 10 --damping 0.85 --output partA/output/pregel_pagerank.csv
python partA/powergraph_sim.py --data-dir <PATH_TO_ml-100k> --workers 8 --hub-degree 50000 --output-dir partA/output
```

| Output | Produced by |
|---|---|
| `graph_stats.csv` | `graph_stats.py` |
| `partition_messages.csv` | `partition_messages.py` |
| `pagerank_local.csv`, `pagerank_trace.csv` | `pagerank_local.py` |
| `pregel_pagerank.csv`, `pagerank_compare.csv` | `pregel_pagerank.py` (the compare file is written next to `--output`; it re-runs the local implementation with the same `--iterations`/`--damping`) |
| `powergraph_results.csv`, `powergraph_scaling.csv`, `powergraph_scaling.png` | `powergraph_sim.py` (scaling uses `--workers` and `--scaling-hub-degrees`, default `1000 10000 50000`) |

**Exactly how the final outputs were produced (Windows host).** Spark 4.2 does not start on
native Windows without Hadoop's `winutils.exe`, which is only distributed by unofficial
repositories. So the same five commands were run, unchanged, inside the pinned container
(Python 3.14.10, Java 21, the six packages). On Linux/macOS with the pinned versions, the
plain commands above work directly.

```bash
docker build -f Dockerfile.spark -t bda-a3a-spark .
docker run --rm -v "<PATH_TO_ml-100k>:/data/ml-100k:ro" -v "${PWD}:/work" -w /work bda-a3a-spark bash -c '
python partA/graph_stats.py --data-dir /data/ml-100k --output partA/output/graph_stats.csv
python partA/partition_messages.py --data-dir /data/ml-100k --workers 4 8 16 32 --message-bytes 16 --iterations 10 --output partA/output/partition_messages.csv
python partA/pagerank_local.py --data-dir /data/ml-100k --iterations 10 --damping 0.85 --output-dir partA/output
spark-submit --master "local[*]" --packages io.graphframes:graphframes-spark4_2.13:0.12.3 partA/pregel_pagerank.py --data-dir /data/ml-100k --iterations 10 --damping 0.85 --output partA/output/pregel_pagerank.csv
python partA/powergraph_sim.py --data-dir /data/ml-100k --workers 8 --hub-degree 50000 --output-dir partA/output'
```

An earlier run of the four non-Spark scripts on the Windows host (Python 3.14.4) produced
byte-identical CSVs.

### Key results

| Check | Result |
|---|---|
| Fixed graph invariants | 2625 / 943 / 1682 vertices, 100,000 logical and 200,000 directed edges, ratings 1..5 ✔ |
| Max-degree user / movie | user 405 (degree 737) / movie 50 *Star Wars* (degree 583) |
| Rank sum, iterations 0..10 | 1.0 at every iteration (error < 1e-15) |
| Top PageRank vertices | user 405, user 655, user 181, user 13, movie 50 |
| Pregel vs local (10 iterations) | max abs diff **2.6e-18**, mean 7.5e-20 (limit 1e-8) |
| Remote fraction P = 4/8/16/32 | 0.751 / 0.876 / 0.938 / 0.969 |
| HUB-GRAPH, P=8, H=50,000 | vertex-partition imbalance 2.129 (hub owner = worker 0, work 79,837 vs mean 37,500); edge-partition imbalance 1.000; replication factor 1.292; hub replicas 8; GAS sync messages 30,738 |

Non-default parameters were also tested (as a TA would): `--workers 7` (local + remote = 200,000;
remote fraction 0.857), `--workers 7 --hub-degree 5000` (imbalance 1.131, hub on worker 3,
7 replicas) and `--iterations 4` for both PageRank programs (max diff 2.6e-18).

## 6. Interpretation answers

### A2 — Why communication matters even on one laptop (≤120 words)

The laptop only *simulates* P workers, but the counts show what a cluster would ship. With
`owner(v)=v mod P`, 75–97 % of the 200,000 PageRank messages per iteration cross workers
(87.6 % at P=8: about 2.8 MB per iteration, 28 MB over 10 iterations), and the remote share
rises with P. On a real cluster each remote message is serialized, sent over the network and
deserialized, which is far slower than the one multiply-add it carries. BSP also makes every
superstep wait for the slowest exchange. PageRank is therefore communication-bound, so
measuring the cut locally predicts scaling cost and motivates better partitioning or message
combiners.

### A4 — Mapping Pregel concepts to `partA/pregel_pagerank.py` (≤180 words)

| Concept | Line / expression |
|---|---|
| Vertex state | L57–59: `.withVertexColumn("rank", F.lit(1.0 / n), …)` — column `rank`, initialised to PR₀ = 1/N; `out_degree` is a static vertex attribute. |
| Message generation | L63: `.sendMsgToDst(Pregel.src("rank") / Pregel.src("out_degree"))` — every directed edge u→v sends PRₜ(u)/out_degree(u). |
| Message aggregation | L65: `.aggMsgs(F.sum(Pregel.msg()))` — messages to the same destination are summed. |
| Vertex update | L60: update expression `(1-d)/N + d * coalesce(Pregel.msg(), 0)` — the third argument of `withVertexColumn` (after the name and the initial value). |
| Superstep | L52: `.setMaxIter(iterations)` with `setEarlyStopping(False)`; `.run()` (L66) executes exactly `iterations` supersteps, each = message generation → aggregation → update, with a global barrier between them. |

### A5 — Why a vertex cut helps a hub despite replicas (≤150 words)

With vertex partitioning, the hub (owned by worker 0) and all 50,000 of its adjacency entries
sit on one worker. Worker 0 does 79,837 units of work against a mean of 37,500 (imbalance
2.13). Every superstep ends at a barrier, so the other workers idle until it finishes. The
vertex cut assigns *edges* round-robin, spreading the hub's edges over all 8 workers
(imbalance 1.00), and each worker gathers a partial sum over its local hub edges in parallel.
The price is replication: the hub's 8 replicas cost 2·(8−1) = 14 synchronization messages per
GAS iteration. That cost depends on the number of workers, not on the hub's degree, so 14 small
messages replace 50,000 extra edge operations on one straggler. The benefit grows with H:
vertex imbalance rises from 1.10 to 2.13 for H = 1k to 50k, while edge imbalance stays at 1.00.

## 7. Known limitations / deviations

1. **Run inside a Linux container on a Windows laptop.** Spark 4.2 needs Hadoop `winutils.exe`
   on Windows, so every output was produced in a container with exactly Python 3.14.10,
   Java 21 (OpenJDK 21.0.13) and the six pinned packages. The program names, arguments and
   output paths are unchanged. The container runs in Docker Desktop's WSL2 VM, which sees the
   laptop's 12 logical CPUs.
2. **`typing_extensions` shim.** `graphframes-py 0.12.3` imports `typing_extensions.Self` but
   does not declare that package as a dependency. Rather than add a seventh package to
   `requirements.txt`, `pregel_pagerank.py` adds a 6-line shim when the module is missing. It
   maps the name to the identical standard-library `typing.Self` (Python ≥ 3.11). It has no
   effect when `typing_extensions` is already installed.
3. **Interpretation of "number_of_original_vertices"** (replication factor): all logical
   vertices of HUB-GRAPH (2625 MovieLens + 1 hub + H synthetic users), each counted once. For
   P=8, H=50,000 that is 67,995 replicas / 52,626 vertices = 1.292. The value falls as H grows
   because many degree-1 synthetic users each add one replica. Counting only the 2625
   MovieLens vertices would instead give 17,987 / 2,625 = 6.85. `gas_sync_messages` stays at
   30,738 for every H because the hub always has P replicas and the synthetic users add none.
4. With P=8 the round-robin edge assignment gives a perfectly even split
   (|E_HUB| = 150,000 is divisible by 8), so edge imbalance is exactly 1.0. Other P values
   (e.g. 7) give slightly uneven splits, and the program handles them generally.
5. `pagerank_trace.csv` reports `l1_change = 0` for iteration 0 (there is no previous vector).
   Vertex-type labels are `user` / `movie`.
