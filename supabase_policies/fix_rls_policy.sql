-- Fix RLS policies for files table to allow service role operations
-- Run this in your Supabase SQL Editor
-- 
-- ISSUE: Your existing policies only apply to 'authenticated' role
-- The service role needs its own policy to bypass RLS

-- Add service role policy (keeps your existing policies intact)
CREATE POLICY "Service role bypass RLS" ON files
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Verify all policies
SELECT 
    policyname,
    cmd as command,
    roles,
    qual as using_expression,
    with_check as with_check_expression
FROM pg_policies
WHERE tablename = 'files'
ORDER BY policyname;
