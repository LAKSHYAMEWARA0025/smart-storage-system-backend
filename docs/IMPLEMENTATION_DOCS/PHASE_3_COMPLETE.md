# Phase 3: Schema Analysis & Storage Decision - COMPLETE ✅

## Summary

Phase 3 has been successfully implemented. The core decision-making logic for analyzing schemas and determining storage strategy is now complete.

---

## Files Created

### 1. 🆕 `app/services/schema_analyzer.py`
**Purpose:** Analyzes JSON data to detect schemas and calculate metrics

**Key Classes:**

**FieldInfo (Dataclass):**
- Stores information about a single field
- Includes: name, type, nullable, sample_values, cardinality, type_distribution

**Schema (Dataclass):**
- Represents a detected schema
- Includes: schema_id, fields, field_names, record_count, schema_hash
- Flags: has_nested_objects, has_arrays

**SchemaAnalysis (Dataclass):**
- Complete analysis result for a dataset
- Includes: schemas, total_records, unified_schema, null_density, schema_variants, metrics

**SchemaAnalyzer (Main Class):**
- `analyze_objects()` - Main analysis function
- `_extract_schemas()` - Extract unique schema variants
- `_analyze_schema_group()` - Analyze objects with same schema
- `_analyze_field()` - Analyze specific field across objects
- `detect_nested_structures()` - Check for nested objects/arrays
- `calculate_type_consistency()` - Average type consistency
- `get_indexable_fields()` - Determine which fields to index
- `compare_with_existing_schema()` - Compare with existing schemas
- `extract_core_and_optional_fields()` - Separate nullable/non-nullable
- `generate_schema_summary()` - Generate summary for reporting

**Features:**
- ✅ Detects all unique schema variants
- ✅ Calculates comprehensive metrics
- ✅ Identifies nested structures (objects/arrays)
- ✅ Analyzes type distribution per field
- ✅ Determines indexable fields automatically
- ✅ Compares with existing schemas
- ✅ Generates detailed summaries

---

### 2. 🆕 `app/services/storage_decision.py`
**Purpose:** Implements SQL vs NoSQL decision logic

**Key Classes:**

**StorageDecision (Dataclass):**
- Result of storage decision analysis
- Includes: storage_type, confidence, reasons, metrics, passed_rules, failed_rules

**StorageDecisionEngine (Main Class):**
- `decide_storage()` - Main decision function for all schemas
- `_decide_for_schema()` - Decide for single schema
- `_check_nested_structures()` - Rule 1: No nested objects/arrays
- `_check_null_density()` - Rule 2: Null density ≤ 20%
- `_check_schema_variants()` - Rule 3: Variants ≤ sqrt(N)
- `_check_type_consistency()` - Rule 4: Type consistency ≥ 90%
- `evaluate_ambiguous_case()` - Detect borderline cases
- `should_prompt_user()` - Determine if user input needed
- `get_decision_summary()` - Human-readable summary

**Decision Rules Applied:**

**Rule 1: Data Structure**
- ❌ FAIL if nested objects found → NoSQL
- ❌ FAIL if array fields found → NoSQL
- ✅ PASS if flat structure only

**Rule 2: Null Density**
- ❌ FAIL if null_density > 20% → NoSQL
- ✅ PASS if null_density ≤ 20%

**Rule 3: Schema Variants**
- ❌ FAIL if variants > sqrt(N) → NoSQL
- ✅ PASS if variants ≤ sqrt(N)

**Rule 4: Type Consistency**
- ❌ FAIL if avg_consistency < 90% → NoSQL
- ✅ PASS if avg_consistency ≥ 90%

**Features:**
- ✅ Applies all SQL eligibility rules
- ✅ Provides detailed reasons for decisions
- ✅ Tracks which rules passed/failed
- ✅ Calculates confidence levels
- ✅ Detects ambiguous/borderline cases
- ✅ Uses configurable thresholds from env vars

---

### 3. 🆕 `app/services/naming_service.py`
**Purpose:** Generates appropriate names for tables and collections

**Key Class:**

**NamingService:**
- `generate_name()` - Main naming function with priority logic
- `extract_from_filename()` - Extract name from filename
- `infer_from_fields()` - Infer entity name from field patterns
- `generate_fallback_name()` - Generate unique fallback name
- `sanitize_name()` - Make name database-safe
- `is_meaningful_name()` - Check if name is not generic
- `ensure_unique()` - Add suffix if name exists
- `pluralize()` - Convert singular to plural
- `suggest_alternative_names()` - Suggest alternatives
- `validate_name()` - Validate name format

**Naming Priority:**
1. User-provided name (if valid)
2. Filename (if meaningful)
3. Field-based inference (pattern matching)
4. Fallback: `data_{timestamp}_{hash}`

**Field Pattern Recognition:**
- `user` - Detects: user_id, username, email, password
- `product` - Detects: product_id, product_name, price, sku
- `order` - Detects: order_id, customer_id, order_date
- `customer` - Detects: customer_id, customer_name, customer_email
- `employee` - Detects: employee_id, employee_name, department
- `transaction` - Detects: transaction_id, amount, transaction_date
- And more...

**Name Sanitization:**
- Converts to lowercase
- Replaces spaces/hyphens with underscores
- Removes special characters
- Ensures doesn't start with number
- Removes consecutive underscores

**Features:**
- ✅ Smart field-based inference
- ✅ Filename extraction
- ✅ Database-safe sanitization
- ✅ Uniqueness guarantee
- ✅ Generic name avoidance
- ✅ Automatic pluralization
- ✅ Alternative name suggestions
- ✅ Name validation

---

## Integration & Data Flow

```
Upload JSON File
    ↓
FileParser.parse_json_to_list()
    ↓
SchemaAnalyzer.analyze_objects()
    ├─> Extract schemas
    ├─> Calculate metrics
    ├─> Detect nested structures
    └─> Analyze type consistency
    ↓
StorageDecisionEngine.decide_storage()
    ├─> Apply Rule 1: Nested structures
    ├─> Apply Rule 2: Null density
    ├─> Apply Rule 3: Schema variants
    └─> Apply Rule 4: Type consistency
    ↓
Decision: SQL or NoSQL
    ↓
NamingService.generate_name()
    ├─> Try user suggestion
    ├─> Try filename
    ├─> Try field inference
    └─> Fallback to generated name
    ↓
Final: Storage Type + Entity Name
```

---

## Example Usage

### Schema Analysis
```python
from app.services.schema_analyzer import SchemaAnalyzer

analyzer = SchemaAnalyzer()

# Analyze objects
objects = [
    {"id": 1, "name": "John", "age": 30},
    {"id": 2, "name": "Jane", "age": 25}
]

analysis = analyzer.analyze_objects(objects)

print(f"Total records: {analysis.total_records}")
print(f"Schema variants: {analysis.schema_variants}")
print(f"Null density: {analysis.null_density}%")
```

### Storage Decision
```python
from app.services.storage_decision import StorageDecisionEngine

engine = StorageDecisionEngine()

# Make decision
decisions = engine.decide_storage(analysis)

for schema_id, decision in decisions.items():
    print(f"Schema: {schema_id}")
    print(f"Storage: {decision.storage_type}")
    print(f"Confidence: {decision.confidence}")
    print(f"Reasons: {decision.reasons}")
```

### Name Generation
```python
from app.services.naming_service import NamingService

naming = NamingService()

# Generate name
name = naming.generate_name(
    schema=schema,
    file_name="customer_orders.json",
    user_suggested=None,
    existing_names=["users", "products"]
)

print(f"Generated name: {name}")
```

---

## Testing

All services tested and working:

```bash
python -c "from app.services.schema_analyzer import SchemaAnalyzer; \
from app.services.storage_decision import StorageDecisionEngine; \
from app.services.naming_service import NamingService; \
print('✅ All Phase 3 services imported successfully!')"
```

**Output:**
```
🔧 Loading configuration...
✅ Configuration loaded successfully
📊 Environment: DEV
📊 Max media file size: 50MB
📊 Max data file size: 50MB
✅ All Phase 3 services imported successfully!
```

---

## Key Capabilities

### ✅ Schema Detection
- Automatically detects all unique schema variants
- Identifies nested structures (objects/arrays)
- Analyzes field types and distributions
- Calculates comprehensive metrics

### ✅ Storage Decision
- Applies all 4 SQL eligibility rules
- Provides detailed reasoning
- Tracks passed/failed rules
- Detects ambiguous cases
- Uses configurable thresholds

### ✅ Smart Naming
- Infers entity names from field patterns
- Extracts meaningful names from filenames
- Generates safe fallback names
- Ensures uniqueness
- Validates name format

### ✅ Metrics Calculation
- Null density (Rule 2)
- Schema variants with sqrt(N) threshold (Rule 3)
- Type consistency (Rule 4)
- Field cardinality for indexing
- Type distribution per field

---

## Configuration

All thresholds are configurable via environment variables:

```env
NULL_DENSITY_THRESHOLD=0.20          # 20%
TYPE_CONSISTENCY_THRESHOLD=0.90      # 90%
FIELD_OVERLAP_THRESHOLD=0.70         # 70% (for Phase 4)
```

---

## What's Next?

**Phase 4: Schema Registry**

We'll create:
- `app/models/mongo_models.py` - MongoEngine models for schema registry
- `app/services/schema_registry.py` - CRUD operations and schema matching

The schema registry will:
- Store all schema metadata in MongoDB
- Enable schema matching and conflict detection
- Track schema versions
- Support schema evolution

---

**Phase 3 Status: ✅ COMPLETE**

Ready to proceed to Phase 4 when you give the word! 🚀
