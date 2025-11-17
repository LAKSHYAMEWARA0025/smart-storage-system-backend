# Fix: Media Upload RLS Error

## Problem

You're getting this error when uploading media files:

```
500 Internal Server Error
{
  "detail": "{'statusCode': 400, 'error': 'Unauthorized', 'message': 'new row violates row-level security policy'}"
}
```

## Root Cause

The `files` table in your Supabase database has Row-Level Security (RLS) enabled with policies for `authenticated` users only:

- Users can insert own files (INSERT, authenticated)
- Users can view own files (SELECT, authenticated)
- Users can update own files (UPDATE, authenticated)
- Users can delete own files (DELETE, authenticated)

**The problem:** There's no policy for the `service_role`. When your backend uses `supabase_admin` (service role client) to insert files, it's not operating as an authenticated user, so all the existing policies don't apply and the insert is blocked.

## Solution

You need to add RLS policies that explicitly allow the service role to bypass RLS restrictions.

### Step 1: Run the SQL Fix

1. Open your **Supabase Dashboard**
2. Go to **SQL Editor**
3. Copy and paste the contents of `fix_rls_policy.sql`
4. Click **Run**

This will add a single policy:
- **"Service role bypass RLS"** - Allows the service role to perform any operation on the files table

Your existing user policies will remain unchanged.

### Step 2: Verify the Fix

Run the debug script to verify everything is working:

```bash
python debug_rls_issue.py
```

This script will:
- Check your environment variables
- Test service role access
- Attempt a test insert
- Diagnose any remaining issues

### Step 3: Test Media Upload

Try uploading a media file again through your API:

```bash
curl -X POST "http://localhost:8000/api/files/upload" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@test_image.jpg" \
  -F "tags=test,debug" \
  -F "description=Test upload after RLS fix"
```

## Alternative Solution (Less Secure)

If you don't need RLS protection on the `files` table, you can simply disable it:

```sql
ALTER TABLE files DISABLE ROW LEVEL SECURITY;
```

**Warning:** This removes all RLS protection, meaning any authenticated user could potentially access or modify any file record (though your application logic still enforces user ownership).

## Understanding the Issue

### What is RLS?

Row-Level Security (RLS) is a PostgreSQL feature that restricts which rows users can access in a table. It's enforced at the database level, providing an additional security layer.

### Why Did This Happen?

Your code correctly uses the service role client (`supabase_admin`), which should bypass RLS. However, when RLS is enabled on a table, you need to explicitly create a policy that allows the service role to bypass it.

### The Fix Explained

The SQL script creates this policy:

```sql
CREATE POLICY "Service role can do anything" ON files
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
```

This tells PostgreSQL: "Allow the service role to perform any operation on any row in the files table."

## Verification Checklist

After applying the fix, verify:

- [ ] SQL script ran without errors
- [ ] Debug script shows "✅ Service role can INSERT into files table"
- [ ] Media upload works through the API
- [ ] Files appear in the database
- [ ] Users can view their uploaded files

## Additional Notes

### Service Role vs Anon Key

- **Anon Key** (`SUPABASE_KEY`): Used for client-side operations, respects RLS
- **Service Role Key** (`SUPABASE_SERVICE_KEY`): Used for server-side operations, can bypass RLS with proper policies

### Security Best Practices

1. **Keep RLS enabled** - It provides defense in depth
2. **Use service role only on the backend** - Never expose it to clients
3. **Validate user ownership in application code** - Don't rely solely on RLS
4. **Audit service role usage** - Log all operations that bypass RLS

## Troubleshooting

### Issue: "Service role can do anything" policy already exists

**Solution:** The policy was already created. Try uploading again.

### Issue: Still getting RLS errors after applying fix

**Possible causes:**
1. Wrong service key in `.env` file
2. Policy not applied to correct table
3. Cache issue - restart your application

**Debug steps:**
```bash
# 1. Verify environment variables
cat .env | grep SUPABASE_SERVICE_KEY

# 2. Run debug script
python debug_rls_issue.py

# 3. Check Supabase logs
# Go to Supabase Dashboard > Logs > Database
```

### Issue: Debug script fails with connection error

**Solution:** Check your `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in `.env`

## Related Files

- `fix_rls_policy.sql` - SQL script to fix RLS policies
- `debug_rls_issue.py` - Python script to diagnose RLS issues
- `app/controllers/file_controller.py` - File upload implementation
- `app/config.py` - Supabase client configuration
- `docs/RBAC_GUIDE.md` - Role-based access control documentation

## Need More Help?

If you're still experiencing issues:

1. Check the application logs for detailed error messages
2. Review Supabase Dashboard > Logs > Database for RLS violations
3. Verify your service role key is correct
4. Ensure the `files` table exists and has the correct schema

## Success Indicators

You'll know the fix worked when:

1. ✅ Media uploads complete without errors
2. ✅ Files appear in Supabase Storage
3. ✅ File records are created in the `files` table
4. ✅ Users can retrieve their uploaded files
5. ✅ Cache invalidation works correctly
