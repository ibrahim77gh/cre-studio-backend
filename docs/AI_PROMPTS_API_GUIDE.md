# AI Prompt Management - API Guide

## Overview

Super Users can now view and edit the AI prompts that generate campaign content (Meta Ads and Google Display) from the frontend. They can:
- Edit default prompts (used for all properties)
- Create custom prompts for specific properties (overrides default)
- Use template variables like `{campaign_name}`, `{messaging}` in prompts

---

## Setup

```bash
# 1. Run migration
python manage.py migrate property_app

# 2. Populate default prompts
python manage.py populate_default_prompts
```

---

## Frontend User Flow

### Step 1: View Prompts List

**User Action:** Super User navigates to "AI Prompt Settings" page

**What to Display:**
- List of default prompts (used for all properties)
- List of property-specific prompts (override defaults)
- Each prompt shows: Type (Meta/Google), Property name, Active status, Last updated by

**API Endpoint:**
```
GET /api/prompt-configurations/

Optional filters:
?property_id=5
?prompt_type=meta_ad
?is_active=true
```

**Response Fields:**
- `id` - Prompt ID
- `prompt_type` - "meta_ad" or "google_display"
- `property` - Property ID (null for default)
- `property_name` - Property name or "Default"
- `is_active` - Active status
- `updated_by_email` - Who last updated
- `updated_at` - When last updated

---

### Step 2: Edit Prompt

**User Action:** User clicks "Edit" on a prompt

**What to Display:**
- System Message (defines AI's role)
- User Prompt Template (with variable placeholders)
- Available Variables (as hints)
- Active/Inactive toggle

**API Endpoints:**

**Get Prompt Details:**
```
GET /api/prompt-configurations/{id}/
```

**Response includes:**
- `system_message` - AI role definition
- `user_prompt_template` - Template with variables
- `available_variables` - Object with variable descriptions
- `extracted_variables` - Array of variables found in template
- All other fields from list view

**Get Available Variables (for hints):**
```
GET /api/prompt-configurations/available_variables/

Optional: ?prompt_type=meta_ad
```

**Save Changes:**
```
PATCH /api/prompt-configurations/{id}/
Authorization: Bearer {token}

Body:
{
  "system_message": "...",
  "user_prompt_template": "...",
  "is_active": true
}
```

---

### Step 3: Create Property-Specific Prompt

**User Action:** User clicks "+ Create Custom Prompt"

**What to Display:**
- Prompt Type selector (Meta Ad / Google Display)
- Property selector (or leave null for default)
- System Message field
- User Prompt Template field (with variable hints)
- Active checkbox

**API Endpoint:**
```
POST /api/prompt-configurations/
Authorization: Bearer {token}

Body:
{
  "prompt_type": "meta_ad",
  "property": 5,  // or null for default
  "system_message": "...",
  "user_prompt_template": "...",
  "available_variables": {
    "messaging": "Campaign messaging and key points",
    "primary_goal": "Primary goal of the campaign",
    "target_audience": "Target audience description",
    "campaign_name": "Name of the campaign or key event"
  },
  "is_active": true
}
```

---

### Step 4: Delete Prompt

**User Action:** User clicks "Delete" on a prompt

**API Endpoint:**
```
DELETE /api/prompt-configurations/{id}/
Authorization: Bearer {token}
```

---

## How It Works

### Prompt Resolution
When generating campaign content:
1. Check for active property-specific prompt
2. If not found, use active default prompt
3. If no default, use hardcoded fallback

### Variable Substitution
Template variables are replaced with actual campaign data:

**Template:**
```
Campaign: {campaign_name}
Message: {messaging}
Goal: {primary_goal}
Audience: {target_audience}
```

**Becomes:**
```
Campaign: Summer Sale
Message: Get 50% off all items
Goal: conversions
Audience: Young shoppers aged 18-35
```

---

## API Reference

### Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/prompt-configurations/` | ✅ | List all prompts |
| GET | `/api/prompt-configurations/{id}/` | ✅ | Get prompt details |
| POST | `/api/prompt-configurations/` | 🔐 Super User | Create new prompt |
| PATCH | `/api/prompt-configurations/{id}/` | 🔐 Super User | Update prompt |
| DELETE | `/api/prompt-configurations/{id}/` | 🔐 Super User | Delete prompt |
| GET | `/api/prompt-configurations/available_variables/` | ✅ | Get available variables |

### Query Parameters (GET list)

- `property_id` - Filter by property ID
- `prompt_type` - Filter by type (meta_ad, google_display)
- `is_active` - Filter by active status (true/false)

### Permissions

- **Super Users:** Full CRUD access
- **Regular Users:** Read-only access (can view but not modify)

---

## Template Variables

These variables are available in all prompts and automatically populated from campaign data:

| Variable | Description |
|----------|-------------|
| `{messaging}` | Campaign messaging and key points |
| `{primary_goal}` | Primary goal (awareness, conversions, etc.) |
| `{target_audience}` | Target audience description |
| `{campaign_name}` | Name of the campaign or key event |

**Usage in templates:**
- Use `{variable_name}` syntax
- All variables will be replaced when AI generates content
- Invalid variables will cause validation errors

---

## Error Handling

### Common Errors

**1. Duplicate Prompt:**
```json
{
  "prompt_type": ["A meta_ad prompt already exists for property 'Luxury Mall'."]
}
```

**2. Permission Denied:**
```json
{
  "detail": "Only super users can create or modify prompt configurations."
}
```

**3. Invalid Variables:**
```json
{
  "user_prompt_template": ["Template contains variables not defined in available_variables: unknown_var"]
}
```

### Error Response Format

All validation errors return HTTP 400 with JSON body containing field-specific errors.

---

## Response Examples

### List Prompts
```json
[
  {
    "id": 1,
    "prompt_type": "meta_ad",
    "property": null,
    "property_name": "Default",
    "is_active": true,
    "updated_by_email": "admin@example.com",
    "updated_at": "2025-10-13T10:30:00Z"
  },
  {
    "id": 2,
    "prompt_type": "meta_ad",
    "property": 5,
    "property_name": "Luxury Mall",
    "is_active": true,
    "updated_by_email": "admin@example.com",
    "updated_at": "2025-10-13T11:00:00Z"
  }
]
```

### Prompt Details
```json
{
  "id": 1,
  "prompt_type": "meta_ad",
  "property": null,
  "property_name": "Default",
  "system_message": "You are an expert Meta ad copywriter...",
  "user_prompt_template": "Generate Meta ad content:\n\nMessaging: {messaging}\nGoal: {primary_goal}...",
  "available_variables": {
    "messaging": "Campaign messaging and key points",
    "primary_goal": "Primary goal of the campaign",
    "target_audience": "Target audience description",
    "campaign_name": "Name of the campaign or key event"
  },
  "extracted_variables": ["messaging", "primary_goal", "target_audience", "campaign_name"],
  "is_active": true,
  "created_by": 1,
  "created_by_email": "admin@example.com",
  "updated_by": 1,
  "updated_by_email": "admin@example.com",
  "created_at": "2025-10-13T10:00:00Z",
  "updated_at": "2025-10-13T10:30:00Z"
}
```

### Available Variables
```json
{
  "meta_ad": {
    "messaging": "Campaign messaging and key points",
    "primary_goal": "Primary goal of the campaign (e.g., awareness, conversions)",
    "target_audience": "Target audience description",
    "campaign_name": "Name of the campaign or key event"
  },
  "google_display": {
    "messaging": "Campaign messaging and key points",
    "primary_goal": "Primary goal of the campaign (e.g., awareness, conversions)",
    "target_audience": "Target audience description",
    "campaign_name": "Name of the campaign or key event"
  }
}
```

---

## UI Requirements

### Prompt List Page
- Display default prompts separately from property-specific
- Show prompt type, property name, active status
- "Edit" button for each prompt (Super User only)
- "+ Create Custom Prompt" button (Super User only)
- "Delete" button for property-specific prompts (Super User only)

### Edit/Create Modal
- System Message textarea
- User Prompt Template textarea
- Display available variables as hints near template field
- Active checkbox
- Property selector (for create only)
- Prompt type selector (for create only)
- Save/Cancel buttons

### Permission Control
- Only show edit/create/delete actions to Super Users
- Redirect non-super users if they try to access

### Variable Hints
Display near template field:
```
Available Variables:
• {messaging} - Campaign messaging and key points
• {primary_goal} - Primary goal of the campaign
• {target_audience} - Target audience description
• {campaign_name} - Name of the campaign or key event
```

---

## Testing Checklist

- [ ] Can list all prompts
- [ ] Can filter by property/type/active
- [ ] Can view prompt details
- [ ] Super User can create prompt
- [ ] Super User can edit prompt
- [ ] Super User can delete prompt
- [ ] Non-super user cannot modify
- [ ] Variable hints display correctly
- [ ] Validation errors display properly
- [ ] Can toggle active/inactive

---

## Default Prompts

After running `populate_default_prompts`, two default prompts are created:

### Meta Ad (Default)
- Generates: headlines, main copy, display copy, CTA
- Character limits: Headlines 50, Main copy 200, Display 325

### Google Display (Default)
- Generates: headlines, long headlines, descriptions
- Character limits: Headlines 30, Long headlines 90, Descriptions 90
- No exclamation marks allowed

---

## Summary

**Backend provides:**
- RESTful API for prompt CRUD operations
- Automatic prompt resolution (property-specific → default → fallback)
- Variable substitution system
- Super User permission enforcement

**Frontend needs to build:**
1. Prompt list page (with default/custom separation)
2. Edit prompt modal (system message + template editor)
3. Create prompt modal (with property selector)
4. Delete confirmation
5. Variable hints display
6. Permission guards for Super User only
