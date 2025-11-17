# Filename Sanitization Fix

## Problem

Video upload was failing with error:

```
InvalidKey: Invalid key: 955a1bcb-fff7-4ead-9d1c-d2f038b41bb0/To Be Hero X Theme Song Full   New Type of Hero - Sub Español  AMV  - El Cóndor Anime - コンドル (1080p, h264).mp4
```

## Root Cause

Supabase Storage doesn't accept filenames with:
- Special characters (parentheses, pipes, etc.)
- Multiple consecutive spaces
- Non-ASCII characters (Japanese: コンドル, Spanish: ñ)
- Very long filenames

## Solution

Created a filename sanitizer that:

1. **Normalizes Unicode** - Converts accented characters to ASCII equivalents
   - `Español` → `Espanol`
   - `ñ` → `n`

2. **Removes Special Characters** - Replaces with underscores
   - `(1080p, h264)` → `_1080p_h264_`
   - Multiple spaces → single underscore

3. **Generates Unique Names** - Adds file hash to prevent collisions
   - `video.mp4` → `video_abc12345.mp4`

4. **Preserves Original** - Stores original filename in metadata

## Changes Made

### 1. Created `app/utils/filename_sanitizer.py`

Two main functions:
- `sanitize_filename()` - Cleans filename for storage
- `generate_unique_filename()` - Adds uniqueness using file hash

### 2. Updated `app/controllers/file_controller.py`

```python
# Before
file_path_in_bucket = f"{user_id}/{filename}"

# After
original_filename = filename
sanitized_filename = generate_unique_filename(filename, file_hash)
file_path_in_bucket = f"{user_id}/{sanitized_filename}"
```

### 3. Metadata Preservation

Original filename is preserved in the metadata:

```python
"metadata": {
    ...enhanced_metadata,
    "original_filename": original_filename  # User sees this
}
```

## Examples

| Original Filename | Sanitized Filename |
|-------------------|-------------------|
| `To Be Hero - Español (1080p).mp4` | `To_Be_Hero_-_Espanol_1080p_abc12345.mp4` |
| `My File (2024).pdf` | `My_File_2024_abc12345.pdf` |
| `コンドル.mp4` | `file_abc12345.mp4` |
| `file with spaces.jpg` | `file_with_spaces_abc12345.jpg` |

## Benefits

1. ✅ **No Upload Failures** - All filenames are storage-safe
2. ✅ **Unique Names** - Hash prevents collisions
3. ✅ **Original Preserved** - Users see original filename in metadata
4. ✅ **Cross-Platform** - Works on all operating systems
5. ✅ **Deduplication** - Same file hash = same sanitized name

## Testing

Run the test script:

```bash
python test_filename_sanitizer.py
```

This tests various edge cases including:
- Special characters
- Unicode characters
- Multiple spaces
- Very long filenames

## Try It Now

Upload your video again - it should work now! The filename will be sanitized automatically, but the original filename is preserved in the metadata for display purposes.

## Related Files

- `app/utils/filename_sanitizer.py` - Sanitization logic
- `app/controllers/file_controller.py` - Updated to use sanitizer
- `test_filename_sanitizer.py` - Test cases
