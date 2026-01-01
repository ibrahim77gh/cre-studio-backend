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

## App Assignment Management

### Overview

Users can be assigned to one or more apps to control their access. The app assignment system allows administrators to:
- Assign apps during user creation
- Update app assignments when editing users
- Manage app assignments through dedicated endpoints
- View which apps a user has access to

Superusers automatically have access to all active apps.

### App Assignment in User Creation/Update

When creating or updating users, you can include the `app_ids` field:

**Create User with App Assignment:**
```json
{
  "email": "newuser@example.com",
  "password": "securepassword123",
  "confirm_password": "securepassword123",
  "first_name": "Jane",
  "last_name": "Smith",
  "role": "tenant",
  "property_id": 1,
  "app_ids": [1, 2, 3]
}
```

**Update User's App Assignments:**
```
PATCH /api/auth/user-management/{id}/
```
```json
{
  "app_ids": [1, 2, 3]
}
```

### Dedicated App Assignment Endpoints

#### Assign Apps to User
```
POST /api/auth/user-management/{id}/assign_apps/
```

Assigns one or more apps to a user. Creates new app memberships without removing existing ones.

**Request Body:**
```json
{
  "app_ids": [1, 2, 3]
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Assigned 2 new app(s) to user",
  "user": {
    "id": 5,
    "email": "user@example.com",
    "apps": [
      {
        "id": 1,
        "name": "Campaign Planner",
        "slug": "campaign-planner"
      },
      {
        "id": 2,
        "name": "Analytics Dashboard",
        "slug": "analytics"
      }
    ]
  }
}
```

#### Remove Apps from User
```
POST /api/auth/user-management/{id}/remove_apps/
```

Removes one or more apps from a user's assignments.

**Request Body:**
```json
{
  "app_ids": [2]
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Removed 1 app(s) from user",
  "user": {
    "id": 5,
    "email": "user@example.com",
    "apps": [
      {
        "id": 1,
        "name": "Campaign Planner",
        "slug": "campaign-planner"
      }
    ]
  }
}
```

#### Synchronize User's App Assignments
```
POST /api/auth/user-management/{id}/sync_apps/
```

Replaces all existing app assignments with the provided list. Useful for bulk updates.

**Request Body:**
```json
{
  "app_ids": [1, 3]
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Synchronized 2 app(s) for user",
  "user": {
    "id": 5,
    "email": "user@example.com",
    "apps": [
      {
        "id": 1,
        "name": "Campaign Planner",
        "slug": "campaign-planner"
      },
      {
        "id": 3,
        "name": "Reporting Tool",
        "slug": "reporting"
      }
    ]
  }
}
```

#### Get User's Apps
```
GET /api/auth/user-management/{id}/apps/
```

Retrieves all apps assigned to a user.

**Response:**
```json
{
  "user": {
    "id": 5,
    "email": "user@example.com",
    "is_superuser": false
  },
  "apps": [
    {
      "id": 1,
      "name": "Campaign Planner",
      "slug": "campaign-planner",
      "description": "Plan and manage marketing campaigns"
    },
    {
      "id": 2,
      "name": "Analytics Dashboard",
      "slug": "analytics",
      "description": "View analytics and reports"
    }
  ]
}
```

### App Assignment in List Response

When listing users, the response includes app information:

```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "is_active": true,
  "role_info": {
    "role": "tenant",
    "property": {
      "id": 1,
      "name": "Sample Mall"
    }
  },
  "apps": [
    {
      "id": 1,
      "name": "Campaign Planner",
      "slug": "campaign-planner"
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

### App Access Control

- Users must be explicitly assigned to apps to access them
- Superusers automatically have access to all active apps
- App assignments are independent of property/role assignments
- Only active apps can be assigned to users
- Invalid app IDs will result in validation errors

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
      property_id: userData.propertyId,
      app_ids: [1, 2]  // Assign to Campaign Planner and Analytics apps
    })
  });
  
  if (!response.ok) {
    const errors = await response.json();
    throw new Error(JSON.stringify(errors));
  }
  
  return await response.json();
};
```

#### Assigning Apps to Existing User
```javascript
const assignAppsToUser = async (userId, appIds) => {
  const response = await fetch(`/api/auth/user-management/${userId}/assign_apps/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + accessToken
    },
    body: JSON.stringify({
      app_ids: appIds
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to assign apps');
  }
  
  return await response.json();
};
```

#### Removing Apps from User
```javascript
const removeAppsFromUser = async (userId, appIds) => {
  const response = await fetch(`/api/auth/user-management/${userId}/remove_apps/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + accessToken
    },
    body: JSON.stringify({
      app_ids: appIds
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to remove apps');
  }
  
  return await response.json();
};
```

#### Synchronizing User's App Access
```javascript
const syncUserApps = async (userId, appIds) => {
  const response = await fetch(`/api/auth/user-management/${userId}/sync_apps/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + accessToken
    },
    body: JSON.stringify({
      app_ids: appIds
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to sync apps');
  }
  
  return await response.json();
};
```

#### Getting User's Assigned Apps
```javascript
const getUserApps = async (userId) => {
  const response = await fetch(`/api/auth/user-management/${userId}/apps/`, {
    headers: {
      'Authorization': 'Bearer ' + accessToken
    }
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch user apps');
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

## Quick Reference: App Assignment Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/user-management/` | Create user with `app_ids` in body |
| PATCH | `/api/auth/user-management/{id}/` | Update user with `app_ids` in body |
| POST | `/api/auth/user-management/{id}/assign_apps/` | Add apps to user (incremental) |
| POST | `/api/auth/user-management/{id}/remove_apps/` | Remove apps from user |
| POST | `/api/auth/user-management/{id}/sync_apps/` | Replace all apps (bulk update) |
| GET | `/api/auth/user-management/{id}/apps/` | Get user's assigned apps |
| GET | `/api/auth/user-management/` | List users (includes `apps` field) |
| GET | `/api/auth/user-management/{id}/` | Get user details (includes `apps` field) |

## Common Use Cases

### Creating a User with App Access
1. Use `POST /api/auth/user-management/` with `app_ids` in the request body
2. User receives invitation email
3. User accepts invitation and gains access to assigned apps

### Adding App Access to Existing User
1. Use `POST /api/auth/user-management/{id}/assign_apps/` to add one or more apps
2. Or use `PATCH /api/auth/user-management/{id}/` with `app_ids` to update assignments

### Bulk Updating User's App Access
1. Use `POST /api/auth/user-management/{id}/sync_apps/` to replace all assignments at once
2. This removes all existing assignments and creates new ones

### Checking User's App Access
1. Use `GET /api/auth/user-management/{id}/apps/` to see all apps the user can access
2. Or use `GET /api/auth/user-management/{id}/` to see user details including apps