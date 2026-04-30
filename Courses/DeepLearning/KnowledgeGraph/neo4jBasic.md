Neo4j Queries
1. Indegree
Finds the number of incoming relationships for a specific node label.
MATCH (a:Airport)<-[:HAS_ROUTE]-(others)
RETURN a.code, count(*) AS inDegree
2. Outdegree
Finds the number of outgoing relationships for a specific node label.
MATCH (a:Airport)-[:HAS_ROUTE]->(others)
RETURN a.code, count(*) AS outDegree
3. Total Degree
Finds the total number of relationships connected to a node, regardless of direction.
MATCH (n)-[r]-()
RETURN n, count(r) AS degree
4. Degree Centrality (Using APOC)
Calculates degree centrality for nodes using the APOC library (if installed).
MATCH (n)
RETURN n.name AS name, apoc.node.degree(n) AS degree
5. Find Shortest Path
Finds the shortest path between two nodes by name.
MATCH (start:Node {name: 'Start'}), (end:Node {name: 'End'})
MATCH p = shortestPath((start)-[*..15]-(end))
RETURN p