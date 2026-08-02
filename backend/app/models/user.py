"""
User Models - Pydantic schemas for user authentication and profile management.

=== What are Pydantic models? ===
Pydantic models are Python classes that define the exact shape of data flowing
in and out of the API. They validate incoming requests (e.g., "is this a real
email address?") and structure outgoing responses (e.g., "never send the
password hash back to the frontend").

=== What this file defines ===
This file contains all data schemas related to users and organizations:
  - UserCreate:    What data is needed to register a new account
  - UserLogin:     What data is needed to log in
  - UserResponse:  What user data the API sends back to the frontend
  - OrgResponse:   What organization data the API sends back
  - TokenResponse: The authentication token returned after successful login

=== Relationship to the database ===
These models do NOT directly map to database tables. The database has its own
"users" and "organizations" tables (managed in Supabase). These Pydantic models
act as a translation layer:
  - Request models (UserCreate, UserLogin) validate data BEFORE it goes into the DB
  - Response models (UserResponse, OrgResponse) shape data AFTER it comes out of the DB

This separation is intentional -- we never want the raw DB row (which contains
the password hash) to accidentally leak to the client.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime


class UserCreate(BaseModel):
    """
    Schema for new user registration requests.

    Used by: POST /auth/register endpoint
    Sent by: The frontend sign-up form

    When a new user registers, the frontend sends this data. The backend then:
    1. Validates the email format (thanks to EmailStr)
    2. Hashes the password (never stored in plain text)
    3. Creates a user record in the "users" table
    4. Optionally creates an organization if org_name is provided
    """

    # The user's email address. EmailStr is a special Pydantic type that checks
    # the string is a valid email format (e.g., "user@example.com"). If someone
    # sends "not-an-email", Pydantic rejects the request with a clear error.
    email: EmailStr

    # The user's chosen password in plain text. This is ONLY used during transit
    # from the frontend to the backend. The backend immediately hashes it before
    # storing it in the database. The plain text password is never saved anywhere.
    # Minimum 8 characters; the upper bound is enforced by the validator below.
    password: str = Field(min_length=8)

    # The user's display name (e.g., "Jane Smith"). Shown in the dashboard UI
    # and used for personalization.
    full_name: str

    # Optional: the name of the organization to create (e.g., "Acme Corp").
    # If provided, a new organization is created and the user becomes its owner.
    # If omitted (None), the user might be added to an existing org via invite.
    org_name: str | None = None

    @field_validator("password")
    @classmethod
    def _password_within_bcrypt_limit(cls, v: str) -> str:
        # bcrypt only hashes the first 72 bytes of a password and bcrypt 4.x
        # raises on longer inputs. Reject early with a clean 422 instead of a 500.
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 bytes long.")
        return v


class UserLogin(BaseModel):
    """
    Schema for login requests.

    Used by: POST /auth/login endpoint
    Sent by: The frontend login form

    Contains only the credentials needed to authenticate. The backend verifies
    the password against the stored hash and returns a JWT token on success.
    """

    # The email address the user registered with. Used to look up the account.
    # Plain str (not EmailStr) — format validation belongs on signup, not login.
    email: str

    # The plain text password to verify against the stored hash.
    password: str


class UserResponse(BaseModel):
    """
    Schema for user data returned by the API.

    Used by: All endpoints that return user information (login, profile, etc.)
    Sent to: The frontend, which stores it in state for the dashboard

    IMPORTANT: Notice this model does NOT include "password" -- this is a
    deliberate security measure. Response models should never contain sensitive
    data like passwords, even hashed ones.
    """

    # The unique identifier for this user (UUID string from the database).
    # Used by the frontend to reference this user in subsequent API calls.
    id: str

    # The user's email address. Shown in the profile/settings area of the dashboard.
    email: str

    # The user's display name. Shown in the top-right corner of the dashboard
    # and in conversation views where agents interact.
    full_name: str

    # The ID of the organization this user belongs to. Every user must belong
    # to exactly one organization. This links to the "organizations" table.
    org_id: str

    # The user's role within their organization. Defaults to "owner" because
    # most users create their own org at signup. Other possible values might
    # include "admin" or "member" for team features.
    role: str = "owner"

    # Optional URL to the user's profile picture. Can be a Supabase storage URL
    # or an external URL (e.g., from Google OAuth). None means no avatar set.
    avatar_url: str | None = None

    # When this user account was created. Useful for "member since" displays
    # and admin audit purposes. Optional because it may not always be loaded.
    created_at: datetime | None = None


class OrgResponse(BaseModel):
    """
    Schema for organization data returned by the API.

    Used by: Endpoints that return org details (e.g., GET /org/me)
    Sent to: The frontend for displaying org info in settings

    An organization is the top-level grouping in BotForge. All bots, documents,
    and conversations belong to an organization. This enables multi-tenant
    isolation -- one org's data is never visible to another org.
    """

    # The unique identifier for this organization (UUID string).
    id: str

    # The display name of the organization (e.g., "Acme Corp").
    # Shown in the dashboard header and settings page.
    name: str

    # The subscription plan this org is on. Defaults to "free".
    # Plans control feature limits like number of bots, messages per month, etc.
    # Possible values: "free", "pro", "enterprise" (or similar tiered names).
    plan: str = "free"

    # The user ID of the person who created (and owns) this organization.
    # The owner has full admin privileges including billing and member management.
    owner_id: str

    # When this organization was created. Useful for billing start dates
    # and admin displays. Optional because it may not always be loaded.
    created_at: datetime | None = None


class TokenResponse(BaseModel):
    """
    Schema for the authentication response returned after successful login.

    Used by: POST /auth/login and POST /auth/register endpoints
    Sent to: The frontend, which stores the token for authenticated API calls

    This follows the OAuth2 convention for token responses, making it compatible
    with standard HTTP auth libraries on the frontend.
    """

    # The JWT (JSON Web Token) string. The frontend stores this (usually in
    # memory or localStorage) and sends it in the "Authorization: Bearer <token>"
    # header with every subsequent API request.
    access_token: str

    # The type of token. Always "bearer" in our case. This tells the frontend
    # how to format the Authorization header. Included because the OAuth2 spec
    # requires it, even though it's always the same value.
    token_type: str = "bearer"

    # The full user profile returned alongside the token. This saves the frontend
    # from making a separate "GET /me" request immediately after login -- it
    # already has all the user data it needs to render the dashboard.
    user: UserResponse
