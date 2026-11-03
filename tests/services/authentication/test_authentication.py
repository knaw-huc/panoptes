"""
Tests for app.services.authentication.authentication.
"""

from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest

from app.models import User
from app.services.authentication.authentication import (
    ALGORITHM,
    InvalidCredentialsException,
    create_access_token,
    get_password_hash,
    get_user_with_password,
    verify_password,
)


class TestPasswordHashing:
    """Password hash verification."""

    def test_verify_password_succeeds_for_matching_password(self):
        """Accept a password that matches its stored hash."""
        hashed = get_password_hash("correct-horse")

        assert verify_password("correct-horse", hashed) is True

    def test_verify_password_fails_for_wrong_password(self):
        """Reject a password that does not match its stored hash."""
        hashed = get_password_hash("correct-horse")

        assert verify_password("wrong-password", hashed) is False


class TestCreateAccessToken:
    """Access token claims and expiration."""

    def test_token_contains_provided_claims(self, fake_settings):
        """Include the supplied subject and an expiration in the signed token."""
        token = create_access_token({"sub": "alice"})

        payload = jwt.decode(token, fake_settings.jwt_secret, algorithms=[ALGORITHM])

        assert payload["sub"] == "alice"
        assert "exp" in payload


def make_db(users):
    """Build a mock database whose user query returns the supplied records."""
    db = MagicMock()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=users)
    db.users.find.return_value = cursor
    return db


class TestGetUserWithPassword:
    """User lookup and credential validation."""

    @pytest.mark.asyncio
    async def test_returns_user_for_valid_credentials(self):
        """Return the user when the username and password are valid."""
        hashed = get_password_hash("secret")
        db = make_db([{"_id": "1", "username": "alice", "password_hash": hashed}])

        user = await get_user_with_password("alice", "secret", db)

        assert isinstance(user, User)
        assert user.username == "alice"

    @pytest.mark.asyncio
    async def test_raises_for_unknown_user(self):
        """Reject credentials for a username absent from the database."""
        db = make_db([])

        with pytest.raises(InvalidCredentialsException):
            await get_user_with_password("unknown", "secret", db)

    @pytest.mark.asyncio
    async def test_raises_for_wrong_password(self):
        """Reject an incorrect password for an existing user."""
        hashed = get_password_hash("secret")
        db = make_db([{"_id": "1", "username": "alice", "password_hash": hashed}])

        with pytest.raises(InvalidCredentialsException):
            await get_user_with_password("alice", "wrong-password", db)
