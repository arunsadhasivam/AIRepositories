in readme.md

The `README.md` file contains the following complete set of Neo4j concepts and Cypher queries :

# Neo4j Graph Concepts & Advanced Queries

This document outlines Neo4j concepts and provides a comprehensive set of Cypher queries for common tasks.

## Core Concepts

* **Nodes:** Fundamental entities in the graph (e.g., Person, Airport), which can have labels to categorize them.
* **Relationships (Edges):** Connections between nodes that define interactions; these are stored as first-class citizens.
* **Properties:** Key-value pairs stored on nodes or relationships to hold data attributes.
* **Cypher:** A declarative query language used to interact with data using ASCII-art style patterns.
* **ACID Compliance:** Ensures database reliability and data integrity.
* **Schema-Optional:** Allows for flexible data modeling and evolution.

## Neo4j Queries

### 1. Indegree
Finds the number of incoming relationships for a specific node label.
```cypher
MATCH (a:Airport)<-[:HAS_ROUTE]-(others)
RETURN a.code, count(*) AS inDegree
```

### 2. Outdegree
Finds the number of outgoing relationships for a specific node label.
```cypher
MATCH (a:Airport)-[:HAS_ROUTE]->(others)
RETURN a.code, count(*) AS outDegree
```

### 3. Total Degree
Finds the total number of relationships connected to a node, regardless of direction.
```cypher
MATCH (n)-[r]-()
RETURN n, count(r) AS degree
```

### 4. Degree Centrality (Using APOC)
Calculates degree centrality for nodes using the APOC library (if installed).
```cypher
MATCH (n)
RETURN n.name AS name, apoc.node.degree(n) AS degree
```

### 5. Find Shortest Path
Finds the shortest path between two nodes by name.
```cypher
MATCH (start:Node {name: 'Start'}), (end:Node {name: 'End'})
MATCH p = shortestPath((start)-[*..15]-(end))
RETURN p
```

