# LLM usage — Assignment 3B

## Tools used

* **Claude Code** (Anthropic, model Claude Opus 5.5) in the Claude desktop app. It read the
  assignment PDF and course notes, and wrote the loader, Cypher queries and recommender. It
  ran them against the local `neo4j:2026.10.1` container, drove Neo4j Browser for the PROFILE
  export, and drafted the README. I reviewed the outputs and the explanations.

## Prompts that materially affected the implementation

1. *"Complete this assignment and check out the lecture slides for reference"* (assignment PDF
   attached). This produced the loader (constraints first, then MERGE in UNWIND batches of
   1000), the four parameterized query files and the two recommenders.
2. *"Take the Q3 profile screenshot in Neo4j Browser for me."* The assistant set
   `:param {target_user: 1, like_threshold: 4, topk: 10}` in Neo4j Browser and ran
   `PROFILE` + Q3. It then exported the plan diagram as `q3_profile.png`. This replaced an
   earlier image drawn from the driver's plan, which was not a Browser screenshot.
3. *"Correct whatever you can and evaluate like a strict TA and make final changes."* This
   re-ran all three programs inside a pinned Python 3.14.10 container (connected to Neo4j via
   `--network container:bda-neo4j`), so no output depends on the host's Python 3.14.4. It also
   rechecked the word limits, the tie rules and the leakage rule.

## Where the LLM's first idea was wrong / inefficient, and the fix

* **Path growth query.** The obvious form, `MATCH p=(u)-[:RATED*4]-(n) WHERE all(r IN
  relationships(p) WHERE r.rating >= $t)`, filters only *after* building each full length-4
  path. It was replaced with a quantified path pattern,
  `(()-[r:RATED WHERE r.rating >= $like_threshold]-()){4}`, so the rating predicate prunes
  during expansion. L=4 still enumerates 70.6 M valid paths, with a median of about 38 s.
* **Deprecated pattern predicate.** `WHERE NOT (u)-[:RATED]->(b)` is legacy syntax, so it was
  written as `NOT EXISTS { (u)-[:RATED]->(b) }`. The PROFILE shows this as `AntiSemiApply` +
  `Expand(Into)`, which turned out to be the most expensive operator (66.7 M of 71.2 M DB hits).
* **Q3 PROFILE image.** The first `q3_profile.png` was drawn from the driver's
  `summary.profile` rather than coming from Neo4j Browser, so it did not meet the requirement.
  It was replaced with Neo4j Browser's *Download diagram PNG* export of the same PROFILE. Both
  report 71,187,146 total DB hits.

## How problems were detected

* Checking `db_counts.csv` against the fixed counts after two loads (with and without
  `--reset`).
* Comparing `in_genre` (2893) with a direct count of 1-flags in `u.item`.
* Cross-checking Cypher Q3 against Python Method A for user 1: identical movies and support
  values.
* Asserting that no recommended movie was rated by the user in training.
* Re-running with `--target-user 50 --like-threshold 5 --topk 5` and `--neighbors 5`.

## A concept that became clearer

The PROFILE changed how I think about query cost. Q3 returns only 10 rows, yet it does
71 million DB hits. About 94 % of them come from the `NOT EXISTS` anti-join, which is checked
once for each of the 734,937 three-hop paths. Producing the answer itself is cheap. The path
growth table shows the same effect: the number of paths multiplies by about 90 per hop, while
the number of distinct vertices reached saturates near 943. This explains why collaborative
filtering aggregates neighbourhoods into similarity scores (as in Method B's Jaccard weights)
instead of enumerating paths. It also explains why Method B, which weights a few close
neighbours, beat Method A's raw supporter counts on Precision@10 (0.355 vs 0.247).
