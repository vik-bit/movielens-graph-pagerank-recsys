"""B1: load the MovieLens 100K *training* graph (u1.base only) into Neo4j.

(:User {id})  (:Movie {id, title})  (:Genre {id, name})
(:User)-[:RATED {rating, timestamp}]->(:Movie)   (:Movie)-[:IN_GENRE]->(:Genre)

Idempotent: uniqueness constraints + MERGE in UNWIND batches. --reset wipes the graph first.
"""
import argparse
import csv
import os

from neo4j import GraphDatabase

BATCH = 1000


def read_users(data_dir):
    with open(os.path.join(data_dir, "u.user"), encoding="latin-1") as f:
        return [{"id": int(line.split("|")[0])} for line in f if line.strip()]


def read_genres(data_dir):
    out = []
    with open(os.path.join(data_dir, "u.genre"), encoding="latin-1") as f:
        for line in f:
            line = line.strip()
            if line:
                name, gid = line.rsplit("|", 1)
                out.append({"id": int(gid), "name": name})
    return out


def read_movies(data_dir):
    """Return (movies, in_genre pairs). Last 19 columns of u.item are genre flags 0..18."""
    movies, in_genre = [], []
    with open(os.path.join(data_dir, "u.item"), encoding="ISO-8859-1") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if not line:
                continue
            parts = line.split("|")
            mid = int(parts[0])
            movies.append({"id": mid, "title": parts[1]})
            flags = parts[-19:]
            for gid, flag in enumerate(flags):
                if flag == "1":
                    in_genre.append({"movie": mid, "genre": gid})
    return movies, in_genre


def read_base(data_dir, filename="u1.base"):
    rows = []
    with open(os.path.join(data_dir, filename), encoding="latin-1") as f:
        for line in f:
            if line.strip():
                u, m, r, t = line.split("\t")
                rows.append({"u": int(u), "m": int(m), "r": int(r), "t": int(t)})
    return rows


def batched(rows, n=BATCH):
    for i in range(0, len(rows), n):
        yield rows[i:i + n]


def run_batches(session, query, rows):
    for chunk in batched(rows):
        session.execute_write(lambda tx, c=chunk: tx.run(query, rows=c).consume())


CONSTRAINTS = [
    "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
    "CREATE CONSTRAINT movie_id IF NOT EXISTS FOR (m:Movie) REQUIRE m.id IS UNIQUE",
    "CREATE CONSTRAINT genre_id IF NOT EXISTS FOR (g:Genre) REQUIRE g.id IS UNIQUE",
]

Q_USERS = "UNWIND $rows AS row MERGE (:User {id: row.id})"
Q_GENRES = "UNWIND $rows AS row MERGE (g:Genre {id: row.id}) SET g.name = row.name"
Q_MOVIES = "UNWIND $rows AS row MERGE (m:Movie {id: row.id}) SET m.title = row.title"
Q_IN_GENRE = """
UNWIND $rows AS row
MATCH (m:Movie {id: row.movie}) MATCH (g:Genre {id: row.genre})
MERGE (m)-[:IN_GENRE]->(g)
"""
Q_RATED = """
UNWIND $rows AS row
MATCH (u:User {id: row.u}) MATCH (m:Movie {id: row.m})
MERGE (u)-[r:RATED]->(m)
SET r.rating = row.r, r.timestamp = row.t
"""

COUNT_QUERIES = [
    ("users", "MATCH (n:User) RETURN count(n) AS c"),
    ("movies", "MATCH (n:Movie) RETURN count(n) AS c"),
    ("genres", "MATCH (n:Genre) RETURN count(n) AS c"),
    ("rated_relationships", "MATCH ()-[r:RATED]->() RETURN count(r) AS c"),
    ("in_genre_relationships", "MATCH ()-[r:IN_GENRE]->() RETURN count(r) AS c"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--uri", default="bolt://localhost:7687")
    ap.add_argument("--user", default="neo4j")
    ap.add_argument("--password", default="bdaGraph2026")
    ap.add_argument("--database", default="neo4j")
    ap.add_argument("--reset", action="store_true", help="delete the existing graph before loading")
    ap.add_argument("--output", default="partB/output/db_counts.csv")
    a = ap.parse_args()

    users = read_users(a.data_dir)
    genres = read_genres(a.data_dir)
    movies, in_genre = read_movies(a.data_dir)
    ratings = read_base(a.data_dir)  # training data ONLY (u1.test is never read here)

    with GraphDatabase.driver(a.uri, auth=(a.user, a.password)) as driver:
        driver.verify_connectivity()
        with driver.session(database=a.database) as s:
            if a.reset:
                s.run("MATCH (n) CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS").consume()
                print("graph reset")
            for c in CONSTRAINTS:
                s.run(c).consume()
            s.run("CALL db.awaitIndexes()").consume()
            run_batches(s, Q_USERS, users)
            run_batches(s, Q_GENRES, genres)
            run_batches(s, Q_MOVIES, movies)
            run_batches(s, Q_IN_GENRE, in_genre)
            run_batches(s, Q_RATED, ratings)
            counts = [(name, s.run(q).single()["c"]) for name, q in COUNT_QUERIES]

    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    with open(a.output, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        w.writerows(counts)
    for k, v in counts:
        print(f"{k},{v}")


if __name__ == "__main__":
    main()
