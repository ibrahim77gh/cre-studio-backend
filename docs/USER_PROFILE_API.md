# User Profile API Documentation

## Overview

The User Profile API allows logged-in users to update their own profile information. This API is separate from the User Management API and is designed for users to manage their own profiles without requiring admin permissions.

## API Endpoints

All profile endpoints are prefixed with `/api/auth/profile/`

### Get Current User Profile
```
GET /api/auth/profile/
```

Returns the current user's profile information.

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe"
}
```

### Update Current User Profile
```
PUT /api/auth/profile/
PATCH /api/auth/profile/
```

Updates the current user's profile information.

**Request Body (PATCH example):**
```json
{
  "first_name": "Updated First Name",
  "last_name": "Updated Last Name",
  "password": "newpassword123"
}
```

**Request Body (PUT example):**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "password": "newpassword123"
}
```

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "Updated First Name",
  "last_name": "Updated Last Name"
}
```

## Field Details

### Editable Fields
- `first_name` (string, optional): User's first name
- `last_name` (string, optional): User's last name  
- `password` (string, optional): New password (will be hashed automatically)

### Read-Only Fields
- `id` (integer): User ID (cannot be changed)
- `email` (string): User's email address (cannot be changed)

### Restricted Fields
The following fields are **NOT** available in this API and can only be managed by admins through the User Management API:
- `role` - User role and permissions
- `property_id` - Property assignment
- `property_group_id` - Property group assignment
- `is_active` - Account status
- `is_staff` - Staff status
- `is_superuser` - Superuser status

## Authentication

All endpoints require authentication. Include the JWT token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

Or use cookie-based authentication if configured.

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 400 Bad Request
```json
{
  "password": ["This password is too short. It must contain at least 8 characters."]
}
```

### 405 Method Not Allowed
```json
{
  "error": "Profile creation is handled through user registration"
}
```

## Usage Examples

### Update Profile Information
```bash
curl -X PATCH "http://localhost:8000/api/auth/profile/" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Jane",
    "last_name": "Smith"
  }'
```

### Change Password
```bash
curl -X PATCH "http://localhost:8000/api/auth/profile/" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "newsecurepassword123"
  }'
```

### Get Current Profile
```bash
curl -X GET "http://localhost:8000/api/auth/profile/" \
  -H "Authorization: Bearer <your_jwt_token>"
```

## Security Notes

1. **Password Validation**: Passwords are validated using Django's built-in password validators
2. **Role Restrictions**: Users cannot modify their own roles or permissions through this API
3. **Email Immutability**: Users cannot change their email address through this API
4. **Self-Only Access**: Users can only access and modify their own profile

## Related APIs

- **User Management API** (`/api/auth/user-management/`): For admins to manage other users
- **Authentication API** (`/api/auth/jwt/create/`): For user login and token generation
