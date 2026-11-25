"""A2: logical workers (owner(v,P)=v mod P) and PageRank message cost on G_D."""
import argparse
import csv
import os

from common import directed_edges, owner, read_ratings


def partition_row(gd, p, message_bytes, iterations):
    local = sum(1 for s, d in gd if owner(s, p) == owner(d, p))
    remote = len(gd) - local
    msgs = len(gd)  # one PageRank message per directed edge per iteration
    remote_bytes = remote * message_bytes
    return {
        "workers": p,
        "local_directed_edges": local,
        "remote_directed_edges": remote,
        "remote_fraction": remote / msgs,
        "messages_per_iteration": msgs,
        "remote_bytes_per_iteration": remote_bytes,
        "remote_bytes_for_10_iterations": remote_bytes * iterations,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--workers", type=int, nargs="+", default=[4, 8, 16, 32])
    ap.add_argument("--message-bytes", type=int, default=16)
    ap.add_argument("--iterations", type=int, default=10)
    ap.add_argument("--output", default="partA/output/partition_messages.csv")
    a = ap.parse_args()

    gd = directed_edges(read_ratings(a.data_dir))
    rows = [partition_row(gd, p, a.message_bytes, a.iterations) for p in a.workers]
    for r in rows:
        assert r["local_directed_edges"] + r["remote_directed_edges"] == len(gd)

    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    cols = ["workers", "local_directed_edges", "remote_directed_edges", "remote_fraction",
            "messages_per_iteration", "remote_bytes_per_iteration", "remote_bytes_for_10_iterations"]
    with open(a.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
