from pydantic import BaseModel


class UserCreate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    name: str | None = None
    email: str
    password: str
    date_of_birth: str | None = None


class UserLoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: str | None = None
