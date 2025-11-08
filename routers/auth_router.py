from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import User
from utils import auth as auth_utils

# --- Pydantic Schemas for Responses ---


class Token(BaseModel):
    access_token: str
    token_type: str


class Msg(BaseModel):
    message: str


# We use this to safely return user data *without* the password hash
class UserOut(BaseModel):
    user_id: int
    username: str
    role: str  # We can just return the role's string value
    last_login: datetime | None

    class Config:
        from_attributes = True


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

auth_router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),  # noqa: B008
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 1. Decode the token
    payload = auth_utils.decode_token(token)
    if payload is None:
        raise credentials_exception

    # 2. Get username from payload ("sub")
    username = payload.get("sub")
    if username is None:
        raise credentials_exception

    # 3. Find the user in the database
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception

    # 4. Return the complete User object (from SQLAlchemy)
    return user


# --- 1. Login Endpoint ---
@auth_router.post("/token", response_model=Token)
async def login_for_access_token(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
):
    # 1. Find the user by username
    user = db.query(User).filter(User.username == form_data.username).first()

    # 2. Check if user exists and verify password
    if not user or not auth_utils.verify_password(
        form_data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Create tokens
    # We add the user's role to the access token for role-based access
    access_token_data = {"sub": user.username, "role": user.role.value}
    access_token = auth_utils.create_access_token(data=access_token_data)

    # Refresh token only needs the subject (username)
    refresh_token_data = {"sub": user.username}
    refresh_token = auth_utils.create_refresh_token(data=refresh_token_data)

    # 4. Set the refresh token in an HttpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,  # Crucial: Client-side JS cannot access this cookie
        samesite="strict",  # Helps prevent CSRF
        secure=True,  # Set to True if in production (HTTPS)
        max_age=auth_utils.settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    # 5. Return the access token in the response body
    return {"access_token": access_token, "token_type": "bearer"}


# --- 2. Refresh Token Endpoint ---
@auth_router.post("/refresh", response_model=Token)
async def refresh_access_token(
    db: Annotated[Session, Depends(get_db)],
    refresh_token: Annotated[str | None, Cookie()] = None,  # Extract from cookie
):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token found.",
        )

    # 1. Decode the refresh token
    payload = auth_utils.decode_token(refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    # 2. Get username from payload and find user
    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with token not found.",
        )

    # 3. Issue a new access token (with fresh role data)
    new_access_token_data = {"sub": user.username, "role": user.role.value}
    new_access_token = auth_utils.create_access_token(data=new_access_token_data)

    return {"access_token": new_access_token, "token_type": "bearer"}


# --- 3. Logout Endpoint ---
@auth_router.post("/logout", response_model=Msg)
async def logout(response: Response):
    # The simplest way to "log out" stateless tokens
    # is to clear the cookie on the client.
    response.delete_cookie(key="refresh_token")
    return {"message": "Logged out successfully."}


@auth_router.get("/me", response_model=UserOut)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user
