"""Shared helpers for Assignment 3A (graph construction from MovieLens 100K u.data).

Vertex-ID convention (Section 5 of the assignment):
  * user vertex  = original user_id          (1..943)
  * movie vertex = 100000 + original movie_id (100001..101682)
"""
import os
from collections import defaultdict

MOVIE_OFFSET = 100000


def movie_vertex(movie_id):
    return MOVIE_OFFSET + movie_id


def vertex_type(v):
    return "movie" if v > MOVIE_OFFSET else "user"


def original_id(v):
    return v - MOVIE_OFFSET if v > MOVIE_OFFSET else v


def read_ratings(data_dir, filename="u.data"):
    """Return list of (user_id, movie_id, rating, timestamp) integer tuples."""
    path = os.path.join(data_dir, filename)
    rows = []
    with open(path, "r", encoding="latin-1") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            u, m, r, t = line.split("\t")
            rows.append((int(u), int(m), int(r), int(t)))
    return rows


def logical_edges(ratings):
    """Undirected logical graph G_L: one (user_vertex, movie_vertex) edge per rating row."""
    return [(u, movie_vertex(m)) for (u, m, _r, _t) in ratings]


def directed_edges(ratings):
    """Execution graph G_D: every logical edge {u,m} becomes u->m and m->u."""
    out = []
    for u, m in logical_edges(ratings):
        out.append((u, m))
        out.append((m, u))
    return out


def vertices_of(edges):
    vs = set()
    for a, b in edges:
        vs.add(a)
        vs.add(b)
    return sorted(vs)


def degrees(edges):
    deg = defaultdict(int)
    for a, b in edges:
        deg[a] += 1
        deg[b] += 1
    return deg


def owner(v, p):
    """Logical worker owner: owner(v,P) = v mod P (never Python hash())."""
    return v % p
