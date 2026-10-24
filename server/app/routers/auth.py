"""Authentication endpoints: register, login, current user."""
from fastapi import APIRouter, Depends, HTTPException, status

from ..database import db, row_to_dict
from ..deps import get_current_user
from ..schemas import LoginRequest, RegisterRequest, TokenOut, UserOut
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest):
    with db() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", (body.email,)
        ).fetchone()
        if existing:
            raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?,?,?)",
            (body.name, body.email, hash_password(body.password)),
        )
        user = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    user_dict = row_to_dict(user)
    return {"access_token": create_access_token(user_dict["id"]), "user": user_dict}


@router.post("/login", response_model=TokenOut)
def login(body: LoginRequest):
    with db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?", (body.email.strip().lower(),)
        ).fetchone()
    if user is None or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid email or password")
    user_dict = row_to_dict(user)
    return {"access_token": create_access_token(user_dict["id"]), "user": user_dict}


@router.get("/me", response_model=UserOut)
def me(user: dict = Depends(get_current_user)):
    return user
