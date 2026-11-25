"""B3/B4: run Q1-Q4 with Cypher parameters, measure path growth for L=1..4,
and PROFILE Q3 (plan saved as q3_profile_plan.txt plus q3_profile_rendered.png; the graded
q3_profile.png is the Neo4j Browser export and is never overwritten by this script).

python partB/run_queries.py --uri bolt://localhost:7687 --user neo4j --password bdaGraph2026 \
    --target-user 1 --like-threshold 4 --topk 10 --output-dir partB/output
"""
import argparse
import csv
import os
import statistics
import time

from neo4j import GraphDatabase

HERE = os.path.dirname(os.path.abspath(__file__))
QUERY_FILES = {
    "q1": "q1_liked_movies.cypher",
    "q2": "q2_similar_users.cypher",
    "q3": "q3_candidates.cypher",
    "q4": "q4_genre_aware.cypher",
}


def load_query(name):
    with open(os.path.join(HERE, "queries", QUERY_FILES[name]), encoding="utf-8") as f:
        return f.read()


def path_query(length):
    """Exact-length undirected RATED paths from target_user, every hop with rating >= threshold.
    Quantified path pattern keeps Cypher's trail semantics (no relationship repeated in a path).
    `length` is a validated int, interpolated only because a quantifier cannot be a parameter."""
    length = int(length)
    return (
        "MATCH (s:User {id: $target_user}) "
        f"(()-[r:RATED WHERE r.rating >= $like_threshold]-()){{{length}}} (e) "
        "RETURN count(*) AS matched_paths, count(DISTINCT e) AS distinct_end_vertices"
    )


def write_csv(path, keys, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(keys)
        for r in rows:
            w.writerow([r[k] for k in keys])


def run_named_queries(driver, db, params, out_dir):
    for name in ["q1", "q2", "q3", "q4"]:
        records, _summary, keys = driver.execute_query(load_query(name), params, database_=db)
        write_csv(os.path.join(out_dir, f"{name}.csv"), keys, records)
        print(f"{name}: {len(records)} rows -> {name}.csv")
        for r in records:
            print("   ", dict(r))


def path_growth(driver, db, params, out_dir, max_len=4, runs=5):
    rows = []
    with driver.session(database=db) as s:
        for length in range(1, max_len + 1):
            q = path_query(length)
            s.run(q, params).consume()  # warm-up execution (not timed)
            times = []
            result = None
            for _ in range(runs):
                t0 = time.perf_counter_ns()
                result = s.run(q, params).single()  # fully consumes the result
                times.append((time.perf_counter_ns() - t0) / 1e6)
            rows.append({
                "path_length": length,
                "matched_paths": result["matched_paths"],
                "distinct_end_vertices": result["distinct_end_vertices"],
                "median_ms": round(statistics.median(times), 3),
            })
            print(rows[-1], "all runs ms:", [round(t, 1) for t in times])
    write_csv(os.path.join(out_dir, "path_growth.csv"),
              ["path_length", "matched_paths", "distinct_end_vertices", "median_ms"], rows)


def _plan_lines(plan, depth=0):
    args = plan.get("args", {})
    ident = ", ".join(plan.get("identifiers", []))
    details = args.get("Details", "")
    line = (f"{'  ' * depth}{plan['operatorType']:<38} rows={plan.get('rows', ''):>8} "
            f"dbHits={plan.get('dbHits', ''):>8}  {details}")
    out = [(line, plan.get("rows", 0), plan.get("dbHits", 0), plan["operatorType"], ident)]
    for child in plan.get("children", []):
        out.extend(_plan_lines(child, depth + 1))
    return out


def profile_q3(driver, db, params, out_dir):
    """Programmatic PROFILE of Q3. The Neo4j Browser screenshot (q3_profile.png) is the graded
    artifact; this writes a text dump and a fallback rendering of the same plan."""
    with driver.session(database=db) as s:
        res = s.run("PROFILE " + load_query("q3"), params)
        n_rows = len(list(res))
        summary = res.consume()
    prof = summary.profile
    lines = _plan_lines(prof)
    total_hits = sum(l[2] or 0 for l in lines)
    txt = os.path.join(out_dir, "q3_profile_plan.txt")
    with open(txt, "w", encoding="utf-8") as f:
        f.write(f"PROFILE Q3  params={params}\nresult rows={n_rows}  total dbHits={total_hits}\n\n")
        for l in lines:
            f.write(l[0] + "\n")
    print(f"Q3 PROFILE: result rows={n_rows}, total dbHits={total_hits}; plan -> {txt}")
    for l in lines:
        print("   ", l[0])

    png = os.path.join(out_dir, "q3_profile_rendered.png")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig_h = 1.2 + 0.32 * len(lines)
        fig, ax = plt.subplots(figsize=(16, fig_h))
        ax.axis("off")
        ax.text(0, 1, f"PROFILE Q3 (target_user={params['target_user']}, like_threshold="
                      f"{params['like_threshold']}, topk={params['topk']})   result rows={n_rows}   "
                      f"total dbHits={total_hits}", fontsize=11, fontweight="bold",
                va="top", family="monospace", transform=ax.transAxes)
        for i, l in enumerate(lines):
            ax.text(0, 1 - (i + 2) / (len(lines) + 2), l[0][:190], fontsize=8.5, va="top",
                    family="monospace", transform=ax.transAxes)
        fig.savefig(png, dpi=130, bbox_inches="tight")
        plt.close(fig)
    except ImportError:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uri", default="bolt://localhost:7687")
    ap.add_argument("--user", default="neo4j")
    ap.add_argument("--password", default="bdaGraph2026")
    ap.add_argument("--database", default="neo4j")
    ap.add_argument("--target-user", type=int, default=1)
    ap.add_argument("--like-threshold", type=int, default=4)
    ap.add_argument("--topk", type=int, default=10)
    ap.add_argument("--max-path-length", type=int, default=4)
    ap.add_argument("--timing-runs", type=int, default=5)
    ap.add_argument("--skip-path-growth", action="store_true")
    ap.add_argument("--skip-profile", action="store_true")
    ap.add_argument("--output-dir", default="partB/output")
    a = ap.parse_args()
    os.makedirs(a.output_dir, exist_ok=True)

    params = {"target_user": a.target_user, "like_threshold": a.like_threshold, "topk": a.topk}
    with GraphDatabase.driver(a.uri, auth=(a.user, a.password)) as driver:
        driver.verify_connectivity()
        run_named_queries(driver, a.database, params, a.output_dir)
        if not a.skip_path_growth:
            path_growth(driver, a.database, params, a.output_dir, a.max_path_length, a.timing_runs)
        if not a.skip_profile:
            profile_q3(driver, a.database, params, a.output_dir)


if __name__ == "__main__":
    main()
