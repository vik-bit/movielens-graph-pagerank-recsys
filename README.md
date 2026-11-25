# MovieLens graph analytics: PageRank and graph recommendations

> **Coursework.** This is my submission for Assignment 3 of **Big Data Analytics (IIIT Delhi,
> Autumn 2026)**. The task, the dataset and the required outputs were set by the course; the code,
> measurements and write-ups are mine. It is published as a record of course work, not as a
> standalone project. See [AI assistance](#ai-assistance) for how it was built.

Both parts work on the MovieLens 100K ratings graph (943 users, 1,682 movies, 100,000 ratings).

| Part | What it does | Details |
|---|---|---|
| [**pagerank/**](pagerank/) (3A) | Graph statistics, PageRank written by hand and as Pregel in Spark GraphFrames, message counts under partitioning, and a PowerGraph-style vertex-cut simulation | [README](pagerank/README.md) |
| [**recommendation/**](recommendation/) (3B) | Loads the graph into Neo4j, answers recommendation queries in Cypher, and compares two recommenders on a held-out test split | [README](recommendation/README.md) |

## Results

**Recommendations (3B).** Trained on `u1.base` only; `u1.test` is read once, in the evaluation step.
Top-10 recommendations for 456 eligible users:

| Method | Precision@10 | Recall@10 | Users with at least one hit |
|---|---:|---:|---:|
| A: common-neighbour support (every supporter counts 1) | 0.247 | 0.135 | 376 |
| B: Jaccard-weighted user–user, 20 neighbours | **0.355** | **0.209** | **406** |

Weighting neighbours by how much their likes overlap with the user's turns a popularity vote into a
personalised one. The Cypher and Python versions of method A were cross-checked and return the same
movies with the same support. A `PROFILE` of the candidate query showed the "not already rated" check
causing about 94% of its 71M database hits, and multi-hop path counts growing from 0.73M (3 hops) to
70.6M (4 hops), while the number of distinct vertices reached stays near the size of the graph.

**PageRank (3A).**

| Check | Result |
|---|---|
| Pregel (GraphFrames, Spark 4.2) vs local implementation, 10 iterations | max abs difference **2.6e-18** |
| Rank sum at every iteration | 1.0 (error < 1e-15) |
| Cross-worker messages with `owner(v) = v mod P`, P = 4 / 8 / 16 / 32 | 75% / 88% / 94% / 97% |
| Hub graph (one vertex with 50,000 edges), 8 workers: load imbalance | vertex partition **2.13** vs vertex cut **1.00**, for 8 hub replicas and 14 sync messages per iteration |

## Running it

Each part has its own README with exact commands, pinned versions (Python 3.14, Java 21,
PySpark 4.2, GraphFrames 0.12.3, Neo4j 2026.10) and a Dockerfile. All outputs were produced in those
containers. The MovieLens 100K archive is not included; download it from
[GroupLens](https://grouplens.org/datasets/movielens/100k/) and pass its folder as `--data-dir`.

The Neo4j password in part 3B is the throwaway local value the assignment specified for its
container.

## AI assistance

I built this with Claude Code, and each part's `LLM_USAGE.md` records the prompts that shaped the
implementation and where the first approach was wrong (for example, a path query that filtered
after expansion instead of during it). I reviewed the code and the outputs.

## Licence

MIT. MovieLens is distributed by GroupLens under its own terms.
