#!/usr/bin/env python
# coding: utf-8

# # Lesson 2: Querying Knowledge Graphs with Cypher

# <p style="background-color:#fd4a6180; padding:15px; margin-left:20px"> <b>Note:</b> This notebook takes about 30 seconds to be ready to use. Please wait until the "Kernel starting, please wait..." message clears from the top of the notebook before running any cells. You may start the video while you wait.</p>
# 

# ### Import packages and set up Neo4

# In[1]:


from dotenv import load_dotenv
import os

from langchain_community.graphs import Neo4jGraph

# Warning control
import warnings
warnings.filterwarnings("ignore")


# In[ ]:


load_dotenv('.env', override=True)
NEO4J_URI = os.getenv('NEO4J_URI')
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')
NEO4J_DATABASE = os.getenv('NEO4J_DATABASE')


# - Initialize a knowledge graph instance using LangChain's Neo4j integration

# In[ ]:


kg = Neo4jGraph(
    url=NEO4J_URI, username=NEO4J_USERNAME, password=NEO4J_PASSWORD, database=NEO4J_DATABASE
)


# ### Querying the movie knowledge graph 
# - Match all nodes in the graph

# In[ ]:


cypher = """
  MATCH (n) 
  RETURN count(n)
  """


# In[ ]:


result = kg.query(cypher)
result


# In[ ]:


cypher = """
  MATCH (n) 
  RETURN count(n) AS numberOfNodes
  """


# In[ ]:


result = kg.query(cypher)
result


# In[ ]:


print(f"There are {result[0]['numberOfNodes']} nodes in this graph.")


# - Match only the `Movie` nodes by specifying the node label

# In[ ]:


cypher = """
  MATCH (n:Movie) 
  RETURN count(n) AS numberOfMovies
  """
kg.query(cypher)


# - Change the variable name in the node pattern match for improved readability

# In[ ]:


cypher = """
  MATCH (m:Movie) 
  RETURN count(m) AS numberOfMovies
  """
kg.query(cypher)


# - Match only the `Person` nodes

# In[ ]:


cypher = """
  MATCH (people:Person) 
  RETURN count(people) AS numberOfPeople
  """
kg.query(cypher)


# - Match a single person by specifying the value of the `name` property on the `Person` node

# In[ ]:


cypher = """
  MATCH (tom:Person {name:"Tom Hanks"}) 
  RETURN tom
  """
kg.query(cypher)


# - Match a single `Movie` by specifying the value of the `title` property

# In[ ]:


cypher = """
  MATCH (cloudAtlas:Movie {title:"Cloud Atlas"}) 
  RETURN cloudAtlas
  """
kg.query(cypher)


# - Return only the `released` property of the matched `Movie` node

# In[ ]:


cypher = """
  MATCH (cloudAtlas:Movie {title:"Cloud Atlas"}) 
  RETURN cloudAtlas.released
  """
kg.query(cypher)


# - Return two properties

# In[ ]:


cypher = """
  MATCH (cloudAtlas:Movie {title:"Cloud Atlas"}) 
  RETURN cloudAtlas.released, cloudAtlas.tagline
  """
kg.query(cypher)


# #cypher = """
#   MATCH (nineties:Movie) 
#   WHERE nineties.released >= 1990 
#     AND nineties.released < 2000 
#   RETURN nineties.title
#   """
# ## Cypher patterns with conditional matching

# In[ ]:


cypher = """
  MATCH (nineties:Movie) 
  WHERE nineties.released >= 1990 
    AND nineties.released < 2000 
  RETURN nineties.title
  """


# In[ ]:


kg.query(cypher)


# ### Pattern matching with multiple nodes

# In[ ]:


cypher = """
  MATCH (actor:Person)-[:ACTED_IN]->(movie:Movie) 
  RETURN actor.name, movie.title LIMIT 10
  """
kg.query(cypher)


# In[ ]:


cypher = """
  MATCH (tom:Person {name: "Tom Hanks"})-[:ACTED_IN]->(tomHanksMovies:Movie) 
  RETURN tom.name,tomHanksMovies.title
  """
kg.query(cypher)


# In[ ]:


cypher = """
  MATCH (tom:Person {name:"Tom Hanks"})-[:ACTED_IN]->(m)<-[:ACTED_IN]-(coActors) 
  RETURN coActors.name, m.title
  """
kg.query(cypher)


# ### Delete data from the graph

# In[ ]:


cypher = """
MATCH (emil:Person {name:"Emil Eifrem"})-[actedIn:ACTED_IN]->(movie:Movie)
RETURN emil.name, movie.title
"""
kg.query(cypher)


# In[ ]:


cypher = """
MATCH (emil:Person {name:"Emil Eifrem"})-[actedIn:ACTED_IN]->(movie:Movie)
DELETE actedIn
"""
kg.query(cypher)


# ### Adding data to the graph

# In[ ]:


cypher = """
CREATE (andreas:Person {name:"Andreas"})
RETURN andreas
"""

kg.query(cypher)


# In[ ]:


cypher = """
MATCH (andreas:Person {name:"Andreas"}), (emil:Person {name:"Emil Eifrem"})
MERGE (andreas)-[hasRelationship:WORKS_WITH]->(emil)
RETURN andreas, hasRelationship, emil
"""
kg.query(cypher)

