# Upload Worker Fixes - Summary

## Issues Fixed

### 1. **Merged Schema Not Being Processed**
**Problem:** When user selected the merged schema option with `schema_id = "merged_all"`, the worker only looped through `schemas_detected` and never processed the merged schema.

**Solution:** Added logic to detect if merged schema is selected and process it accordingly:
```python
if 'merged_all' in decisions and analysis_data.merged_schema:
    schemas_to_process = [analysis_data.merged_schema]
else:
    schemas_to_process = analysis_data.schemas_detected
```

### 2. **Custom Name Not Being Used**
**Problem:** Even when user provided a custom name like "users_subscription", the system was using the filename-derived name "testnosql".

**Solution:** The merged schema now correctly uses the custom_name from the decision:
```python
decision = decisions.get(schema_id, {})
custom_name = decision.get('custom_name')
base_name = custom_name or schema_detection['suggested_name']
```

### 3. **Merged Schema Data Not Being Retrieved**
**Problem:** The `parsed_data` is keyed by individual schema IDs, but merged schema needs all data combined.

**Solution:** Added special handling for merged schema data:
```python
if schema_id == 'merged_all':
    # For merged schema, get all data
    schema_data = []
    for data_list in analysis_data.parsed_data.values():
        schema_data.extend(data_list)
else:
    # For individual schema, get specific data
    schema_data = analysis_data.parsed_data.get(schema_id, [])
```

### 4. **Duplicate Schema Registry Entries**
**Problem:** When uploading data multiple times with action='create', the system tried to create duplicate schema registry entries, causing MongoDB unique key errors:
```
E11000 duplicate key error: schema_name_1_version_1 dup key: { schema_name: "testnosql", version: 1 }
```

**Solution:** Added existence check before creating schema registry entry:
```python
existing_schema = schema_registry.find_by_name_and_user(base_name, user_id)

if existing_schema:
    # Schema exists - append data
    schema_registry.increment_record_count(existing_schema.schema_id, count)
else:
    # Schema doesn't exist - create new
    schema_registry.create_schema(...)
```

### 5. **User Isolation Not Enforced**
**Problem:** No check to ensure data is only added to schemas owned by the same user.

**Solution:** Always use `find_by_name_and_user(base_name, user_id)` which filters by user_id, ensuring:
- User A's "users_subscription" is separate from User B's "users_subscription"
- Data can only be added to schemas owned by the same user

## Changes Made

### File: `app/workers/upload_worker.py`

#### Change 1: Determine Which Schemas to Process (Lines ~151-165)
**Before:**
```python
# Process each schema
for idx, schema_detection in enumerate(analysis_data.schemas_detected):
    schema_id = schema_detection['schema_id']
    decision = decisions.get(schema_id, {})
    schema_data = analysis_data.parsed_data.get(schema_id, [])
```

**After:**
```python
# Determine which schemas to process
if 'merged_all' in decisions and analysis_data.merged_schema:
    schemas_to_process = [analysis_data.merged_schema]
else:
    schemas_to_process = analysis_data.schemas_detected

# Process each schema
for idx, schema_detection in enumerate(schemas_to_process):
    schema_id = schema_detection['schema_id']
    decision = decisions.get(schema_id, {})
    
    # Get parsed data
    if schema_id == 'merged_all':
        schema_data = []
        for data_list in analysis_data.parsed_data.values():
            schema_data.extend(data_list)
    else:
        schema_data = analysis_data.parsed_data.get(schema_id, [])
```

#### Change 2: SQL Schema Registry Logic (Lines ~330-370)
**Before:**
```python
# Store in registry (only if creating new, not evolving)
if action != 'evolve':
    schema_registry.create_schema(...)
else:
    existing_schema = schema_registry.find_by_name_and_user(base_name, user_id)
    # ... evolution logic
```

**After:**
```python
# Check if schema already exists for this user
existing_schema = schema_registry.find_by_name_and_user(base_name, user_id)

if existing_schema:
    if action == 'create':
        # Append data to existing schema
        schema_registry.increment_record_count(...)
    elif action == 'evolve':
        # Handle evolution
        # ... evolution logic
else:
    # Create new schema
    schema_registry.create_schema(...)
```

#### Change 3: NoSQL Schema Registry Logic (Lines ~440-480)
**Same pattern as SQL** - Check for existence before creating, handle both 'create' and 'evolve' actions properly.

## Behavior Changes

### Before Fix:
1. ❌ Merged schema ignored, always used individual schemas
2. ❌ Custom name ignored, always used filename-derived name
3. ❌ Duplicate uploads caused MongoDB unique key errors
4. ❌ No user isolation check

### After Fix:
1. ✅ Merged schema properly processed when selected
2. ✅ Custom name "users_subscription" correctly used
3. ✅ Duplicate uploads append data instead of creating duplicates
4. ✅ User isolation enforced - data only added to user's own schemas

## Testing Scenarios

### Scenario 1: First Upload with Merged Schema
**Input:**
```json
{
  "decisions": {
    "merged_all": {
      "action": "create",
      "custom_name": "users_subscription"
    }
  }
}
```

**Expected:**
- Creates collection: `user_955a1bcb_users_subscription_v1`
- Creates schema registry entry: `schema_name = "users_subscription"`
- Inserts all data

### Scenario 2: Second Upload with Same Name
**Input:** Same as Scenario 1

**Expected:**
- Uses existing collection: `user_955a1bcb_users_subscription_v1`
- Finds existing schema registry entry
- Appends data (no duplicate error)
- Increments record count

### Scenario 3: Different User, Same Name
**User A uploads "users_subscription"**
- Creates: `user_aaaaaaaa_users_subscription_v1`
- Registry: `schema_name = "users_subscription", user_id = "user_a"`

**User B uploads "users_subscription"**
- Creates: `user_bbbbbbbb_users_subscription_v1`
- Registry: `schema_name = "users_subscription", user_id = "user_b"`

**Result:** ✅ Both schemas exist independently, no conflicts

### Scenario 4: Individual Schemas (Not Merged)
**Input:**
```json
{
  "decisions": {
    "schema_123": {
      "action": "create",
      "custom_name": "products"
    },
    "schema_456": {
      "action": "create",
      "custom_name": "orders"
    }
  }
}
```

**Expected:**
- Processes both individual schemas
- Creates separate collections/tables
- Each with their own registry entry

## Logs to Expect

### Successful Merged Schema Upload:
```
📦 Processing merged schema
📊 Merged schema contains 100 total records
📋 Collection name: user_955a1bcb_users_subscription_v1
✅ Inserted 100 documents into 'user_955a1bcb_users_subscription_v1'
✨ NoSQL: Creating new schema 'users_subscription' for user
✅ Upload job completed
```

### Duplicate Upload (Appending Data):
```
📦 Processing merged schema
📊 Merged schema contains 50 total records
📋 Collection name: user_955a1bcb_users_subscription_v1
Collection user_955a1bcb_users_subscription_v1 already exists
✅ Inserted 50 documents into 'user_955a1bcb_users_subscription_v1'
📊 NoSQL: Schema 'users_subscription' already exists for user, appending data
✅ Upload job completed
```

## Migration Notes

**No database migration required** - These are code-only changes.

**Existing data:** All existing schema registry entries and collections remain unchanged and will work correctly with the new logic.

## Related Files

- `app/workers/upload_worker.py` - Main changes
- `app/services/schema_registry.py` - Uses existing `find_by_name_and_user()` method
- `app/controllers/upload_controller.py` - No changes needed
- Frontend - No changes needed

## Conclusion

All issues have been resolved:
1. ✅ Merged schema is now properly processed
2. ✅ Custom names are correctly used
3. ✅ No more duplicate key errors
4. ✅ User isolation is enforced
5. ✅ Data can be appended to existing schemas

The system now correctly handles both merged and individual schemas, respects user-provided custom names, and prevents duplicate schema registry entries while maintaining proper user isolation.
