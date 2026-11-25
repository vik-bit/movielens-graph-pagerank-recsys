"""B6/B7: graph-neighbourhood recommenders built from u1.base ONLY, evaluated on u1.test.

Method A - common-neighbour support:
    score_A(u,m) = #DISTINCT v in Supporters(u) with m in Liked(v)
Method B - Jaccard-weighted neighbourhood (top `neighbors` users by Jaccard DESC, user_id ASC):
    score_B(u,m) = SUM Jaccard(u,v) over selected neighbours v that like m
Candidates exclude every movie u rated in training (any rating). Ties: score DESC, movie_id ASC.

python partB/recommend.py --data-dir <PATH_TO_ml-100k> --users 1 50 100 --like-threshold 4 \
    --neighbors 20 --topk 10 --output-dir partB/output
"""
import argparse
import csv
import os
from collections import defaultdict


# ----------------------------------------------------------------------------- data
def read_ratings(path):
    rows = []
    with open(path, encoding="latin-1") as f:
        for line in f:
            if line.strip():
                u, m, r, _t = line.split("\t")
                rows.append((int(u), int(m), int(r)))
    return rows


def read_titles(data_dir):
    titles = {}
    with open(os.path.join(data_dir, "u.item"), encoding="ISO-8859-1") as f:
        for line in f:
            if line.strip():
                parts = line.split("|")
                titles[int(parts[0])] = parts[1]
    return titles


class TrainingGraph:
    """Bipartite user-movie graph from TRAINING rows only."""

    def __init__(self, train_rows, like_threshold):
        self.rated = defaultdict(set)    # u -> every movie rated in training (any rating)
        self.liked = defaultdict(set)    # u -> Liked(u)
        self.likers = defaultdict(set)   # m -> users who like m (inverted index)
        for u, m, r in train_rows:
            self.rated[u].add(m)
            if r >= like_threshold:
                self.liked[u].add(m)
                self.likers[m].add(u)

    # ------------------------------------------------------------- Method A
    def recommend_a(self, u, topk):
        liked_u = self.liked.get(u, set())
        supporters = set()
        for m in liked_u:
            supporters |= self.likers[m]
        supporters.discard(u)
        score = defaultdict(int)
        rated_u = self.rated.get(u, set())
        for v in supporters:
            for m in self.liked[v]:
                if m not in rated_u:
                    score[m] += 1  # each supporter v counted once per movie (sets => DISTINCT)
        ranked = sorted(score.items(), key=lambda kv: (-kv[1], kv[0]))
        return ranked[:topk]

    # ------------------------------------------------------------- Method B
    def neighbors_b(self, u, k):
        liked_u = self.liked.get(u, set())
        if not liked_u:
            return []
        overlap = defaultdict(int)
        for m in liked_u:
            for v in self.likers[m]:
                if v != u:
                    overlap[v] += 1
        sims = []
        for v, inter in overlap.items():  # inter > 0, so Jaccard > 0 (zero-similarity users discarded)
            union = len(liked_u) + len(self.liked[v]) - inter
            sims.append((v, inter / union))
        sims.sort(key=lambda x: (-x[1], x[0]))
        return sims[:k]

    def recommend_b(self, u, k_neighbors, topk):
        rated_u = self.rated.get(u, set())
        score = defaultdict(float)
        for v, sim in self.neighbors_b(u, k_neighbors):
            for m in self.liked[v]:
                if m not in rated_u:
                    score[m] += sim
        ranked = sorted(score.items(), key=lambda kv: (-kv[1], kv[0]))
        return ranked[:topk]

    def recommend(self, method, u, k_neighbors, topk):
        if method == "A":
            return self.recommend_a(u, topk)
        return self.recommend_b(u, k_neighbors, topk)


# ----------------------------------------------------------------------------- evaluation
def evaluate(graph, test_rows, like_threshold, k_neighbors, k):
    """Uses u1.test ONLY to define RelevantTest(u) after recommendations are produced."""
    relevant = defaultdict(set)
    for u, m, r in test_rows:
        if r >= like_threshold:
            relevant[u].add(m)
    eligible = sorted(u for u, s in relevant.items() if s)
    out = []
    for method in ["A", "B"]:
        precisions, recalls, users_hit = [], [], 0
        for u in eligible:
            recs = {m for m, _s in graph.recommend(method, u, k_neighbors, k)}
            hits = len(recs & relevant[u])
            precisions.append(hits / k)
            recalls.append(hits / len(relevant[u]))
            users_hit += hits > 0
        out.append({
            "method": method,
            "eligible_users": len(eligible),
            "mean_precision_at_10": sum(precisions) / len(precisions),
            "mean_recall_at_10": sum(recalls) / len(recalls),
            "users_with_at_least_one_hit": users_hit,
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--users", type=int, nargs="+", default=[1, 50, 100])
    ap.add_argument("--like-threshold", type=int, default=4)
    ap.add_argument("--neighbors", type=int, default=20)
    ap.add_argument("--topk", type=int, default=10)
    ap.add_argument("--eval-k", type=int, default=10, help="K used for Precision@K / Recall@K")
    ap.add_argument("--skip-eval", action="store_true")
    ap.add_argument("--output-dir", default="partB/output")
    a = ap.parse_args()
    os.makedirs(a.output_dir, exist_ok=True)

    titles = read_titles(a.data_dir)
    train = read_ratings(os.path.join(a.data_dir, "u1.base"))
    graph = TrainingGraph(train, a.like_threshold)  # built before u1.test is ever opened

    rec_rows = []
    for method in ["A", "B"]:
        for u in a.users:
            for rank, (m, score) in enumerate(graph.recommend(method, u, a.neighbors, a.topk), 1):
                assert m not in graph.rated.get(u, set())
                rec_rows.append([method, u, rank, m, titles.get(m, ""),
                                 score if method == "A" else round(score, 10)])
    with open(os.path.join(a.output_dir, "recommendations.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["method", "user_id", "rank", "movie_id", "title", "score"])
        w.writerows(rec_rows)
    for r in rec_rows:
        print(r)

    if not a.skip_eval:
        test = read_ratings(os.path.join(a.data_dir, "u1.test"))  # evaluation ONLY
        ev = evaluate(graph, test, a.like_threshold, a.neighbors, a.eval_k)
        cols = ["method", "eligible_users", "mean_precision_at_10", "mean_recall_at_10",
                "users_with_at_least_one_hit"]
        with open(os.path.join(a.output_dir, "evaluation.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(ev)
        for r in ev:
            print(r)


if __name__ == "__main__":
    main()
