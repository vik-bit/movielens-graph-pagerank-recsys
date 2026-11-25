// Q4 - genre-aware three-hop candidates: as Q3, but candidate B must share at least one
// Genre with the liked movie A on the same path.
// support = DISTINCT supporting users X over valid paths; shared_genres = DISTINCT matching genres
MATCH (u:User {id: $target_user})-[r1:RATED]->(a:Movie)<-[r2:RATED]-(x:User)-[r3:RATED]->(b:Movie),
      (a)-[:IN_GENRE]->(g:Genre)<-[:IN_GENRE]-(b)
WHERE r1.rating >= $like_threshold
  AND r2.rating >= $like_threshold
  AND r3.rating >= $like_threshold
  AND x <> u
  AND NOT EXISTS { (u)-[:RATED]->(b) }
RETURN b.id AS movie_id, b.title AS title,
       count(DISTINCT x) AS support, count(DISTINCT g) AS shared_genres
ORDER BY support DESC, shared_genres DESC, movie_id ASC
LIMIT $topk
