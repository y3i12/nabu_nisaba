# Kuzu Cypher Query Grammar for LLMs

## 1. Overview and Architecture

### Core Characteristics
- **Based on**: openCypher standard with Kuzu-specific extensions
- **Model**: Structured property graph model (schema required before data insertion)
- **Processing**: Case-insensitive queries (keywords, variables, table names, column names)
- **Encoding**: UTF-8 support including Unicode characters
- **Termination**: Statements must end with semicolon (;)
- **Semantics**: Walk semantic by default (allows repeated edges) vs Neo4j's trail semantic

### Key Differences from Neo4j Cypher
1. **Schema Required**: Predefined schema vs Neo4j's schema-optional approach
2. **Walk Semantics**: Allows repeated edges by default vs Neo4j's trail semantics
3. **Strong Typing**: PostgreSQL typing system with stricter type requirements
4. **LOAD FROM**: Uses LOAD FROM instead of LOAD CSV FROM
5. **Function Prefixes**: List functions use `list_` prefix (e.g., `list_concat`)
6. **Show Clauses**: SHOW commands become function calls (e.g., `CALL show_functions() RETURN *`)

---

## 2. Syntax and Grammar Rules

### Basic Syntax
```cypher
// Single-line comment
/* Multi-line 
   comment */

// Statement termination
MATCH (n:Person) WHERE n.age > 30 RETURN n.name;

// Multi-line statements
MATCH (n:Person)
WHERE n.age > 30  
RETURN n.name;
```

### Identifiers and Naming
- **Node/Relationship Tables**: CamelCase (Person, CarOwner)
- **Variables**: Case-insensitive
- **Reserved Keywords**: Must be escaped with backticks (`)
- **Unicode Support**: Full UTF-8 support

### Reserved Keywords
- **Clauses**: COLUMN, CREATE, DEFAULT, GROUP, INSTALL, MACRO, OPTIONAL, PROFILE, UNION, UNWIND, WITH
- **Subclauses**: LIMIT, ONLY, ORDER, WHERE  
- **Expressions**: ALL, CASE, CAST, ELSE, END, EXISTS, GLOB, SHORTEST, THEN, WHEN
- **Literals**: NULL, FALSE, TRUE
- **Operators**: AND, DISTINCT, IN, IS, NOT, OR, STARTS, XOR

---

## 3. Data Types

### Primitive Types
```cypher
// Integers
INT8, INT16, INT32 (alias: INT), INT64 (alias: SERIAL), INT128
UINT8, UINT16, UINT32, UINT64

// Floating Point
FLOAT (aliases: REAL, FLOAT4)     // 4 bytes
DOUBLE (alias: FLOAT8)            // 8 bytes
DECIMAL(precision, scale)         // arbitrary precision

// Other Primitives
BOOLEAN                           // true/false
STRING                            // variable-length UTF-8
UUID                              // 16-byte universally unique identifier
DATE                              // ISO-8601 format (YYYY-MM-DD)
TIMESTAMP                         // ISO-8601 with timezone support
INTERVAL (alias: DURATION)        // date/time difference
BLOB (alias: BYTEA)              // binary data up to 4KB
NULL                              // special value for unknown data
```

### Complex Types
```cypher
// Lists and Arrays
LIST                              // variable-length: [1, 2, 3, 4]
ARRAY                             // fixed-length: INT64[256]

// Structures
STRUCT                            // {first: 'Adam', last: 'Smith'}
MAP                               // map(['key1', 'key2'], ['val1', 'val2'])
UNION                             // holds multiple alternative values

// Graph-specific
NODE                              // nodes with _ID, _LABEL, and properties
REL                               // relationships with _SRC, _DST, _ID, _LABEL
RECURSIVE_REL                     // paths: STRUCT{LIST[NODE], LIST[REL]}
```

### SERIAL Type (Auto-increment)
```cypher
CREATE NODE TABLE Person(id SERIAL PRIMARY KEY, name STRING);
// Automatically generates: 0, 1, 2, 3, ...
```

---

## 4. Query Clauses

### 4.1 MATCH Clause
```cypher
// Basic node matching
MATCH (n:Person) RETURN n;
MATCH (n:Person:Employee) RETURN n;              // Multiple labels
MATCH (n) RETURN n;                              // Any label

// Relationship matching
MATCH (a:Person)-[r:FOLLOWS]->(b:Person) RETURN a, r, b;
MATCH (a:Person)<-[r:FOLLOWS]-(b:Person) RETURN a, r, b;
MATCH (a:Person)-[r:FOLLOWS]-(b:Person) RETURN a, r, b;  // Undirected

// Multiple relationship labels
MATCH (a:Person)-[r:FOLLOWS|:KNOWS]->(b:Person) RETURN a, r, b;

// Variable-length relationships
MATCH (a:Person)-[r:FOLLOWS*1..3]->(b:Person) RETURN a, b;

// Shortest path algorithms
MATCH (a)-[r* SHORTEST 1..4]->(b) RETURN a, b;
MATCH (a)-[r* ALL SHORTEST 1..3]->(b) RETURN a, b;
MATCH (a)-[r* WSHORTEST(score) 1..4]->(b) RETURN a, b;

// Recursive relationship semantics
MATCH (a)-[r:FOLLOWS* TRAIL 2..4]->(b)     // no repeated relationships
MATCH (a)-[r:FOLLOWS* ACYCLIC 2..4]->(b)   // no repeated nodes

// Property filtering in patterns
MATCH (a:Person {name: 'Alice', age: 30}) RETURN a;
MATCH (a)-[r:FOLLOWS {since: 2020}]->(b) RETURN a, r, b;

// Filtering recursive relationships
MATCH (a)-[:FOLLOWS*1..2 (r, n | WHERE r.since < 2022 AND n.age > 45)]->(b) 
RETURN a, b;

// Property projection in recursive relationships
MATCH (a)-[r:FOLLOWS*1..2 (rel, node | WHERE rel.since > 2020 | {rel.since}, {node.name})]->(b) 
RETURN a, b;

// Named paths
MATCH p = (a:Person)-[:FOLLOWS]->(b:Person) RETURN p;
MATCH p = (a)-[:FOLLOWS*1..3]->(b) RETURN nodes(p), rels(p);
```

### 4.2 OPTIONAL MATCH (Left Outer Join)
```cypher
MATCH (u:User) 
OPTIONAL MATCH (u)-[:FOLLOWS]->(f:User) 
RETURN u.name, f.name;  // f.name will be NULL if no match
```

### 4.3 CREATE Clause
```cypher
// Create nodes
CREATE (n:Person {name: 'Alice', age: 30});
CREATE (n:Person {name: 'Bob'}), (m:Person {name: 'Carol'});

// Create relationships
CREATE (a:Person {name: 'Alice'})-[r:KNOWS {since: 2020}]->(b:Person {name: 'Bob'});
```

### 4.4 MERGE Clause
```cypher
// Match or create pattern
MERGE (n:Person {name: 'Alice'}) RETURN n;

// With ON CREATE and ON MATCH
MERGE (n:Person {name: 'Alice'})
ON CREATE SET n.created = timestamp(), n.age = 25
ON MATCH SET n.lastAccessed = timestamp()
RETURN n;
```

### 4.5 SET Clause
```cypher
MATCH (n:Person {name: 'Alice'}) SET n.age = 31;
MATCH (n:Person {name: 'Alice'}) SET n.age = NULL;
MATCH (n:Person {name: 'Alice'}) SET n.age = 32, n.city = 'New York';
```

### 4.6 DELETE Clause
```cypher
// Delete nodes (must have no relationships)
MATCH (n:Person {name: 'Alice'}) DELETE n;

// Delete relationships
MATCH (a)-[r:KNOWS]->(b) WHERE a.name = 'Alice' DELETE r;

// Delete node and all relationships
MATCH (n:Person {name: 'Alice'}) DETACH DELETE n;
```

### 4.7 RETURN Clause
```cypher
MATCH (n:Person) RETURN n;
MATCH (n:Person) RETURN n.*;                    // all properties
MATCH (n:Person) RETURN n.name, n.age;         // specific properties
MATCH (n:Person) RETURN n.name AS personName;  // alias
MATCH (n:Person) RETURN DISTINCT n.city;       // distinct values
```

### 4.8 WHERE Clause
```cypher
MATCH (n:Person) WHERE n.age > 30 RETURN n;
MATCH (n:Person) WHERE n.name IN ['Alice', 'Bob'] RETURN n;
MATCH (n:Person) WHERE n.age > 25 AND n.city = 'NYC' RETURN n;

// Pattern existence
MATCH (n:Person) WHERE EXISTS { (n)-[:KNOWS]->() } RETURN n;

// NULL handling
MATCH (n:Person) WHERE n.email IS NULL RETURN n;
MATCH (n:Person) WHERE n.email IS NOT NULL RETURN n;
```

### 4.9 ORDER BY and LIMIT
```cypher
MATCH (n:Person) RETURN n.name ORDER BY n.age DESC;
MATCH (n:Person) RETURN n.name ORDER BY n.age ASC, n.name DESC;
MATCH (n:Person) RETURN n.name LIMIT 10;
MATCH (n:Person) RETURN n.name ORDER BY n.age DESC LIMIT 5;
```

### 4.10 WITH Clause (Query Chaining)
```cypher
MATCH (n:Person) 
WITH n, COUNT(*) as connectionCount
WHERE connectionCount > 5
RETURN n.name;
```

### 4.11 UNWIND Clause
```cypher
UNWIND [1, 2, 3] AS number RETURN number;
UNWIND ['Alice', 'Bob', 'Carol'] AS name 
MATCH (n:Person {name: name}) RETURN n;
```

---

## 5. Functions

### 5.1 Aggregate Functions
```cypher
COUNT(*)                    // count all records
COUNT(n.property)          // count non-null values
AVG(n.age)                 // average
MIN(n.age)                 // minimum  
MAX(n.age)                 // maximum
SUM(n.score)               // sum
COLLECT(n.name)            // collect values into list
```

### 5.2 Node/Relationship Functions
```cypher
ID(n)                      // internal ID
LABEL(n)                   // node/relationship label
LABELS(n)                  // alias for LABEL
```

### 5.3 Mathematical Functions
```cypher
ABS(x), CEIL(x), FLOOR(x), ROUND(x)
SQRT(x), POW(x, y), LOG(x), EXP(x)
SIN(x), COS(x), TAN(x), ASIN(x), ACOS(x), ATAN(x)
RAND()                     // random float 0-1
```

### 5.4 String Functions
```cypher
LENGTH(str)                            // string length
UPPER(str), LOWER(str)
SUBSTRING(str, start, length)
TRIM(str), LTRIM(str), RTRIM(str)
REPLACE(str, search, replacement)
SPLIT(str, delimiter)
CONCAT(str1, str2, ...)
CONTAINS(str, substring)
STARTS_WITH(str, prefix)
ENDS_WITH(str, suffix)
```

### 5.5 List Functions (Note: `list_` prefix)
```cypher
LIST_CREATION(1, 2, 3)                 // creates [1, 2, 3]
RANGE(start, stop, step)               // range of values
LIST_CONCAT(list1, list2)              // concatenate lists
LIST_REVERSE(list)                     // reverse list
LIST_SORT(list [, 'DESC'] [, 'NULLS FIRST'])
LIST_SIZE(list)                        // list length
LIST_CONTAINS(list, value)             // check if list contains value
list[index]                            // access by index (0-based)
list[start:end]                        // slice notation
```

### 5.6 Date/Time Functions
```cypher
CURRENT_DATE()                         // current date
NOW(), CURRENT_TIMESTAMP()             // current timestamp
DATE(string)                           // parse date from string
TIMESTAMP(string)                      // parse timestamp
INTERVAL(string)                       // create interval
date + interval                        // add interval to date
EXTRACT(year FROM date)                // extract date parts
```

### 5.7 Type Conversion
```cypher
CAST(value, 'TARGET_TYPE') 
CAST(123, 'STRING')                    // "123"
CAST('123', 'INT64')                   // 123
TYPEOF(value)                          // returns type name
```

### 5.8 Path Functions
```cypher
NODES(path)                            // extract nodes from path
RELS(path)                             // extract relationships  
LENGTH(path)                           // number of relationships
COST(path)                             // total cost of weighted path
IS_TRAIL(path)                         // check if no repeated edges
IS_ACYCLIC(path)                       // check if no repeated nodes
```

### 5.9 Utility Functions
```cypher
COALESCE(val1, val2, ...)              // first non-null value
IFNULL(val1, val2)                     // val2 if val1 is null

CASE 
  WHEN condition1 THEN result1
  WHEN condition2 THEN result2
  ELSE default_result
END
```

---

## 6. Operators

### 6.1 Comparison Operators
```cypher
= != <> < <= > >=                     // standard comparisons
IS NULL, IS NOT NULL                  // null checks
IN [list]                              // membership test
```

### 6.2 Logical Operators
```cypher
AND, OR, NOT, XOR                      // logical operations
```

### 6.3 Arithmetic Operators
```cypher
+ - * / %                              // basic arithmetic
^                                      // exponentiation  
```

### 6.4 String Operators
```cypher
+                                      // string concatenation
STARTS WITH                            // prefix check  
ENDS WITH                              // suffix check
CONTAINS                               // substring check
=~                                     // regex pattern matching
```

### 6.5 List Operators
```cypher
+                                      // list concatenation
IN                                     // element membership
[index]                                // element access
[start:end]                            // slicing
```

---

## 7. Pattern Matching

### 7.1 Node Patterns
```cypher
(n)                                    // any node
(n:Label)                              // node with specific label
(n:Label1:Label2)                      // node with multiple labels
(n {prop: value})                      // node with property filter
```

### 7.2 Relationship Patterns
```cypher
-[r]-                                  // undirected relationship
-[r]->                                 // directed relationship (outgoing, child->parent)
<-[r]-                                 // directed relationship (incoming, child<-parent)
-[r:TYPE]->                            // relationship with specific type
-[r:TYPE1|:TYPE2]->                    // relationship with multiple types
-[r*1..3]->                            // variable-length relationship
-[r* SHORTEST]->                       // shortest path
```

### 7.3 Complex Patterns
```cypher
// Multiple patterns (comma-separated)
MATCH (a)-[:FOLLOWS]->(b)-[:LIVES_IN]->(c), (a)-[:KNOWS]->(d)

// Path variables
MATCH p = (a)-[:FOLLOWS*1..3]->(b)
```

---

## 8. Data Definition Language (DDL)

### 8.1 Create Tables
```cypher
// Node tables (require primary key)
CREATE NODE TABLE Person(
  id SERIAL PRIMARY KEY, 
  name STRING NOT NULL,
  age INT64,
  email STRING
);

// Relationship tables
CREATE REL TABLE Knows(
  FROM Person TO Person,
  since DATE,
  strength DOUBLE
);

// Multiple FROM-TO relationships
CREATE REL TABLE Interaction(
  FROM Person TO Person,
  FROM Person TO Company,
  type STRING
);
```

### 8.2 Alter Tables
```cypher
ALTER TABLE Person ADD COLUMN phone STRING;
ALTER TABLE Person DROP COLUMN phone;
ALTER TABLE Person RENAME TO Individual;
```

### 8.3 Data Import/Export
```cypher
// CSV import
COPY Person FROM 'people.csv' (HEADER=true);

// Parquet import
COPY Person FROM 'people.parquet';

// With options
COPY Person FROM 'people.csv' (
  HEADER=true,
  DELIMITER='|',
  IGNORE_ERRORS=true
);

// LOAD FROM for scanning
LOAD FROM 'data.csv' (HEADER=true)
WHERE age > 18
RETURN name, age + 1 AS next_age;
```

---

## 9. Extensions System

### 9.1 Extension Management
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

### 9.2 Available Official Extensions
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

### 9.3 Custom Extensions
```cypher
// Load custom extension with path
LOAD EXTENSION 'extension/custom_json/build/libjson.kuzu_extension';
```


## 10. Kuzu-Specific Features

### 10.1 Structured Property Graph Model
- **Schema Required**: Must define schema before data insertion
- **Strong Typing**: PostgreSQL-compatible type system
- **Primary Keys**: Required for node tables
- **No Primary Keys**: Relationship tables don't have primary keys

### 10.2 Walk Semantics
```cypher
// Kuzu allows repeated edges by default
MATCH (a)-[r*1..3]->(b)              // walk semantic

// Use TRAIL or ACYCLIC for restrictions
MATCH (a)-[r* TRAIL 1..3]->(b)       // no repeated edges
MATCH (a)-[r* ACYCLIC 1..3]->(b)     // no repeated nodes
```

### 10.3 Query Hints
```cypher
// Join order hints
MATCH (a:Person)<-[e:knows]-(b:Person)-[e2:knows]->(c:Person)
HINT (a JOIN (e JOIN b)), (e2 JOIN c)
RETURN a, b, c;
```

### 10.4 Parameters and Prepared Statements
```cypher
// Parameters prefixed with $
MATCH (n:Person) 
WHERE n.age > $minAge AND n.city = $city
RETURN n.name;
```

### 10.5 Subqueries
```cypher
// EXISTS subqueries
MATCH (n:Person) 
WHERE EXISTS { 
  MATCH (n)-[:KNOWS]->(friend:Person) 
  WHERE friend.age > 30 
}
RETURN n;

// COUNT subqueries  
MATCH (n:Person)
WHERE COUNT { (n)-[:KNOWS]->(:Person) } > 2
RETURN n;
```

### 10.6 Variable Binding and Scoping
- Variables bound in MATCH are available in subsequent clauses
- WITH clause creates new scope boundaries
- Variables must be explicitly passed through WITH clauses
- Case-insensitive variable names

### 10.7 Transaction Support
```cypher
BEGIN TRANSACTION;
// Queries here
COMMIT;
// or ROLLBACK;
```

### 10.8 Profiling
```cypher
PROFILE MATCH (n:Person) WHERE n.age > 30 RETURN n.name;
```

### 10.9 Unsupported Neo4j Features
- FOREACH clause (use UNWIND instead)
- FINISH clause (use RETURN COUNT(*) instead)
- CALL <subquery> syntax
- Manual index creation on custom properties
- Filter on node labels in WHERE (e.g., WHERE n:Person)
- Properties inside node patterns in WHERE

---

## Performance Best Practices

1. **Use COPY FROM** for bulk imports instead of CREATE/MERGE
2. **Leverage primary key indices** for fast lookups
3. **Use LIMIT** to restrict large result sets
4. **Consider query hints** for join order optimization
5. **Use projected graphs** for algorithms to focus on relevant subsets
6. **Enable caching** for remote file access with HTTP_CACHE_FILE=TRUE
7. **Use TOP parameter** in FTS queries for better performance
8. **Monitor buffer size** for large graphs with memory-intensive algorithms

## Error Handling and Best Practices

1. **Always terminate statements** with semicolon
2. **Use prepared statements** to avoid injection attacks
3. **Be mindful of case-insensitivity** in queries
4. **Variable-length relationships** need upper bounds
5. **Extensions must be loaded** per session
6. **Projected graphs** are bound to connection instance
7. **FTS indexes** automatically update on data changes
8. **Vector indexes** support filtered searches with Cypher predicates
