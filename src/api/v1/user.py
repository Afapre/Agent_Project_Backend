from fastapi import APIRouter, HTTPException

from src.api.v1.chat_common import get_user_or_404
from src.data_logic.postgres import create_user as db_create_user
from src.data_logic.postgres import delete_user as db_delete_user
from src.data_logic.postgres import login_user as db_login_user
from src.schema.user_models import UserCreate, UserLoginRequest, UserResponse

router = APIRouter()


@router.post("/users", response_model=UserResponse)
async def create_user(payload: UserCreate):
    try:
        created = db_create_user(
            first_name=payload.first_name or "",
            last_name=payload.last_name or "",
            email=payload.email,
            password=payload.password,
            date_of_birth=payload.date_of_birth,
        )
        return UserResponse(**created)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/users/login", response_model=UserResponse)
async def login_user(payload: UserLoginRequest):
    try:
        user = db_login_user(email=payload.email, password=payload.password)
        return UserResponse(**user)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    user = get_user_or_404(user_id)
    return UserResponse(**user)


@router.delete("/users/{user_id}")
async def delete_user(user_id: str):
    db_delete_user(user_id)
    return {"message": "User deleted", "user_id": user_id}
