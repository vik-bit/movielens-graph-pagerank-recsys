"""A1: build G_L / G_D from u.data and write graph_stats.csv."""
import argparse
import csv
import os

from common import (MOVIE_OFFSET, degrees, directed_edges, logical_edges,
                    read_ratings, vertices_of)


def compute_stats(data_dir):
    ratings = read_ratings(data_dir)
    gl = logical_edges(ratings)
    gd = directed_edges(ratings)
    verts = vertices_of(gl)
    users = [v for v in verts if v < MOVIE_OFFSET]
    movies = [v for v in verts if v > MOVIE_OFFSET]
    deg = degrees(gl)  # undirected degree in G_L (= out-degree in G_D)
    # Ties broken by smallest vertex id (deterministic).
    max_user = min(users, key=lambda v: (-deg[v], v))
    max_movie = min(movies, key=lambda v: (-deg[v], v))
    return [
        ("logical_vertices", len(verts)),
        ("logical_user_vertices", len(users)),
        ("logical_movie_vertices", len(movies)),
        ("logical_edges", len(gl)),
        ("directed_edges", len(gd)),
        ("min_rating", min(r for _, _, r, _ in ratings)),
        ("max_rating", max(r for _, _, r, _ in ratings)),
        ("max_user_degree", deg[max_user]),
        ("max_user_id", max_user),
        ("max_movie_degree", deg[max_movie]),
        ("max_movie_id", max_movie - MOVIE_OFFSET),  # original movie_id
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--output", default="partA/output/graph_stats.csv")
    a = ap.parse_args()
    rows = compute_stats(a.data_dir)
    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    with open(a.output, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        w.writerows(rows)
    for k, v in rows:
        print(f"{k},{v}")


if __name__ == "__main__":
    main()
