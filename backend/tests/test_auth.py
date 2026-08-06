"""认证测试：注册（4 角色）/ 登录 / me / refresh / 401 未登录。

依据：api.md §1 + m1-acceptance AC-BE-02/03 + AC-QA-01（认证分组）。
"""
from __future__ import annotations

from tests.conftest import _test_phone, auth_headers, register_and_login


# ── 注册 ──────────────────────────────────────────────────────────


def test_register_all_roles(client):
    for role in ("patient", "therapist", "doctor", "admin"):
        tok, _, user_id = register_and_login(client, role)
        assert tok
        assert isinstance(user_id, int)


def test_register_duplicate_username_409(client):
    tok, _, _ = register_and_login(client, "admin", username="dup_user")
    assert tok
    # 同名再次注册 → 409（需带 phone，否则先命中 422 phone missing）
    r = client.post(
        "/api/v1/auth/register",
        json={"username": "dup_user", "password": "secret123", "display_name": "dup", "role": "patient", "phone": "13800000001"},
    )
    assert r.status_code == 409


def test_register_invalid_role_422(client):
    # 缺 phone 也会 422——此测试验证 role 非法，phone 给合法值以聚焦 role
    r = client.post(
        "/api/v1/auth/register",
        json={"username": "bad_role", "password": "secret123", "display_name": "bad", "role": "superman", "phone": "13800000002"},
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


# ── logout ────────────────────────────────────────────────────────


def test_logout_revokes_refresh(client):
    """logout 后 refresh token 失效（401），幂等可重复调用。"""
    _, refresh, _ = register_and_login(client, "patient")

    # logout 前 refresh 可用
    r0 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r0.status_code == 200

    # logout → 200
    r1 = client.post("/api/v1/auth/logout", json={"refresh_token": refresh})
    assert r1.status_code == 200
    assert r1.json()["message"] == "Logged out"

    # 已撤销的 refresh 再 refresh → 401
    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r2.status_code == 401

    # 幂等：重复 logout 仍 200
    r3 = client.post("/api/v1/auth/logout", json={"refresh_token": refresh})
    assert r3.status_code == 200


def test_logout_invalid_token_idempotent(client):
    """非法/伪造 token logout 也返回 200（幂等，不泄露信息）。"""
    r = client.post("/api/v1/auth/logout", json={"refresh_token": "not-a-real-token"})
    assert r.status_code == 200
    assert r.json()["message"] == "Logged out"


# ── 忘记密码（手机号 + 验证码） ──────────────────────────────────


def test_password_reset_flow(client):
    """忘记密码全链路：发验证码 → 验证码重置 → 旧密码失效新密码可登录。"""
    _, _, _ = register_and_login(client, "patient", username="reset_flow")
    # 拿到该用户的手机号（helper 生成的 phone 与 username 同种子）
    phone = _test_phone("reset_flow")

    # ① 请求验证码
    r = client.post("/api/v1/auth/password-reset/request", json={"phone": phone})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["dev_code"] and len(body["dev_code"]) == 6

    # ② 错误验证码 → 400
    r = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"phone": phone, "code": "000000", "new_password": "newpass123"},
    )
    assert r.status_code == 400

    # ③ 正确验证码 → 200
    r = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"phone": phone, "code": body["dev_code"], "new_password": "newpass123"},
    )
    assert r.status_code == 200, r.text

    # ④ 旧密码登录失败、新密码登录成功
    r = client.post("/api/v1/auth/login", json={"username": "reset_flow", "password": "secret123"})
    assert r.status_code == 401
    r = client.post("/api/v1/auth/login", json={"username": "reset_flow", "password": "newpass123"})
    assert r.status_code == 200


def test_password_reset_unregistered_phone(client):
    """未注册手机号请求验证码也返回 200（防枚举），但 confirm 会 400。"""
    r = client.post("/api/v1/auth/password-reset/request", json={"phone": "13999999999"})
    assert r.status_code == 200
    body = r.json()
    r = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"phone": "13999999999", "code": body["dev_code"], "new_password": "newpass123"},
    )
    assert r.status_code == 400
    assert "未注册" in r.json()["detail"]


def test_password_reset_invalid_phone_422(client):
    """手机号格式非法 → 422。"""
    r = client.post("/api/v1/auth/password-reset/request", json={"phone": "123"})
    assert r.status_code == 422


# ── 登录后修改密码 ───────────────────────────────────────────────


def test_change_password_flow(client):
    """修改密码：原密码校验 → 新密码生效 → 旧 refresh token 被撤销。"""
    tok, refresh, _ = register_and_login(client, "therapist", username="chg_pwd")

    # 原密码错误 → 400
    r = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "wrong", "new_password": "newpass456"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 400
    assert "原密码不正确" in r.json()["detail"]

    # 原密码正确 → 200
    r = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "secret123", "new_password": "newpass456"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200

    # 新密码登录成功
    r = client.post("/api/v1/auth/login", json={"username": "chg_pwd", "password": "newpass456"})
    assert r.status_code == 200

    # 旧 refresh token 已被撤销 → 401
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 401


def test_change_password_requires_auth(client):
    """未登录调用修改密码 → 401。"""
    r = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "x", "new_password": "newpass456"},
    )
    assert r.status_code == 401
