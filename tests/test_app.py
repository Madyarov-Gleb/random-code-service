import pytest
from flask import Flask

import app as app_module


@pytest.fixture()
def application():
    return app_module.create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "DEMO_USERNAME": "demo",
            "DEMO_PASSWORD": "demo",
        }
    )


@pytest.fixture()
def client(application):
    return application.test_client()


def login(client, username="demo", password="demo"):
    return client.post(
        "/",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


def test_login_page_loads(client):
    response = client.get("/")

    assert response.status_code == 200


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("", ""),
        ("demo", "wrong-password"),
        ("unknown", "demo"),
    ],
)
def test_invalid_credentials_do_not_authorize(client, username, password):
    response = login(client, username, password)

    assert response.status_code == 401
    assert client.get("/code").status_code == 302


def test_valid_credentials_redirect_to_code(client):
    response = login(client)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/code")


def test_direct_code_request_redirects_to_login(client):
    response = client.get("/code")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_successful_login_allows_exactly_one_code_view(client):
    login(client)

    first_view = client.get("/code")
    refreshed_view = client.get("/code")

    assert first_view.status_code == 200
    assert refreshed_view.status_code == 302
    assert refreshed_view.headers["Location"].endswith("/")


@pytest.mark.parametrize(
    ("random_value", "expected_code"),
    [
        (0, b"1000"),
        (8999, b"9999"),
    ],
)
def test_generated_code_includes_four_digit_boundaries(
    client, monkeypatch, random_value, expected_code
):
    monkeypatch.setattr(app_module.secrets, "randbelow", lambda _: random_value)
    login(client)

    response = client.get("/code")

    assert response.status_code == 200
    assert expected_code in response.data


@pytest.mark.parametrize("path", ["/", "/code"])
def test_pages_are_not_cached(client, path):
    if path == "/code":
        login(client)

    response = client.get(path)

    assert response.headers["Cache-Control"] == "no-store"


def test_login_form_is_accessible_and_shows_demo_credentials(client):
    response = client.get("/")

    assert b'<label for="username">' in response.data
    assert b'id="username"' in response.data
    assert b'<label for="password">' in response.data
    assert b'id="password"' in response.data
    assert "Логин: demo · Пароль: demo" in response.get_data(as_text=True)
    assert b'href="/static/style.css"' in response.data


def test_rejected_credentials_show_accessible_error(client):
    response = login(client, password="wrong-password")

    assert response.status_code == 401
    assert b'role="alert"' in response.data
    assert "Неверный логин или пароль" in response.get_data(as_text=True)


def test_result_page_marks_the_server_generated_code(client, monkeypatch):
    monkeypatch.setattr(app_module.secrets, "randbelow", lambda _: 0)
    login(client)

    response = client.get("/code")

    assert b'data-testid="generated-code"' in response.data
    assert b"1000" in response.data


def test_module_exposes_application_for_production_server():
    assert isinstance(app_module.app, Flask)


def test_environment_configures_demo_credentials(monkeypatch):
    monkeypatch.setenv("DEMO_USERNAME", "reviewer")
    monkeypatch.setenv("DEMO_PASSWORD", "7391")
    configured_app = app_module.create_app()
    configured_client = configured_app.test_client()

    response = configured_client.post(
        "/",
        data={"username": "reviewer", "password": "7391"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/code")


def test_default_demo_credentials_match_visible_hint(monkeypatch):
    monkeypatch.delenv("DEMO_USERNAME", raising=False)
    monkeypatch.delenv("DEMO_PASSWORD", raising=False)
    default_app = app_module.create_app(
        {"TESTING": True, "SECRET_KEY": "test-secret-key"}
    )
    default_client = default_app.test_client()

    response = default_client.post(
        "/",
        data={"username": "demo", "password": "demo"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/code")
