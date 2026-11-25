# LLM usage — Assignment 3A

## Tools used

* **Claude Code** (Anthropic, model Claude Opus 5.5) in the Claude desktop app. It read the
  assignment PDF and the course notes (Graph Frameworks / Pregel / GAS lecture, PageRank
  material), wrote and ran the scripts, and drafted the README. I reviewed the outputs and
  the explanations.

## Prompts that materially affected the implementation

1. *"Complete this assignment and check out the lecture slides for reference"* (with the
   assignment PDF attached). This produced the overall structure: `common.py` holds the
   vertex-ID convention (movie = 100000 + id) and `owner(v,P) = v mod P`, with one script per
   task and every parameter exposed as a CLI flag (no hard-coding).
2. My approval to run the Spark step in Docker ("Yes, use Docker") after native Windows failed.
   This led to `Dockerfile.spark`, which pins Python 3.14.10, Java 21 and the six packages.
3. *"Correct whatever you can and evaluate like a strict TA and make final changes."* This
   re-ran every output inside the pinned container, so no output depends on the host's
   Python 3.14.4 / Java 17. It also checked the word limits and the line references in the
   A4 mapping, and documented the replication-factor interpretation with both possible values.

## Where the LLM's first attempt was wrong / incomplete, and the fix

* **Running `spark-submit` on native Windows.** The first attempt called `spark-submit` from
  the Windows venv. Spark failed during `SparkContext` start-up with
  `HADOOP_HOME and hadoop.home.dir are unset`. Even a trivial `spark.range(5).count()`
  failed, which showed it was a Spark-on-Windows problem, not a GraphFrames one. Downloading
  `winutils.exe` from an unofficial GitHub repository was rejected as unsafe. The job ran in a
  pinned Linux container instead.
* **Missing dependency in `graphframes-py 0.12.3`.** `from graphframes.lib import Pregel`
  raised `ModuleNotFoundError: No module named 'typing_extensions'`. The obvious fix,
  `pip install typing_extensions`, would break the "exactly six packages" rule for
  `requirements.txt`. Instead, a 6-line shim maps `typing_extensions.Self` to the identical
  standard-library `typing.Self`.
* **Plot labels.** In the first `powergraph_scaling.png`, the edge-imbalance labels overlapped
  the x-axis. Setting explicit y-limits fixed it.

## How problems were detected

* Running every required command and reading the output or traceback.
* Checking the fixed invariants in `graph_stats.csv`.
* Asserting in code that `local + remote = 200000` and `sum(vertex work) = 2|E|`.
* Checking `rank_sum = 1` at every iteration.
* Comparing Pregel against the local PageRank: max abs difference 2.6e-18 for both 10 and 4
  iterations.
* Re-running with TA-style values (`--workers 7`, `--hub-degree 5000`, `--iterations 4`).
* Diffing the outputs from the Windows host and from the pinned container (byte-identical).

## A concept that became clearer

The vertex cut finally made sense to me through the numbers. Under vertex partitioning, the
hub's entire degree lands on the one worker that owns it (200000 mod 8 = worker 0). Its
imbalance grows linearly with H: 1.10, then 1.27, then 2.13 for H = 1k, 10k and 50k. Every
superstep has to wait for that worker. With a vertex cut, the hub's edges are spread evenly
(imbalance stays at 1.00). The extra cost is synchronizing the hub's replicas, which is
2·(P−1) = 14 messages. That cost depends on the number of workers, not on the hub's degree, so
it stays the same however large the hub grows. The bigger the hub, the more the trade-off
favours the vertex cut.
