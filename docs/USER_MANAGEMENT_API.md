# User Management APIs Documentation

## Overview

The User Management APIs provide a comprehensive system for managing users with hierarchical permissions based on roles within properties and property groups. The system enforces the following hierarchy:

- **Super User**: Can manage all user types across all properties and groups
- **Property Group Admin**: Can manage Property Admins and Tenants within their assigned property group
- **Property Admin**: Can manage Tenants within their assigned property
- **Tenant**: Cannot manage other users

## API Endpoints

All user management endpoints are prefixed with `/api/auth/user-management/`

### Base CRUD Operations

#### List Users
```
GET /api/auth/user-management/
```
Returns a paginated list of users that the current user can manage.

**Query Parameters:**
- `search`: Search by email, first name, or last name
- `ordering`: Order by fields like `email`, `first_name`, `last_name`, `date_joined`
- `page`: Page number for pagination

**Response:**
```json
{
  "count": 10,
  "next": "...",
  "previous": null,
  "results": [
    {
      "id": 1,
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "is_active": true,
      "is_staff": false,
      "is_superuser": false,
      "date_joined": "2024-01-01T00:00:00Z",
      "last_login": "2024-01-01T00:00:00Z",
      "role_info": {
        "role": "tenant",
        "property": {
          "id": 1,
          "name": "Sample Mall",
          "property_group": {
            "id": 1,
            "name": "Sample Group"
          }
        }
      }
    }
  ]
}
```

#### Create User
```
POST /api/auth/user-management/
```

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "password": "securepassword123",
  "confirm_password": "securepassword123",
  "first_name": "Jane",
  "last_name": "Smith",
  "role": "tenant",
  "property_id": 1
}
```

**Role Options:**
- `super_user` (Superusers only)
- `group_admin` (requires `property_group_id`)
- `property_admin` (requires `property_id`)
- `tenant` (requires `property_id`)

**Permission Rules:**
- Superusers can create any role
- Group Admins can create Property Admins and Tenants within their group
- Property Admins can create Tenants within their property
- Tenants cannot create users

#### Retrieve User
```
GET /api/auth/user-management/{id}/
```

#### Update User
```
PUT /api/auth/user-management/{id}/
PATCH /api/auth/user-management/{id}/
```

**Request Body (PATCH example):**
```json
{
  "first_name": "Updated Name",
  "role": "property_admin",
  "property_id": 2
}
```

#### Delete User
```
DELETE /api/auth/user-management/{id}/
```

**Behavior:**
- Superusers: Hard delete
- Other roles: Soft delete (sets `is_active = False`)

### Additional Actions

#### Activate User
```
POST /api/auth/user-management/{id}/activate/
```
Reactivates a deactivated user.

#### Deactivate User
```
POST /api/auth/user-management/{id}/deactivate/
```
Deactivates a user (users cannot deactivate themselves).

#### Get Manageable Scopes
```
GET /api/auth/user-management/my_manageable_scopes/
```

Returns the properties and groups that the current user can manage.

**Response:**
```json
{
  "can_manage_all": false,
  "properties": [
    {
      "id": 1,
      "name": "Sample Mall",
      "property_group": {
        "id": 1,
        "name": "Sample Group"
      }
    }
  ],
  "property_groups": [
    {
      "id": 1,
      "name": "Sample Group"
    }
  ]
}
```

#### Get Role Options
```
GET /api/auth/user-management/role_options/
```

Returns the roles that the current user can assign to others.

**Response:**
```json
{
  "roles": [
    {
      "value": "property_admin",
      "label": "Property Admin"
    },
    {
      "value": "tenant",
      "label": "Tenant"
    }
  ]
}
```

## Permission System

### Hierarchical Access Control

The system implements a strict hierarchy where higher-level roles can manage lower-level roles within their scope:

1. **Superusers** can manage everyone
2. **Property Group Admins** can manage:
   - Property Admins in their group's properties
   - Tenants in their group's properties
   - Users directly assigned to their group
3. **Property Admins** can manage:
   - Tenants in their specific property
4. **Tenants** cannot manage anyone

### Scope Limitations

- Users can only manage other users within their assigned properties/groups
- Users cannot modify themselves through these APIs (prevents privilege escalation)
- Role assignments are validated against the requester's permissions

## Error Responses

### 400 Bad Request
```json
{
  "email": ["User with this email already exists."],
  "password": ["This password is too short."],
  "role": ["You don't have permission to create users with role 'super_user'"]
}
```

### 403 Forbidden
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

## Usage Examples

### Frontend Integration

#### Creating a Property Admin (as Group Admin)
```javascript
const createPropertyAdmin = async (userData) => {
  const response = await fetch('/api/auth/user-management/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + accessToken
    },
    body: JSON.stringify({
      email: userData.email,
      password: userData.password,
      confirm_password: userData.password,
      first_name: userData.firstName,
      last_name: userData.lastName,
      role: 'property_admin',
      property_id: userData.propertyId
    })
  });
  
  if (!response.ok) {
    const errors = await response.json();
    throw new Error(JSON.stringify(errors));
  }
  
  return await response.json();
};
```

#### Getting Manageable Properties for Dropdown
```javascript
const getManageableScopes = async () => {
  const response = await fetch('/api/auth/user-management/my_manageable_scopes/', {
    headers: {
      'Authorization': 'Bearer ' + accessToken
    }
  });
  
  const data = await response.json();
  return data.properties; // Use for property selection dropdown
};
```

#### Filtering Users by Search
```javascript
const searchUsers = async (searchTerm) => {
  const response = await fetch(`/api/auth/user-management/?search=${encodeURIComponent(searchTerm)}`, {
    headers: {
      'Authorization': 'Bearer ' + accessToken
    }
  });
  
  return await response.json();
};
```

## Security Considerations

1. **Password Validation**: Uses Django's built-in password validators
2. **Permission Checks**: All operations are validated against user's role and scope
3. **Self-Protection**: Users cannot modify their own roles through these APIs
4. **Input Validation**: All inputs are validated for security and business rules
5. **Soft Deletes**: Non-superusers can only deactivate users, preserving data integrity

## Migration from Existing System

If you have existing user management code, you can:

1. Keep the old `/api/auth/manage-users/` endpoint for backward compatibility
2. Gradually migrate to the new `/api/auth/user-management/` endpoints
3. The new system is fully compatible with existing user and membership models

## Invitation System

### Overview

The user management system now uses an invitation-based workflow:

1. **User Creation**: When a user is created through the API, they are created as inactive (`is_active=False`)
2. **Invitation Email**: An invitation email is automatically sent to the user's email address
3. **Invitation Acceptance**: Users must accept their invitation by clicking the link in the email
4. **Account Activation**: Only after accepting the invitation is the user account activated (`is_active=True`)

### Invitation Email

The invitation email includes:
- Welcome message with site branding
- User's assigned role and property/group information
- Secure invitation link with token
- 7-day expiration period

### Invitation Acceptance

Users can accept invitations by visiting:
```
GET /api/auth/accept-invitation/{token}/
```

This endpoint:
- Validates the invitation token
- Checks if the invitation has expired (7 days)
- Activates the user account
- Returns confirmation message

### Resending Invitations

Administrators can resend invitation emails:
```
POST /api/auth/resend-invitation/{user_id}/
```

This is useful when:
- The original email was not received
- The invitation has expired
- The user requests a new invitation

### Manual Activation

The manual activation endpoint (`POST /api/auth/user-management/{id}/activate/`) now:
- Checks if the user has accepted their invitation
- Only activates users who have accepted invitations
- Provides appropriate error messages for unaccepted invitations

## Notes

- Users created through this API require invitation acceptance before they can log in
- Invitation emails are sent automatically upon user creation
- Users have 7 days to accept their invitation before it expires
- The system integrates with your existing Djoser authentication setup
- All timestamps are in UTC format