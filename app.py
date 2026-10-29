import os
import secrets

from flask import Flask, current_app, redirect, render_template, request, session, url_for


def generate_code() -> str:
    return f"{secrets.randbelow(9000) + 1000:04d}"


def create_app(test_config: dict | None = None) -> Flask:
    application = Flask(__name__)
    application.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-key-change-me"),
        DEMO_USERNAME=os.environ.get("DEMO_USERNAME", "demo"),
        DEMO_PASSWORD=os.environ.get("DEMO_PASSWORD", "demo"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    if test_config is not None:
        application.config.update(test_config)

    @application.after_request
    def disable_cache(response):
        response.headers["Cache-Control"] = "no-store"
        return response

    @application.route("/", methods=["GET", "POST"])
    def login():
        template_context = {
            "demo_username": current_app.config["DEMO_USERNAME"],
            "demo_password": current_app.config["DEMO_PASSWORD"],
        }

        if request.method == "GET":
            session.clear()
            return render_template("login.html", error=None, **template_context)

        supplied_username = request.form.get("username", "")
        supplied_password = request.form.get("password", "")
        username_matches = secrets.compare_digest(
            supplied_username, str(current_app.config["DEMO_USERNAME"])
        )
        password_matches = secrets.compare_digest(
            supplied_password, str(current_app.config["DEMO_PASSWORD"])
        )

        session.clear()
        if not (username_matches and password_matches):
            return render_template(
                "login.html",
                error="Неверный логин или пароль",
                **template_context,
            ), 401

        session["can_view_code"] = True
        return redirect(url_for("code"))

    @application.get("/code")
    def code():
        if not session.pop("can_view_code", False):
            return redirect(url_for("login"))

        return render_template("code.html", code=generate_code())

    return application


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
