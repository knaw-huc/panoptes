import jwt
from datetime import timedelta, datetime

from motor.motor_asyncio import AsyncIOMotorClient
from pwdlib import PasswordHash

from app.config import get_settings
from app.models import User

password_hash = PasswordHash.recommended()
DUMMY_PASSWORD = password_hash.hash("dummy")

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_MINUTES = 7 * 24 * 60
ALGORITHM = "HS256"

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

async def get_user_with_password(username: str, password: str, db: AsyncIOMotorClient) -> User:
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