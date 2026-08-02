"""
Authentication Router
======================

This router handles all authentication-related API endpoints for the BotForge platform.

Endpoints provided:
    POST /signup  - Register a new user and organization, returns a JWT token
    POST /login   - Authenticate an existing user with email/password, returns a JWT token
    GET  /me      - Retrieve the currently authenticated user's profile

Authentication Flow:
    1. User signs up or logs in via POST request with credentials.
    2. Server validates credentials and issues a JWT (JSON Web Token).
    3. The JWT is included in subsequent requests as a Bearer token in the
       Authorization header: "Authorization: Bearer <token>".
    4. Protected endpoints use Depends(get_current_user) to decode the JWT,
       extract the user ID from the "sub" claim, look up the user in the database,
       and inject the user dict into the endpoint function.

Design Decisions:
    - Passwords are hashed using bcrypt (via passlib) before storage. Plain-text
      passwords are never stored in the database.
    - Each new user automatically gets a new organization created for them (multi-tenant
      design). The user becomes the "owner" of that organization.
    - JWT expiration is configurable via settings.jwt_expiration_hours.
    - Passwords are hashed and verified with bcrypt (via passlib), imported once
      at module level so signup and login share a single, consistent code path.
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Depends
from jose import jwt
from passlib.hash import bcrypt

from app.config import get_settings
from app.database import get_supabase
from app.models.user import UserCreate, UserLogin, UserResponse, TokenResponse
from app.middleware.auth import get_current_user

# Create the router instance. This will be mounted on the main app with a prefix
# like "/api/auth", so endpoints here become "/api/auth/signup", "/api/auth/login", etc.
router = APIRouter()


def create_token(user_id: str) -> str:
    """
    Generate a JWT access token for the given user.

    How it works:
        1. Load application settings (secret key, algorithm, expiration).
        2. Build a payload with:
           - "sub" (subject): the user's unique ID, used to identify them later
           - "exp" (expiration): UTC timestamp after which the token is invalid
        3. Encode and sign the payload using the JWT secret and algorithm (e.g., HS256).
        4. Return the encoded token string.

    Args:
        user_id: The unique identifier of the user (UUID string).

    Returns:
        A signed JWT token string that the client will use for authenticated requests.
    """
    settings = get_settings()
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiration_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@router.post("/signup", response_model=TokenResponse)
async def signup(user: UserCreate):
    """
    Register a new user account and organization.

    HTTP Method: POST
    URL: /signup
    Auth Required: No (this is a public endpoint)

    Request Body (UserCreate):
        - email (str): The user's email address (must be unique across all users)
        - password (str): The user's chosen password (will be bcrypt-hashed)
        - full_name (str): The user's display name
        - org_name (str, optional): Organization name; defaults to "<full_name>'s Org"

    Request Flow:
        1. Check if a user with the given email already exists in the database.
           If so, return HTTP 400 "Email already registered".
        2. Create a new organization record with a generated UUID and "free" plan.
        3. Hash the user's password using bcrypt.
        4. Create a new user record linked to the organization, with role "owner".
        5. Update the organization to set this user as the owner.
        6. Generate a JWT token for the new user.
        7. Return the token and user profile in the response.

    Response (TokenResponse):
        - access_token (str): JWT token for authenticating future requests
        - user (UserResponse): The newly created user's profile data

    Error Responses:
        - 400: Email already registered
    """
    db = get_supabase()

    # Check if email exists
    existing = db.table("users").select("id").eq("email", user.email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash the password once (bcrypt; the raw password is never stored).
    hashed_password = bcrypt.hash(user.password)

    org_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    # Create the organization and user. The DB enforces a UNIQUE constraint on
    # users.email, so even if two concurrent signups slip past the check above,
    # the second insert fails — we translate that into a clean 400 rather than
    # letting it surface as a 500.
    try:
        db.table("organizations").insert({
            "id": org_id,
            "name": user.org_name or f"{user.full_name}'s Org",
            "plan": "free",
        }).execute()

        db_user = db.table("users").insert({
            "id": user_id,
            "email": user.email,
            "full_name": user.full_name,
            "password_hash": hashed_password,
            "org_id": org_id,
            "role": "owner",
        }).execute()
    except Exception as exc:  # translate a DB unique-violation into a 400
        msg = str(exc).lower()
        if "duplicate" in msg or "unique" in msg:
            raise HTTPException(status_code=400, detail="Email already registered") from exc
        raise

    # Update org owner - link the organization back to the user who created it
    db.table("organizations").update({"owner_id": user_id}).eq("id", org_id).execute()

    # Generate JWT token so the user is immediately logged in after signup
    token = create_token(user_id)
    user_data = db_user.data[0]

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_data["id"],
            email=user_data["email"],
            full_name=user_data["full_name"],
            org_id=user_data["org_id"],
            role=user_data["role"],
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """
    Authenticate an existing user with email and password.

    HTTP Method: POST
    URL: /login
    Auth Required: No (this is a public endpoint)

    Request Body (UserLogin):
        - email (str): The user's registered email address
        - password (str): The user's password (plain text, verified against stored hash)

    Request Flow:
        1. Look up the user by email in the database.
           If not found, return HTTP 401 "Invalid credentials".
        2. Verify the submitted password against the stored bcrypt hash.
           If it does not match, return HTTP 401 "Invalid credentials".
           (We use the same error message for both cases to avoid leaking
           whether an email is registered or not.)
        3. Generate a JWT token for the authenticated user.
        4. Return the token and user profile.

    Response (TokenResponse):
        - access_token (str): JWT token for authenticating future requests
        - user (UserResponse): The authenticated user's profile data

    Error Responses:
        - 401: Invalid credentials (wrong email or wrong password)
    """
    db = get_supabase()

    result = db.table("users").select("*").eq("email", credentials.email).execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_data = result.data[0]

    # Verify the password against the stored bcrypt hash. bcrypt.verify raises
    # ValueError when the stored hash is missing or malformed, so treat that as a
    # failed login (401) rather than letting it become a 500.
    stored_hash = user_data.get("password_hash") or ""
    try:
        password_ok = bcrypt.verify(credentials.password, stored_hash)
    except ValueError:
        password_ok = False
    if not password_ok:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(user_data["id"])
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_data["id"],
            email=user_data["email"],
            full_name=user_data["full_name"],
            org_id=user_data["org_id"],
            role=user_data.get("role", "owner"),
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Get the currently authenticated user's profile.

    HTTP Method: GET
    URL: /me
    Auth Required: Yes (Bearer token in Authorization header)

    How Authentication Works Here:
        - The `Depends(get_current_user)` dependency extracts the JWT from the
          request's Authorization header, decodes it, looks up the user in the
          database by the "sub" (user ID) claim, and returns the user as a dict.
        - If the token is missing, expired, or invalid, FastAPI automatically
          returns HTTP 401 before this function is even called.

    Request Flow:
        1. The get_current_user dependency validates the JWT and fetches the user.
        2. The user dict is passed directly into the UserResponse model.
        3. The response is returned with the user's profile fields.

    Response (UserResponse):
        - id (str): User's unique ID
        - email (str): User's email
        - full_name (str): User's display name
        - org_id (str): The organization this user belongs to
        - role (str): User's role within the organization (e.g., "owner", "agent")
    """
    return UserResponse(**current_user)
