from dotenv import load_dotenv
import os
from langchain_community.graphs import Neo4jGraph
import ollama

load_dotenv()

# Environment variables
NEO4J_URI = os.environ["NEO4J_URI"]
NEO4J_USERNAME = os.environ["NEO4J_USERNAME"]
NEO4J_PASSWORD = os.environ["NEO4J_PASSWORD"]
NEO4J_DATABASE = os.environ["NEO4J_DATABASE"]

# Neo4j connection
kg = Neo4jGraph(
    url=NEO4J_URI,
    username=NEO4J_USERNAME,
    password=NEO4J_PASSWORD,
    database=NEO4J_DATABASE,
)

# nomic-embed-text produces 768 dimensions (not 1536 like OpenAI)
kg.query(
    """
    CREATE VECTOR INDEX health_providers_embeddings IF NOT EXISTS
    FOR (hp:HealthcareProvider) ON (hp.comprehensiveEmbedding)
    OPTIONS {
      indexConfig: {
        `vector.dimensions`: 768,
        `vector.similarity_function`: 'cosine'
      }
    }
    """
)

# Check index created
res = kg.query("SHOW VECTOR INDEXES")
print(res)

# Fetch all HealthcareProviders with bio
records = kg.query("""
    MATCH (hp:HealthcareProvider)-[:TREATS]->(p:Patient)
    WHERE hp.bio IS NOT NULL
    RETURN elementId(hp) AS id, hp.bio AS bio, hp.name AS name
""")

# Generate Ollama embedding for each provider and store in Neo4j
for record in records:
    bio = record["bio"]
    node_id = record["id"]

    # Generate embedding using Ollama nomic-embed-text
    response = ollama.embeddings(
        model="nomic-embed-text",
        prompt=bio
    )
    vector = response["embedding"]

    # Store embedding back to Neo4j node
    kg.query("""
        MATCH (hp:HealthcareProvider)
        WHERE elementId(hp) = $id
        CALL db.create.setNodeVectorProperty(hp, "comprehensiveEmbedding", $vector)
    """, params={"id": node_id, "vector": vector})

# Verify embeddings stored
result = kg.query("""
    MATCH (hp:HealthcareProvider)
    WHERE hp.bio IS NOT NULL
    RETURN hp.bio, hp.name, hp.comprehensiveEmbedding
    LIMIT 5
""")

for record in result:
    print(f"bio: {record['hp.bio']}, name: {record['hp.name']}")

# Query using vector similarity search
question = "give me a list of healthcare providers in the area of dermatology"

# Generate embedding for the question using Ollama
question_response = ollama.embeddings(
    model="nomic-embed-text",
    prompt=question
)
question_embedding = question_response["embedding"]

# Search Neo4j vector index with question embedding
result = kg.query(
    """
    CALL db.index.vector.queryNodes(
        'health_providers_embeddings',
        $top_k,
        $question_embedding
    ) YIELD node AS healthcare_provider, score
    RETURN healthcare_provider.name, healthcare_provider.bio, score
    """,
    params={
        "question_embedding": question_embedding,
        "top_k": 3,
    },
)

# Print results
for record in result:
    print(f"Name: {record['healthcare_provider.name']}")
    print(f"Bio: {record['healthcare_provider.bio']}")
    print(f"Score: {record['score']}")
    print("---")