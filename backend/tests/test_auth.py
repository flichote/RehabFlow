"""认证测试：注册（4 角色）/ 登录 / me / refresh / 401 未登录。

依据：api.md §1 + m1-acceptance AC-BE-02/03 + AC-QA-01（认证分组）。
"""
from __future__ import annotations

from tests.conftest import auth_headers, register_and_login


# ── 注册 ──────────────────────────────────────────────────────────


def test_register_all_roles(client):
    for role in ("patient", "therapist", "doctor", "admin"):
        tok, _, user_id = register_and_login(client, role)
        assert tok
        assert isinstance(user_id, int)


def test_register_duplicate_username_409(client):
    tok, _, _ = register_and_login(client, "admin", username="dup_user")
    assert tok
    # 同名再次注册 → 409
    r = client.post(
        "/api/v1/auth/register",
        json={"username": "dup_user", "password": "secret123", "display_name": "dup", "role": "patient"},
    )
    assert r.status_code == 409


def test_register_invalid_role_422(client):
    r = client.post(
        "/api/v1/auth/register",
        json={"username": "bad_role", "password": "secret123", "display_name": "bad", "role": "superman"},
    )
    assert r.status_code == 422


# ── 登录 / me ─────────────────────────────────────────────────────


def test_login_and_me_returns_role(client):
    tok, _, _ = register_and_login(client, "doctor")
    r = client.get("/api/v1/auth/me", headers=auth_headers(tok))
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "doctor"
    assert body["username"].startswith("doctor_")


def test_login_wrong_password_401(client):
    tok, _, _ = register_and_login(client, "patient", username="pwd_check")
    assert tok
    r = client.post("/api/v1/auth/login", json={"username": "pwd_check", "password": "wrong-pass"})
    assert r.status_code == 401


def test_me_without_token_401(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


# ── refresh ───────────────────────────────────────────────────────


def test_refresh_token_flow(client):
    _, refresh, _ = register_and_login(client, "patient")
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["refresh_token"]


def test_refresh_with_access_token_401(client):
    tok, _, _ = register_and_login(client, "patient")
    # 用 access token 冒充 refresh → 401
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": tok})
    assert r.status_code == 401
