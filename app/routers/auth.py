import uuid

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from starlette import status

from app.dependencies import MainDbDep, admin_domain
from app.models import RefreshToken, User
from app.services.authentication.authentication import get_user_with_password, InvalidCredentialsException, \
    ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_MINUTES, create_access_token, get_password_hash

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
    dependencies=[Depends(admin_domain)]
)

class Token(BaseModel):
    """
    Response for JWT token
    """
    access_token: str
    refresh_token: str
    token_type: str

@router.post("/login")
async def login(db: MainDbDep, form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Log the user in
    :return:
    """
    try:
        user = await get_user_with_password(form_data.username, form_data.password, db)
    except InvalidCredentialsException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect username or password") from e

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)

    refresh_token_obj = RefreshToken(username=user.username, uuid=str(uuid.uuid4()))

    db['refresh_token'].insert_one(refresh_token_obj.model_dump())

    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    refresh_token = create_access_token(data={"sub": user.username, "uuid": refresh_token_obj.uuid}, expires_delta=refresh_token_expires)
    return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")


@router.post("/init-user")
async def init_user(db: MainDbDep, form_data: OAuth2PasswordRequestForm = Depends()):
    """
    If there are no users yet, this creates an admin user
    :param db:
    :param form_data:
    :return:
    """
    n_users = await db.users.count_documents({})
    if n_users > 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already initialized")

    user = User(username=form_data.username, password_hash=get_password_hash(form_data.password))
    db['users'].insert_one(user.model_dump())
    return {
        "username": user.username,
        "status": "initialized",
        "n_users": n_users
    }