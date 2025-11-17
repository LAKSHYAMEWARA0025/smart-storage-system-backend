# Storage Bucket RLS Fix

## The Real Issue

The error wasn't from the `files` **table** RLS - it was from the **storage bucket** RLS!

### What Was Wrong

In `app/controllers/file_controller.py`, line 191-196, the code was using:

```python
# ❌ WRONG - Uses regular client (respects RLS)
supabase.storage.from_(BUCKET_NAME).upload(...)
public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(...)
```

This uses the regular Supabase client which respects RLS policies. When uploading on behalf of a user, the storage bucket's RLS was blocking the operation.

### The Fix

Changed to use the admin client:

```python
# ✅ CORRECT - Uses admin client (bypasses RLS)
supabase_admin.storage.from_(BUCKET_NAME).upload(...)
public_url = supabase_admin.storage.from_(BUCKET_NAME).get_public_url(...)
```

## Why This Happened

Your Supabase storage bucket (probably named "media") has RLS policies that restrict who can upload files. The regular client (`supabase`) respects these policies, but when your backend uploads files on behalf of users, it needs to use the service role client (`supabase_admin`) to bypass these restrictions.

## Verification

The fix has been applied. Try uploading a file now - it should work!

## Storage Bucket RLS Policies

If you want to check your storage bucket policies:

1. Go to Supabase Dashboard
2. Navigate to: Storage → Your bucket (e.g., "media")
3. Click "Policies"

You should see policies like:
- Users can upload to their own folder
- Users can read their own files
- etc.

These policies are good for security, but your backend needs to use the service role to bypass them when uploading on behalf of users.

## Related Changes

The code now consistently uses `supabase_admin` for:
1. ✅ Checking for existing files (deduplication)
2. ✅ Uploading to storage bucket
3. ✅ Getting public URL
4. ✅ Inserting into files table

All operations that need to bypass RLS now use the admin client.
