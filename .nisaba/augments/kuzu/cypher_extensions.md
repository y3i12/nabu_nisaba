# Kuzu Extensions Manual for LLMs

## 1. Extensions System

### 1.1 Extension Management
```cypher
// List available extensions
CALL SHOW_OFFICIAL_EXTENSIONS() RETURN *;

// Install extension (once per database)
INSTALL <extension_name>;

// Load extension (per session)
LOAD <extension_name>;

// Update extension
UPDATE <extension_name>;

// List loaded extensions
CALL SHOW_LOADED_EXTENSIONS() RETURN *;

// Uninstall extension
UNINSTALL <extension_name>;
```

### 1.2 Available Official Extensions
1. **httpfs** - Remote file access (HTTP/HTTPS, S3, GCS)
2. **fts** - Full-text search with BM25 scoring
3. **vector** - Vector similarity search with HNSW index
4. **json** - JSON data type support
5. **algo** - Graph algorithms
6. **llm** - LLM and embedding API calls
7. **postgres** - PostgreSQL database attachment
8. **duckdb** - DuckDB database attachment
9. **sqlite** - SQLite database attachment
10. **azure** - Azure storage access

### 1.3 Custom Extensions
```cypher
// Load custom extension with path
LOAD EXTENSION 'extension/custom_json/build/libjson.kuzu_extension';
```

---

## 2. Algorithm Extensions

### 2.1 Setup
```cypher
INSTALL algo;
LOAD algo;
```

### 2.2 Projected Graphs (Required for Algorithms)
```cypher
// Create simple projected graph
CALL PROJECT_GRAPH('Graph', ['Person'], ['KNOWS']);

// Create filtered projected graph
CALL PROJECT_GRAPH(
  'filtered_graph',
  { 'Person': 'n.age > 18' },
  { 'KNOWS': 'r.strength > 0.5' }
);

// List projected graphs
CALL SHOW_PROJECTED_GRAPHS();

// Drop projected graph
CALL DROP_PROJECTED_GRAPH('Graph');
```

### 2.3 Available Algorithms

#### PageRank
```cypher
CALL page_rank(
  'Graph',
  dampingFactor := 0.85,    // default: 0.85
  maxIterations := 20,       // default: 20
  tolerance := 0.0000001,    // default: 0.0000001
  normalizeInitial := true   // default: true
) RETURN node, rank;

// Alias: pr
```

#### Strongly Connected Components
```cypher
// BFS-based parallel algorithm
CALL strongly_connected_components('Graph', maxIterations := 100)
RETURN node, group_id;

// DFS-based Kosaraju's algorithm
CALL strongly_connected_components_kosaraju('Graph')
RETURN node, group_id;

// Aliases: scc, scc_ko
```

#### Weakly Connected Components
```cypher
CALL weakly_connected_components('Graph', maxIterations := 100)
RETURN node, group_id;

// Alias: wcc
```

#### K-Core Decomposition
```cypher
CALL k_core_decomposition('Graph')
RETURN node, k_degree;

// Alias: kcore
```

#### Louvain Community Detection
```cypher
CALL louvain(
  'Graph',
  maxPhases := 20,          // default: 20
  maxIterations := 20        // default: 20
) RETURN node, louvain_id;
```

### 2.4 Algorithm Integration
```cypher
// Combine PageRank with graph traversal
CALL page_rank('Graph') 
WITH node, rank WHERE rank > 0.1
MATCH (node)-[:KNOWS]->(neighbor)
RETURN node.name, neighbor.name, rank
ORDER BY rank DESC;

// Community-based analysis
CALL louvain('SocialGraph')
WITH node, louvain_id
MATCH (node)-[:INTERACTS_WITH]-(peer)
WHERE peer.louvain_id = node.louvain_id
RETURN louvain_id, count(*) as internal_connections;
```

---

## 3. Full-Text Search

### 3.1 Setup
```cypher
INSTALL FTS;
LOAD FTS;
```

### 3.2 Create FTS Index
```cypher
CALL CREATE_FTS_INDEX(
  <TABLE_NAME>,              // Node table name
  <INDEX_NAME>,              // Index name
  [<PROPERTY1>, ...],        // Properties to index
  stemmer := 'porter',       // Optional: language stemmer
  stopwords := <STRING>      // Optional: stopwords file/table
);

// Example
CALL CREATE_FTS_INDEX(
  'Book', 
  'book_index', 
  ['abstract', 'title'], 
  stemmer := 'english', 
  stopwords := './stopwords.csv'
);
```

#### Stemmer Options
- Languages: `arabic`, `basque`, `catalan`, `danish`, `dutch`, `english`, `finnish`, `french`, `german`, `greek`, `hindi`, `hungarian`, `indonesian`, `irish`, `italian`, `lithuanian`, `nepali`, `norwegian`, `porter`, `portuguese`, `romanian`, `russian`, `serbian`, `spanish`, `swedish`, `tamil`, `turkish`
- Special: `none` (no stemming)

### 3.3 Query FTS Index
```cypher
CALL QUERY_FTS_INDEX(
  <TABLE_NAME>,
  <INDEX_NAME>,
  <QUERY>,
  conjunctive := false,     // Optional: AND vs OR search
  K := 1.2,                 // Optional: BM25 term frequency parameter
  B := 0.75,                // Optional: BM25 document length parameter
  TOP := <value>            // Optional: Return top-k results
) RETURN node, score;

// Basic search
CALL QUERY_FTS_INDEX('Book', 'book_index', 'quantum machine')
RETURN node.title, score
ORDER BY score DESC;

// Conjunctive search (all terms required)
CALL QUERY_FTS_INDEX('Book', 'book_index', 'dragon magic', conjunctive := true)
RETURN node.title, score;

// Top-K search
CALL QUERY_FTS_INDEX('Book', 'book_index', 'dragon magic', top := 10)
RETURN node.title, score;
```

### 3.4 FTS Integration with Cypher
```cypher
// Combine FTS with graph traversal
MATCH (a:Author)-[:WROTE]->(b:Book)
CALL QUERY_FTS_INDEX('Book', 'book_index', 'quantum physics')
WHERE b = node
RETURN a.name, b.title, score
ORDER BY score DESC;

// Filter by date and text search
MATCH (b:Book)
WHERE b.pubYear > 2012
CALL QUERY_FTS_INDEX('Book', 'book_index', 'machine learning', top := 10)
WHERE b = node
RETURN b.title, b.pubYear, score
ORDER BY score DESC;
```

### 3.5 Index Management
```cypher
// Show all indexes
CALL SHOW_INDEXES() RETURN *;

// Drop FTS index
CALL DROP_FTS_INDEX('Book', 'book_index');
```

---

## 4. Other Extensions

### 4.1 Vector Search Extension
```cypher
INSTALL vector;
LOAD vector;

// Create vector index
CALL CREATE_VECTOR_INDEX(
  'Book',                   // table name
  'book_title_index',       // index name
  'title_embedding',        // property name (FLOAT[] or DOUBLE[])
  metric := 'cosine',       // distance metric: cosine, euclidean, manhattan
  ef_construction := 128,   // construction parameter
  max_level := 4,           // HNSW levels
  m := 16                   // max connections per node
);

// Query vector index
CALL QUERY_VECTOR_INDEX(
  'Book',
  'book_title_index', 
  $query_vector,           // query vector
  $limit,                  // number of results
  efs := 500               // search parameter
) RETURN node.title ORDER BY distance;

// Drop vector index
CALL DROP_VECTOR_INDEX('Book', 'book_title_index');
```

### 4.2 JSON Extension
```cypher
INSTALL json;
LOAD json;

// Load from JSON file
LOAD FROM "patients.json" RETURN *;

// Copy JSON data to table
COPY Patient FROM "patient.json";

// Query JSON properties
MATCH (p:Patient) 
WHERE p.metadata.age > 30 
RETURN p.name, p.metadata;
```

### 4.3 LLM Extension
```cypher
INSTALL llm;
LOAD llm;

// Generate embeddings via OpenAI
RETURN CREATE_EMBEDDING(
  "Kuzu is an embedded graph database",
  "open-ai",
  "text-embedding-3-small"
);

// Generate embeddings via Ollama
RETURN CREATE_EMBEDDING(
  "Kuzu is an embedded graph database",
  "ollama", 
  "nomic-embed-text"
);
```

### 4.4 Database Attachment Extensions

#### PostgreSQL
```cypher
INSTALL postgres;
LOAD postgres;

// Attach database
ATTACH 'host=localhost port=5432 dbname=university user=postgres password=testpwd' 
AS uw (DBTYPE POSTGRES);

// Query attached database
LOAD FROM uw.person RETURN *;

// SQL queries
CALL SQL_QUERY('uw', 'SELECT * FROM person WHERE age >= 20');

// Copy data to Kuzu
COPY Person FROM (LOAD FROM uw.person RETURN name, age);

// Detach
DETACH uw;
```

#### DuckDB
```cypher
INSTALL duckdb;
LOAD duckdb;

// Attach local DuckDB
ATTACH 'university.db' AS uw (DBTYPE DUCKDB);

// Attach remote DuckDB on S3
ATTACH 's3://my-bucket/university.db' AS uw (DBTYPE DUCKDB);
```

#### SQLite
```cypher
INSTALL sqlite;
LOAD sqlite;

// Attach SQLite database
ATTACH 'university.db' AS uw (DBTYPE SQLITE);

// Handle dynamic typing
CALL SQLITE_ALL_VARCHAR_OPTION=TRUE;
```

### 4.5 Cloud Storage Extensions

#### HTTPFS Extension
```cypher
INSTALL httpfs;
LOAD httpfs;

// Read from remote CSV
LOAD FROM "https://extension.kuzudb.com/dataset/test/city.csv" RETURN *;

// Enable caching
CALL HTTP_CACHE_FILE=TRUE;

// S3 access
LOAD FROM "s3://bucket/file.csv" RETURN *;

// GCS access  
LOAD FROM "gs://bucket/file.csv" RETURN *;
```

#### Azure Extension
```cypher
INSTALL azure;
LOAD azure;

// Configure
CALL AZURE_CONNECTION_STRING='DefaultEndpointsProtocol=https;AccountName=...';
// OR
CALL AZURE_ACCOUNT_NAME='myaccount';
CALL AZURE_ACCOUNT_KEY='mykey';

// Azure Blob Storage
LOAD FROM "az://container/file.csv" RETURN *;

// Azure Data Lake Storage
LOAD FROM "abfss://container/file.csv" RETURN *;

// Glob pattern matching
LOAD FROM "az://container/vPerson*.csv" RETURN *;
```
