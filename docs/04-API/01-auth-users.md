# API Spec — Authentication & Users

---

## AUTH ENDPOINTS

---

### POST /auth/register
**Description:** Register a new user account.  
**Auth Required:** No  
**Rate Limit:** 10/hour per IP

**Request Body:**
```json
{
  "email": "john.doe@company.com",
  "password": "SecurePass@123",
  "confirm_password": "SecurePass@123",
  "first_name": "John",
  "last_name": "Doe",
  "department_id": 3
}
```

**Validation Rules:**
| Field | Rules |
|-------|-------|
| email | Required, valid email, max 255 chars, unique |
| password | Required, min 8 chars, 1 uppercase, 1 lowercase, 1 digit, 1 special char |
| confirm_password | Required, must match password |
| first_name | Required, 2–100 chars |
| last_name | Required, 2–100 chars |
| department_id | Optional, must exist |

**Success Response `201`:**
```json
{
  "status": "success",
  "data": {
    "message": "Registration successful. Please check your email to verify your account.",
    "user": {
      "id": 42,
      "uuid": "550e8400-e29b-41d4-a716-446655440000",
      "email": "john.doe@company.com",
      "first_name": "John",
      "last_name": "Doe",
      "role": "employee",
      "status": "pending_verification"
    }
  }
}
```

**Error Responses:**
| Code | Error Code | Condition |
|------|-----------|-----------|
| 400 | VALIDATION_ERROR | Missing/invalid fields |
| 409 | EMAIL_EXISTS | Email already registered |

---

### POST /auth/login
**Description:** Authenticate user and receive JWT tokens.  
**Auth Required:** No  
**Rate Limit:** 5/min per IP

**Request Body:**
```json
{
  "email": "john.doe@company.com",
  "password": "SecurePass@123"
}
```

**Success Response `200`:**
```json
{
  "status": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 900,
    "user": {
      "id": 42,
      "uuid": "550e8400-e29b-41d4-a716-446655440000",
      "email": "john.doe@company.com",
      "first_name": "John",
      "last_name": "Doe",
      "role": "employee",
      "department": { "id": 3, "name": "IT Support" },
      "avatar_url": null,
      "status": "active"
    }
  }
}
```

**Error Responses:**
| Code | Error Code | Condition |
|------|-----------|-----------|
| 401 | INVALID_CREDENTIALS | Wrong email or password |
| 403 | EMAIL_NOT_VERIFIED | Account not verified |
| 403 | ACCOUNT_LOCKED | Too many failed attempts |
| 403 | ACCOUNT_INACTIVE | Account disabled by admin |

---

### POST /auth/refresh
**Description:** Exchange refresh token for new access + refresh token pair.  
**Auth Required:** No (refresh token in body)

**Request Body:**
```json
{ "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." }
```

**Success Response `200`:**
```json
{
  "status": "success",
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "expires_in": 900
  }
}
```

**Error Responses:**
| Code | Error Code | Condition |
|------|-----------|-----------|
| 401 | INVALID_REFRESH_TOKEN | Invalid, expired, or blacklisted |

---

### POST /auth/logout
**Description:** Invalidate current session tokens.  
**Auth Required:** Yes

**Request Body:**
```json
{ "refresh_token": "eyJ..." }
```

**Success Response `200`:**
```json
{ "status": "success", "data": { "message": "Logged out successfully." } }
```

---

### POST /auth/forgot-password
**Description:** Send password reset email.  
**Auth Required:** No  
**Rate Limit:** 3/hour per email

**Request Body:**
```json
{ "email": "john.doe@company.com" }
```

**Success Response `200`:** *(Same response regardless of whether email exists — prevents enumeration)*
```json
{ "status": "success", "data": { "message": "If that email exists, a reset link has been sent." } }
```

---

### POST /auth/reset-password
**Description:** Reset password using token from email.  
**Auth Required:** No

**Request Body:**
```json
{
  "token": "abc123def456...",
  "password": "NewSecurePass@456",
  "confirm_password": "NewSecurePass@456"
}
```

**Success Response `200`:**
```json
{ "status": "success", "data": { "message": "Password reset successfully." } }
```

**Error Responses:**
| Code | Error Code | Condition |
|------|-----------|-----------|
| 400 | INVALID_RESET_TOKEN | Token invalid or expired |

---

### POST /auth/verify-email
**Description:** Verify email address using token from registration email.  
**Auth Required:** No

**Request Body:**
```json
{ "token": "abc123def456..." }
```

**Success Response `200`:**
```json
{ "status": "success", "data": { "message": "Email verified. You can now log in." } }
```

---

### POST /auth/resend-verification
**Description:** Resend email verification link.  
**Auth Required:** No  
**Rate Limit:** 2/hour per email

**Request Body:**
```json
{ "email": "john.doe@company.com" }
```

---

## USER ENDPOINTS

---

### GET /users
**Description:** List all users.  
**Auth Required:** Yes  
**Roles:** Admin, Super Admin

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| page | int | Page number (default: 1) |
| per_page | int | Items per page (default: 20, max: 100) |
| role | string | Filter by role name |
| department_id | int | Filter by department |
| status | string | Filter by status |
| search | string | Search name or email |
| sort_by | string | created_at \| name \| email (default: created_at) |
| order | string | asc \| desc (default: desc) |

**Success Response `200`:**
```json
{
  "status": "success",
  "data": [
    {
      "id": 42,
      "uuid": "550e8400-e29b-41d4-a716-446655440000",
      "email": "john.doe@company.com",
      "first_name": "John",
      "last_name": "Doe",
      "role": "employee",
      "department": { "id": 3, "name": "IT Support" },
      "status": "active",
      "avatar_url": null,
      "last_login_at": "2026-07-05T18:00:00Z",
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "page": 1, "per_page": 20, "total_items": 156,
    "total_pages": 8, "has_next": true, "has_prev": false
  }
}
```

---

### GET /users/me
**Description:** Get current authenticated user's profile.  
**Auth Required:** Yes  
**Roles:** All

**Success Response `200`:**
```json
{
  "status": "success",
  "data": {
    "id": 42,
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "email": "john.doe@company.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1-555-0123",
    "role": "employee",
    "department": { "id": 3, "name": "IT Support" },
    "status": "active",
    "avatar_url": "https://res.cloudinary.com/...",
    "timezone": "UTC",
    "notification_prefs": { "email": true, "in_app": true },
    "last_login_at": "2026-07-05T18:00:00Z",
    "created_at": "2026-01-01T00:00:00Z"
  }
}
```

---

### PUT /users/me
**Description:** Update current user's profile.  
**Auth Required:** Yes  
**Roles:** All

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1-555-0123",
  "timezone": "America/New_York",
  "notification_prefs": { "email": true, "in_app": true }
}
```

---

### GET /users/:id
**Description:** Get a specific user's profile.  
**Auth Required:** Yes  
**Roles:** Admin, Super Admin

**Success Response `200`:** *(Same as GET /users/me)*

---

### PUT /users/:id
**Description:** Update a user (admin use).  
**Auth Required:** Yes  
**Roles:** Admin, Super Admin

**Request Body:**
```json
{
  "role_id": 3,
  "department_id": 5,
  "status": "active"
}
```

---

### DELETE /users/:id
**Description:** Soft-delete a user account.  
**Auth Required:** Yes  
**Roles:** Super Admin

**Success Response `204`:** *(No content)*

---

### POST /users/me/avatar
**Description:** Upload user avatar image.  
**Auth Required:** Yes  
**Content-Type:** `multipart/form-data`

**Form Fields:**
| Field | Type | Rules |
|-------|------|-------|
| avatar | file | Required, JPG/PNG, max 2MB |

**Success Response `200`:**
```json
{ "status": "success", "data": { "avatar_url": "https://res.cloudinary.com/..." } }
```

---

### PUT /users/me/change-password
**Description:** Change password for authenticated user.  
**Auth Required:** Yes

**Request Body:**
```json
{
  "current_password": "OldPass@123",
  "new_password": "NewPass@456",
  "confirm_password": "NewPass@456"
}
```

**Success Response `200`:**
```json
{ "status": "success", "data": { "message": "Password changed. All sessions have been invalidated." } }
```
