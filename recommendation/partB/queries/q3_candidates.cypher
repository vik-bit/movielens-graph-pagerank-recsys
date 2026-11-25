// Q3 - three-hop candidates: target -> liked A <- supporting X -> liked B,
// B never rated (any rating) by target in the training graph; support = DISTINCT X
MATCH (u:User {id: $target_user})-[r1:RATED]->(a:Movie)<-[r2:RATED]-(x:User)-[r3:RATED]->(b:Movie)
WHERE r1.rating >= $like_threshold
  AND r2.rating >= $like_threshold
  AND r3.rating >= $like_threshold
  AND x <> u
  AND NOT EXISTS { (u)-[:RATED]->(b) }
RETURN b.id AS movie_id, b.title AS title, count(DISTINCT x) AS support
ORDER BY support DESC, movie_id ASC
LIMIT $topk
