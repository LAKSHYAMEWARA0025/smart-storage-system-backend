-- Verify RLS policies on files table
-- Run this to check if the service role policy exists

SELECT 
    schemaname,
    tablename,
    policyname,
    cmd as command,
    roles,
    permissive,
    qual as using_clause,
    with_check
FROM pg_policies
WHERE tablename = 'files'
ORDER BY policyname;

-- Expected output should include:
-- 1. Service role bypass RLS (FOR ALL, service_role)
-- 2. Users can delete own files (DELETE, authenticated)
-- 3. Users can insert own files (INSERT, authenticated)
-- 4. Users can update own files (UPDATE, authenticated)
-- 5. Users can view own files (SELECT, authenticated)
