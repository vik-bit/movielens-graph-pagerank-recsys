# Assignment 3B — Interactive Graph Queries and Recommendation

## 1. Course

IIIT Delhi, Big Data Analytics (Autumn 2026), Assignment 3B. Submitted by Bikram Mohanty.

## 2. Hardware

| Item | Value |
|---|---|
| Operating system | Microsoft Windows 11 Home Single Language (build 26300), x64 |
| CPU model | 12th Gen Intel(R) Core(TM) i7-1255U |
| Logical CPUs | 12 |
| RAM | 16 GB (15.7 GB usable) |

## 3. Software versions (exact output)

Every submitted output was produced by programs running in a Linux container that pins the
required versions ([Dockerfile.runtime](Dockerfile.runtime); full capture in
[environment.txt](environment.txt)):

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
$ docker inspect bda-neo4j --format "{{.Config.Image}}"
neo4j:2026.10.1
```

Neo4j was started exactly as specified:

```bash
docker volume create bda-neo4j-data
docker run -d --name bda-neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/bdaGraph2026 -v bda-neo4j-data:/data neo4j:2026.10.1
```

## 4. Dataset

* Programs take `--data-dir <PATH_TO_ml-100k>`; the final run used `../../data/ml-100k`
  (extracted outside the submission; the dataset is not included in this ZIP).
* `ml-100k.zip` MD5 = `0e33842e24a9c977be4e0107933c0723` (matches).
* Checks: `u1.base` 80,000 rows, `u1.test` 20,000 rows, `u.item` 1,682 movies (read as
  ISO-8859-1), `u.genre` 19 genres, `u.user` 943 users.
* **Only `u1.base` is used** to build Neo4j and the recommenders. `u1.test` is opened in exactly
  one place, `evaluate()` in `recommend.py`, after the training graph and the recommender are
  built, and only to define `RelevantTest(u)`.

## 5. Commands used to produce every output file

These are the commands the assignment requires. Run them from the submission root
(`recommendation/`) with the pinned packages and the `bda-neo4j` container running:

```bash
python partB/load_neo4j.py --data-dir <PATH_TO_ml-100k> --uri bolt://localhost:7687 --user neo4j --password bdaGraph2026 --reset
python partB/run_queries.py --uri bolt://localhost:7687 --user neo4j --password bdaGraph2026 --target-user 1 --like-threshold 4 --topk 10 --output-dir partB/output
python partB/recommend.py --data-dir <PATH_TO_ml-100k> --users 1 50 100 --like-threshold 4 --neighbors 20 --topk 10 --output-dir partB/output
```

**Exactly how the final outputs were produced (Windows host).** The same three commands ran,
unchanged, inside the pinned Python 3.14.10 container. The container shares the Neo4j
container's network namespace, so `bolt://localhost:7687` still works:

```bash
docker build -f Dockerfile.runtime -t bda-a3a-spark .
docker run --rm --network container:bda-neo4j -v "<PATH_TO_ml-100k>:/data/ml-100k:ro" -v "${PWD}:/work" -w /work bda-a3a-spark bash -c '
python partB/load_neo4j.py --data-dir /data/ml-100k --uri bolt://localhost:7687 --user neo4j --password bdaGraph2026 --reset
python partB/run_queries.py --uri bolt://localhost:7687 --user neo4j --password bdaGraph2026 --target-user 1 --like-threshold 4 --topk 10 --output-dir partB/output
python partB/recommend.py --data-dir /data/ml-100k --users 1 50 100 --like-threshold 4 --neighbors 20 --topk 10 --output-dir partB/output'
```

`q3_profile.png` was produced in Neo4j Browser (see limitation 1). An earlier run of all three
scripts on the Windows host (Python 3.14.4) produced identical result CSVs; only the
`median_ms` timings differed.

| Output | Produced by |
|---|---|
| `db_counts.csv` | `load_neo4j.py` |
| `q1.csv` … `q4.csv` | `run_queries.py` (reads `partB/queries/*.cypher`, passes `$target_user`, `$like_threshold`, `$topk`) |
| `path_growth.csv` | `run_queries.py` (1 warm-up + 5 timed runs per L; `--skip-path-growth` to skip; L=4 takes ≈ 5 min in total) |
| `q3_profile.png` | Neo4j Browser PROFILE export (see limitation 1) |
| `q3_profile_plan.txt`, `q3_profile_rendered.png` | `run_queries.py` — driver-side `PROFILE` of Q3 (cross-check) |
| `recommendations.csv`, `evaluation.csv` | `recommend.py` (`--eval-k` defaults to 10) |

The loader was run twice (once with `--reset`, once without); both runs gave identical counts,
confirming idempotency. Load time ≈ 20 s (UNWIND batches of 1000, MERGE, uniqueness constraints
on `User.id`, `Movie.id`, `Genre.id` created before loading).

### db_counts.csv

| metric | value |
|---|---|
| users | 943 |
| movies | 1682 |
| genres | 19 |
| rated_relationships | 80000 |
| in_genre_relationships | 2893 (= number of 1-flags in the 19 genre columns of `u.item`) |

### Query results for the default run (user 1, threshold 4, topk 10)

* Q1: ten 5-star movies, ties broken by `movie_id` (1 *Toy Story*, 9, 13, 15, …).
* Q2: top similar user 592 (53 common likes), then 474 and 864 (44 each — tie broken by id).
* Q3: Fargo (309 supporters), Raiders of the Lost Ark (285), Silence of the Lambs (260), …
* Q4: same top candidates with genre restriction (Fargo 302 / 3 shared genres, …).
* Method A for user 1 in `recommendations.csv` reproduces Q3 exactly (same movies, same support
  values), cross-validating the Cypher and Python implementations.

Non-default runs were also checked (`--target-user 50 --like-threshold 5 --topk 5`,
`recommend.py --users 50 --like-threshold 5 --neighbors 5 --topk 5`): all files regenerate and
every recommended movie is absent from the user's training ratings (asserted in code).

## 6. Interpretation answers

### B4 — Path growth and Q3 PROFILE

| path_length | matched_paths | distinct_end_vertices | median_ms |
|---|---|---|---|
| 1 | 84 | 84 | 16.3 |
| 2 | 8,625 | 856 | 26.5 |
| 3 | 734,937 | 1,401 | 349.8 |
| 4 | 70,572,032 | 942 | 38,046.8 |

Matched paths grow by roughly ×85–100 per hop (about the average "liked" degree), while
distinct end vertices saturate: 856 of the 943 users by L=2, and 942 users again at L=4. For
L ≤ 2 the time is fixed query overhead. From L=3 on, time grows with the path count rather than
the result size: about 0.35 s for 0.73 M paths, then about 38 s for 70.6 M paths, which reach
only 942 vertices. This is why multi-hop queries must aggregate early or be bounded.

**Q3 PROFILE (default parameters):** final result **10 rows** (1,266 candidate movies before
`Top`), 71.2 M total DB hits. Two expensive operators:

1. **`Expand(Into)` under `AntiSemiApply`** — the `NOT EXISTS { (u)-[:RATED]->(b) }` check runs
   once for each of the 734,937 three-hop rows, costing **66.7 M DB hits** (≈ 94 % of the
   total).
2. **`Expand(All)` `(x)-[r3:RATED]->(b)`** — the third hop expands 8,625 rows into **1,300,696
   rows** (1.3 M DB hits), and the following `Filter` on `r3.rating` costs another 2.0 M DB
   hits.

### B5 — Interactive query vs global computation (≤120 words)

| Property | Q3 interactive recommendation query | Global PageRank |
|---|---|---|
| Starting scope | One seed vertex (`$target_user`) | Every vertex at once |
| Graph portion touched | Local 3-hop neighbourhood reachable through likes | Whole graph, every edge, every iteration |
| Iterative global synchronization? | No — one traversal, answer in milliseconds | Yes — barrier after each of many iterations |
| Natural system | Graph database (Neo4j, index seek + pointer chasing) | Graph-parallel engine (Pregel/GraphFrames, PowerGraph) |
| Typical use | Online, per-request recommendations/lookups | Offline batch scoring (ranks) reused later |

### B8 — Bridge to collaborative filtering (≤220 words)

1. **Neighbour in Method B:** a user whose set of *liked* training movies overlaps the target
   user's; the top-`neighbors` users by Jaccard similarity act as the target's "taste peers".
2. **Why weight by similarity:** Jaccard 0.8 means the two users agree on most of their likes,
   so their other likes are strong evidence about the target's taste; 0.1 overlap may be
   coincidence (e.g. both liked a blockbuster). Weighting makes score_B a similarity-weighted
   vote, so close neighbours dominate and noisy ones contribute little — which raised
   Precision@10 from 0.247 (Method A, every supporter counts 1) to 0.355.
3. **Information lost by thresholding:** the strength of preference (5 vs 4), all explicit
   dislikes (1–2 are treated the same as "not rated"), and each user's rating scale/bias (a
   harsh rater's 3 may mean "liked").
4. **Using actual ratings:** user-user CF predicts a numeric rating with a mean-centred,
   similarity-weighted average over neighbours N(u) who rated m:
   `r̂(u,m) = r̄_u + Σ_{v∈N(u)} sim(u,v)·(r_vm − r̄_v) / Σ_{v∈N(u)} |sim(u,v)|`,
   with sim(u,v) e.g. Pearson/cosine on co-rated movies (item-item CF uses the symmetric
   formula over similar movies).

### B6/B7 — Evaluation summary (`evaluation.csv`)

| method | eligible_users | mean P@10 | mean R@10 | users with ≥1 hit |
|---|---|---|---|---|
| A (common-neighbour support) | 456 | 0.2471 | 0.1347 | 376 |
| B (Jaccard-weighted, 20 neighbours) | 456 | 0.3553 | 0.2088 | 406 |

Method A favours globally popular movies (support counts every weak supporter equally), while
Method B personalises through the 20 most similar users.

## 7. Known limitations / deviations

1. **`q3_profile.png` is Neo4j Browser's own "Download diagram PNG" export** of the PROFILE
   plan, not a screen capture. The whole plan is too tall for one browser screen, and the export
   keeps every operator readable. To reproduce it: open http://localhost:7474, log in (neo4j /
   bdaGraph2026), run `:param {target_user: 1, like_threshold: 4, topk: 10}`, run `PROFILE`
   followed by the contents of `q3_candidates.cypher`, switch the plan to *Diagram view*, then
   choose ⤓ → *Download diagram PNG*. Browser reports 10 result rows, 71,187,146 total
   database accesses and 5,843 ms. That DB-hit total matches the driver-side PROFILE that
   `run_queries.py` writes to `q3_profile_plan.txt` and `q3_profile_rendered.png`.
2. **Run inside a Linux container on a Windows laptop.** The three Python programs ran in a
   container with exactly Python 3.14.10 and the six pinned packages (Java 21 is also present
   but not used by Part B). They connected to the `neo4j:2026.10.1` container through
   `--network container:bda-neo4j`. Program names, arguments and output paths are unchanged.
3. Path growth uses a quantified path pattern
   `(()-[r:RATED WHERE r.rating >= $like_threshold]-()){L}` so the rating filter is applied
   during expansion; Cypher's default trail semantics apply (a relationship is not reused within
   a path, vertices may repeat). L is interpolated into the query text as a validated integer
   because a quantifier cannot be a parameter.
4. Q4 sort order: `support DESC, shared_genres DESC, movie_id ASC` as specified.
5. Precision@K always divides by K (=10) even if fewer than K candidates exist; Method B for a
   user with no liked training movies returns no recommendations.
