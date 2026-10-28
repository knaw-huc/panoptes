"""
Services and functions for dealing with authentication.
"""

from datetime import timedelta, datetime
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError

# from motor.motor_asyncio import AsyncIOMotorClient
from pwdlib import PasswordHash
from pymongo import AsyncMongoClient
from pymongo.synchronous.database import Database
from starlette import status

from app.config import get_settings
from app.dependencies import MainDbDep
from app.models import User

password_hash = PasswordHash.recommended()
DUMMY_PASSWORD = password_hash.hash("dummy")

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_MINUTES = 7 * 24 * 60
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token", refreshUrl="api/auth/refresh")

class InvalidCredentialsException(Exception):
    """
    Exception raised for invalid credentials
    """

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies password against hashed password
    :param plain_password:
    :param hashed_password:
    :return:
    """
    return password_hash.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Get password hash
    :param password:
    :return:
    """
    return password_hash.hash(password)


async def get_user_with_password(username: str, password: str, db: Database) -> User:
    """
    Get user by username and password
    :param username:
    :param password:
    :param db:
    :return:
    """
    results = await db.users.find({"username": username}).to_list()
    userdata = results[0] if len(results) > 0 else None
    if not userdata:
        verify_password(password, DUMMY_PASSWORD)
        raise InvalidCredentialsException
    user = User(**userdata)
    if not verify_password(password, user.password_hash):
        raise InvalidCredentialsException
    return user


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)],
                           db: MainDbDep) -> User:
    """
    Get the user based on the JWT token
    :param db:
    :param token:
    :return:
    """
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except InvalidTokenError as exc:
        raise credentials_exception from exc

    results = await db.users.find({"username": username}).to_list()
    userdata = results[0] if len(results) > 0 else None
    if not userdata:
        raise credentials_exception
    user = User(**userdata)
    return user

UserDep = Annotated[User, Depends(get_current_user)]


def is_admin(user: UserDep):
    """
    For now, only admins have accounts. So if someone is logged in that user is an admin
    :param user:
    :return:
    """
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return True


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Sign a JWT token
    :param data:
    :param expires_delta:
    :return:
    """
    settings = get_settings()
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=ALGORITHM)
    return encoded_jwt
