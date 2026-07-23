from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from config import ALGORITHM, SECRET_KEY
from database import get_connection
from main import app


PASSWORD = "Integration-Test-Password-2026!"


class AuthIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.email = f"auth-test-{uuid.uuid4().hex}@gmail.com"
        self.user_id: str | None = None
        self.access_token_ids: set[str] = set()

    def tearDown(self) -> None:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                if self.user_id:
                    cursor.execute("DELETE FROM auth_sessions WHERE user_id = %s", (self.user_id,))
                    cursor.execute("DELETE FROM users WHERE id = %s", (self.user_id,))
                if self.access_token_ids:
                    cursor.execute(
                        "DELETE FROM revoked_tokens WHERE jti = ANY(%s)",
                        (list(self.access_token_ids),),
                    )

    def register_user(self) -> None:
        response = self.client.post(
            "/api/auth/register",
            json={"email": self.email, "password": PASSWORD, "accepted_terms": True},
        )
        self.assertEqual(response.status_code, 201)
        self.user_id = response.json()["id"]

    def login_user(self) -> dict[str, str]:
        response = self.client.post("/api/auth/login", json={"email": self.email, "password": PASSWORD})
        self.assertEqual(response.status_code, 200)
        tokens = response.json()
        self.access_token_ids.add(
            jwt.decode(tokens["access_token"], SECRET_KEY, algorithms=[ALGORITHM])["jti"]
        )
        return tokens

    def test_duplicate_registration_is_rejected(self) -> None:
        self.register_user()

        response = self.client.post(
            "/api/auth/register",
            json={"email": self.email, "password": PASSWORD, "accepted_terms": True},
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "该邮箱已注册，请直接登录")

    def test_login_rejects_wrong_password(self) -> None:
        self.register_user()

        response = self.client.post(
            "/api/auth/login",
            json={"email": self.email, "password": "wrong-password"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "邮箱或密码错误")

    def test_refresh_rotates_token_and_rejects_previous_token(self) -> None:
        self.register_user()
        initial_tokens = self.login_user()

        refreshed_response = self.client.post(
            "/api/auth/refresh",
            json={"refresh_token": initial_tokens["refresh_token"]},
        )
        self.assertEqual(refreshed_response.status_code, 200)
        refreshed_tokens = refreshed_response.json()
        self.assertNotEqual(initial_tokens["refresh_token"], refreshed_tokens["refresh_token"])
        self.access_token_ids.add(
            jwt.decode(refreshed_tokens["access_token"], SECRET_KEY, algorithms=[ALGORITHM])["jti"]
        )

        replay_response = self.client.post(
            "/api/auth/refresh",
            json={"refresh_token": initial_tokens["refresh_token"]},
        )

        self.assertEqual(replay_response.status_code, 401)
        self.assertEqual(replay_response.json()["detail"], "Refresh token 无效或已过期")

    def test_logout_revokes_access_and_refresh_tokens(self) -> None:
        self.register_user()
        tokens = self.login_user()
        authorization = {"Authorization": f"Bearer {tokens['access_token']}"}

        logout_response = self.client.post(
            "/api/auth/logout",
            headers=authorization,
            json={"refresh_token": tokens["refresh_token"]},
        )
        self.assertEqual(logout_response.status_code, 204)

        profile_response = self.client.get("/api/auth/me", headers=authorization)
        refresh_response = self.client.post(
            "/api/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )

        self.assertEqual(profile_response.status_code, 401)
        self.assertEqual(refresh_response.status_code, 401)

    def test_expired_session_rejects_access_token(self) -> None:
        self.register_user()
        tokens = self.login_user()
        payload = jwt.decode(tokens["access_token"], SECRET_KEY, algorithms=[ALGORITHM])

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE auth_sessions SET expires_at = %s WHERE id = %s",
                    (datetime.now(timezone.utc) - timedelta(seconds=1), payload["sid"]),
                )

        response = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "登录状态无效或已过期")


if __name__ == "__main__":
    unittest.main()
