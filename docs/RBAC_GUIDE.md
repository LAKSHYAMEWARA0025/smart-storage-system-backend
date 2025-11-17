# Role-Based Access Control (RBAC) Guide

## Overview

The system implements role-based access control with three roles:
- **user**: Default role for all new signups
- **admin**: Full system access
- **moderator**: Limited admin capabilities (future use)

## User Roles

### User (Default)
- Upload and manage own files
- Access own data
- View own profile

### Admin
- All user permissions
- View all users
- View all files
- Manage user roles
- Access system statistics

### Moderator
- User permissions + limited admin features (to be defined)

## API Endpoints

### Authentication & Profile

#### Get Current User Profile
```http
GET /api/auth/profile
Authorization: Bearer <token>
```

**Response:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "role": "user"
}
```

### Admin Endpoints

#### Get All Users (Admin Only)
```http
GET /api/auth/admin/users
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "total": 10,
  "users": [
    {
      "user_id": "uuid",
      "role": "user",
      "created_at": "2024-11-16T..."
    }
  ]
}
```

#### Update User Role (Admin Only)
```http
PUT /api/auth/admin/users/{user_id}/role
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "new_role": "admin"
}
```

#### Get All Files (Admin Only)
```http
GET /api/files/admin/files/all
Authorization: Bearer <admin_token>
```

#### Get Storage Statistics (Admin Only)
```http
GET /api/files/admin/stats
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "total_files": 150,
  "total_size_bytes": 52428800,
  "total_size_mb": 50.0,
  "files_by_category": {
    "images": 80,
    "videos": 30,
    "documents": 40
  },
  "admin_user": "admin@example.com"
}
```

## Using Roles in Code

### Protect Endpoint with Role

```python
from app.security import require_admin, require_role, get_current_user_with_role
from app.models.role_model import UserRole

# Admin only
@router.get("/admin/endpoint")
async def admin_only(admin: dict = Depends(require_admin)):
    # Only admins can access
    return {"message": "Admin access granted"}

# Multiple roles
@router.get("/moderator/endpoint")
async def mod_or_admin(user: dict = Depends(require_role([UserRole.MODERATOR, UserRole.ADMIN]))):
    # Moderators or admins can access
    return {"message": "Access granted"}

# Any authenticated user with role info
@router.get("/profile")
async def get_profile(user: dict = Depends(get_current_user_with_role)):
    # Any authenticated user
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "role": user["role"]
    }
```

### Custom Role Check

```python
from app.security import require_role
from app.models.role_model import UserRole

@router.post("/special")
async def special_endpoint(user: dict = Depends(require_role([UserRole.ADMIN, UserRole.MODERATOR]))):
    # Custom logic based on role
    if user["role"] == "admin":
        # Admin-specific logic
        pass
    elif user["role"] == "moderator":
        # Moderator-specific logic
        pass
```

## Making a User Admin

### Method 1: SQL Query (Recommended)
```sql
-- In Supabase SQL Editor
UPDATE user_profiles
SET role = 'admin', updated_at = NOW()
WHERE id = (SELECT id FROM auth.users WHERE email = 'admin@example.com');
```

### Method 2: Via API (If you're already admin)
```http
PUT /api/auth/admin/users/{user_id}/role
Authorization: Bearer <admin_token>

{
  "new_role": "admin"
}
```

## Security Features

### Row Level Security (RLS)
- Users can only view/modify their own data
- Admins have special policies to view all data
- Enforced at database level

### JWT Token Validation
- All protected endpoints validate JWT tokens
- Tokens contain user identity
- Role fetched from database on each request

### Role Verification
- Role checked on every protected endpoint
- 403 Forbidden if insufficient permissions
- Clear error messages

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Invalid authentication credentials"
}
```

### 403 Forbidden
```json
{
  "detail": "Access denied. Required roles: ['admin']"
}
```

## Testing

### Test as User
1. Signup: `POST /api/auth/signup`
2. Login: `POST /api/auth/login`
3. Get profile: `GET /api/auth/profile` (should show role: "user")
4. Try admin endpoint: `GET /api/auth/admin/users` (should get 403)

### Test as Admin
1. Make user admin via SQL
2. Login: `POST /api/auth/login`
3. Get profile: `GET /api/auth/profile` (should show role: "admin")
4. Access admin endpoint: `GET /api/auth/admin/users` (should work)

## Future Enhancements

- [ ] Moderator-specific permissions
- [ ] Custom permissions per role
- [ ] Role hierarchy
- [ ] Temporary role assignments
- [ ] Audit logging for role changes
- [ ] API to create custom roles
