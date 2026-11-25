// Q1 - direct neighborhood: movies liked (rating >= $like_threshold) by $target_user
MATCH (u:User {id: $target_user})-[r:RATED]->(m:Movie)
WHERE r.rating >= $like_threshold
RETURN m.id AS movie_id, m.title AS title, r.rating AS rating
ORDER BY rating DESC, movie_id ASC
LIMIT $topk
