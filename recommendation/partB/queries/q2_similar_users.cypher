// Q2 - two-hop neighborhood: other users who like at least one movie liked by $target_user
MATCH (u:User {id: $target_user})-[r1:RATED]->(m:Movie)<-[r2:RATED]-(o:User)
WHERE r1.rating >= $like_threshold
  AND r2.rating >= $like_threshold
  AND o <> u
RETURN o.id AS other_user_id, count(DISTINCT m) AS common_likes
ORDER BY common_likes DESC, other_user_id ASC
LIMIT $topk
