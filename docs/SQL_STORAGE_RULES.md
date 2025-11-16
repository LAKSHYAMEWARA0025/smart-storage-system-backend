# SQL Storage Eligibility Rules

## Overview

This document defines the comprehensive rules that determine whether uploaded data should be stored in SQL (PostgreSQL) or NoSQL (MongoDB) databases. The Smart Storage System analyzes incoming JSON data and applies these rules automatically to ensure optimal storage strategy.

---

## Core Principle

**Data must pass ALL eligibility criteria to be stored in SQL. If ANY rule fails, the data is stored in NoSQL (MongoDB).**

---

## Rule 1: Schema Consistency

### 1.1 Null Density Threshold

**Rule:** Null density must be ≤ 20%

**Calculation:**
```
null_density = (total_null_cells / total_cells) × 100

Where:
- total_cells = number_of_objects × number_of_unique_fields
- total_null_cells = sum of missing fields across all objects
```

**Example - FAIL (36% null density):**
```json
[
  {"id": 1, "name": "John", "email": "john@test.com"},
  {"id": 2, "name": "Jane", "email": "jane@test.com"},
  {"id": 3, "name": "Bob", "age": 35},
  {"id": 4, "name": "Alice", "phone": "123-456-7890"}
]
```
- Total cells: 4 rows × 5 fields = 20 cells
- Null cells: 2+2+2+2 = 8 nulls
- Null density: 8/20 = 40% ❌ (> 20%)
- **Result: NoSQL**

**Example - PASS (0% null density):**
```json
[
  {"id": 1, "name": "John", "age": 30, "email": "john@test.com"},
  {"id": 2, "name": "Jane", "age": 25, "email": "jane@test.com"},
  {"id": 3, "name": "Bob", "age": 35, "email": "bob@test.com"}
]
```
- All objects have all fields
- Null density: 0% ✅
- **Result: SQL (if other rules pass)**

### 1.2 Schema Variant Threshold

**Rule:** Number of schema variants must be ≤ sqrt(N)

Where N = total number of objects

**Calculation:**
```
max_allowed_variants = sqrt(number_of_objects)

If actual_variants > max_allowed_variants → NoSQL
```

**Example - FAIL (too many variants):**
```
100 objects with 15 different schema variants
- sqrt(100) = 10
- 15 > 10 ❌
- Result: NoSQL
```

**Example - PASS:**
```
100 objects with 8 different schema variants
- sqrt(100) = 10
- 8 ≤ 10 ✅
- Result: SQL (if other rules pass)
```

**Rationale:** This dynamic threshold prevents creating too many SQL tables while being flexible with data size. As data grows, more variance is tolerated proportionally.

---

## Rule 2: Data Structure Requirements

### 2.1 No Nested Objects

**Rule:** Data must NOT contain nested objects

**FAIL Example:**
```json
{
  "id": 1,
  "name": "John",
  "address": {              // ❌ Nested object
    "street": "123 Main St",
    "city": "NYC",
    "zip": "10001"
  }
}
```
**Result: NoSQL**

**PASS Example:**
```json
{
  "id": 1,
  "name": "John",
  "address_street": "123 Main St",
  "address_city": "NYC",
  "address_zip": "10001"
}
```
**Result: SQL (if other rules pass)**

### 2.2 No Array Fields

**Rule:** Data must NOT contain array fields

**FAIL Example:**
```json
{
  "id": 1,
  "name": "John",
  "tags": ["python", "fastapi", "mongodb"]  // ❌ Array field
}
```
**Result: NoSQL**

**PASS Example:**
```json
{
  "id": 1,
  "name": "John",
  "primary_tag": "python",
  "secondary_tag": "fastapi"
}
```
**Result: SQL (if other rules pass)**

### 2.3 Flat Structure Only

**Rule:** Only flat, single-level key-value structures are allowed for SQL

**Valid SQL Structure:**
```json
{
  "field1": "value",
  "field2": 123,
  "field3": true,
  "field4": "2024-01-01"
}
```

---

## Rule 3: Data Type Consistency

### 3.1 Type Agreement Threshold

**Rule:** For each field, ≥90% of objects must have compatible data types

**Process:**
1. For each field, count data type occurrences
2. Identify majority type
3. Attempt to convert all values to majority type
4. If conversion success rate < 90% → NoSQL

**Example - FAIL (60% conversion success):**
```json
[
  {"id": 1, "age": 25},           // int
  {"id": 2, "age": "thirty"},     // str (can't convert)
  {"id": 3, "age": 35},           // int
  {"id": 4, "age": "forty-five"}, // str (can't convert)
  {"id": 5, "age": 28}            // int
]
```
- Majority type: int (60%)
- Conversion failures: 2/5 = 40%
- Success rate: 60% ❌ (< 90%)
- **Result: NoSQL**

**Example - PASS (100% conversion success):**
```json
[
  {"id": 1, "age": 25},      // int
  {"id": 2, "age": "30"},    // str → int (success)
  {"id": 3, "age": 35.0},    // float → int (success)
  {"id": 4, "age": "40"},    // str → int (success)
  {"id": 5, "age": 28}       // int
]
```
- Majority type: int (60%)
- All conversions successful
- Success rate: 100% ✅
- **Result: SQL (if other rules pass)**

### 3.2 Type Conversion Rules

**Supported Conversions:**
- `str "25"` → `int 25` ✅
- `float 25.0` → `int 25` ✅
- `str "2024-01-01"` → `datetime` ✅
- `int 25` → `str "25"` ✅
- `str "twenty-five"` → `int` ❌ (fails)

**Tie-Breaker Rule:**
If two types have equal occurrences (50-50 split), prefer the more flexible type:
```
Priority: str > float > int > bool
```

**Example:**
```
50 objects with int, 50 objects with str
→ Choose str (more flexible)
```

---

## Rule 4: Field Overlap (for Schema Matching)

### 4.1 Overlap Threshold

**Rule:** When comparing with existing schemas, field overlap must be ≥70%

**Calculation:**
```
common_fields = fields_in_both_schemas
total_unique_fields = all_unique_fields_combined

overlap_percentage = (common_fields / total_unique_fields) × 100
```

**Example - Schema Evolution Candidate:**
```
Existing schema: {id, name, email}           // 3 fields
New data:        {id, name, email, phone}    // 4 fields

Common fields: 3 (id, name, email)
Total unique fields: 4
Overlap: 3/4 = 75% ✅

Result: Can evolve existing schema (with user confirmation)
```

**Example - New Schema Required:**
```
Existing schema: {id, name, email}           // 3 fields
New data:        {product_id, price, stock}  // 3 fields

Common fields: 0
Total unique fields: 6
Overlap: 0/6 = 0% ❌

Result: Create new separate table/collection
```

---

## Complete Decision Flow

```
┌─────────────────────────┐
│   Data Upload           │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Parse & Analyze       │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Has nested objects      │
│ or arrays?              │
└───────────┬─────────────┘
            │
    ┌───────┴───────┐
    │ YES           │ NO
    ▼               ▼
┌────────┐   ┌─────────────────────┐
│ NoSQL  │   │ Calculate           │
└────────┘   │ null_density        │
             └──────────┬──────────┘
                        │
                        ▼
             ┌─────────────────────┐
             │ null_density > 20%? │
             └──────────┬──────────┘
                        │
                ┌───────┴───────┐
                │ YES           │ NO
                ▼               ▼
             ┌────────┐   ┌─────────────────────┐
             │ NoSQL  │   │ Count schema        │
             └────────┘   │ variants            │
                          └──────────┬──────────┘
                                     │
                                     ▼
                          ┌─────────────────────┐
                          │ variants > sqrt(N)? │
                          └──────────┬──────────┘
                                     │
                             ┌───────┴───────┐
                             │ YES           │ NO
                             ▼               ▼
                          ┌────────┐   ┌─────────────────────┐
                          │ NoSQL  │   │ Normalize data      │
                          └────────┘   │ types               │
                                       └──────────┬──────────┘
                                                  │
                                                  ▼
                                       ┌─────────────────────┐
                                       │ Conversion          │
                                       │ success < 90%?      │
                                       └──────────┬──────────┘
                                                  │
                                          ┌───────┴───────┐
                                          │ YES           │ NO
                                          ▼               ▼
                                       ┌────────┐   ┌─────────────────────┐
                                       │ NoSQL  │   │ Check schema        │
                                       └────────┘   │ registry            │
                                                    └──────────┬──────────┘
                                                               │
                                                               ▼
                                                    ┌─────────────────────┐
                                                    │ Existing schema     │
                                                    │ found?              │
                                                    └──────────┬──────────┘
                                                               │
                                                       ┌───────┴───────┐
                                                       │ YES           │ NO
                                                       ▼               ▼
                                            ┌─────────────────┐  ┌──────────────┐
                                            │ Field overlap   │  │ Create new   │
                                            │ ≥ 70%?          │  │ SQL table    │
                                            └────────┬────────┘  └──────────────┘
                                                     │
                                             ┌───────┴───────┐
                                             │ YES           │ NO
                                             ▼               ▼
                                  ┌──────────────────┐  ┌──────────────┐
                                  │ Schema evolution │  │ Create new   │
                                  │ (ask user)       │  │ SQL table    │
                                  └──────────────────┘  └──────────────┘
```

---

## SQL Eligibility Checklist

Before storing data in SQL, verify:

- ✅ Null density ≤ 20%
- ✅ Schema variants ≤ sqrt(N)
- ✅ No nested objects
- ✅ No array fields
- ✅ Flat structure only
- ✅ Data type consistency ≥ 90% (after normalization)
- ✅ Field overlap ≥ 70% (for schema matching)

**If ANY checkbox fails → Store in NoSQL (MongoDB)**

---

## Examples Summary

### Example 1: Perfect SQL Candidate ✅

```json
[
  {"id": 1, "name": "John", "age": 30, "email": "john@test.com"},
  {"id": 2, "name": "Jane", "age": 25, "email": "jane@test.com"},
  {"id": 3, "name": "Bob", "age": 35, "email": "bob@test.com"}
]
```

**Analysis:**
- Flat structure ✅
- No nested objects/arrays ✅
- Consistent schema (1 variant) ✅
- Null density: 0% ✅
- Type consistency: 100% ✅

**Result: SQL (PostgreSQL)**

---

### Example 2: NoSQL - Nested Objects ❌

```json
[
  {
    "id": 1,
    "name": "John",
    "address": {
      "city": "NYC",
      "zip": "10001"
    }
  }
]
```

**Analysis:**
- Has nested objects ❌

**Result: NoSQL (MongoDB)**

---

### Example 3: NoSQL - High Null Density ❌

```json
[
  {"id": 1, "name": "John", "email": "john@test.com"},
  {"id": 2, "name": "Jane", "email": "jane@test.com"},
  {"id": 3, "name": "Bob", "age": 35},
  {"id": 4, "name": "Alice", "phone": "123-456-7890"}
]
```

**Analysis:**
- Null density: 40% ❌ (> 20%)

**Result: NoSQL (MongoDB)**

---

### Example 4: NoSQL - Too Many Variants ❌

```
100 objects with 15 different schema variants
```

**Analysis:**
- sqrt(100) = 10
- Variants: 15 > 10 ❌

**Result: NoSQL (MongoDB)**

---

### Example 5: NoSQL - Type Inconsistency ❌

```json
[
  {"id": 1, "age": 25},
  {"id": 2, "age": "thirty"},
  {"id": 3, "age": 35},
  {"id": 4, "age": "forty-five"},
  {"id": 5, "age": 28}
]
```

**Analysis:**
- Conversion success: 60% ❌ (< 90%)

**Result: NoSQL (MongoDB)**

---

## Configuration

All thresholds are configurable via environment variables:

```env
NULL_DENSITY_THRESHOLD=0.20          # 20%
FIELD_OVERLAP_THRESHOLD=0.70         # 70%
TYPE_CONSISTENCY_THRESHOLD=0.90      # 90%
```

---

## Notes

1. **Conservative Approach:** The system errs on the side of caution. When in doubt, it chooses NoSQL to prevent data loss or corruption.

2. **No Relationships:** The current system does NOT implement foreign key relationships between tables. Each table/collection is independent.

3. **Schema Evolution:** When new data matches an existing schema with ≥70% overlap, the system prompts the user to either evolve the schema or create a new table.

4. **Dynamic Thresholds:** The sqrt(N) formula for schema variants ensures the system scales naturally with data size.

5. **Type Flexibility:** The system attempts to normalize data types using the majority rule, making it more forgiving of minor inconsistencies.

---

**Last Updated:** Phase 1 Implementation
**Version:** 1.0.0
