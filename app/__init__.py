import os
import click
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
login_manager.login_view = "admin.login"


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    if not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY is missing. Set it in your .env file.")

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.routes.main import main_bp
    from app.routes.admin import admin_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    from app.models import Admin, Category, SiteSettings

    @app.context_processor
    def inject_globals():
        return {
            "site": SiteSettings.get(),
            "nav_categories": Category.query.filter_by(is_active=True)
                                      .order_by(Category.sort_order).all(),
            "PHONE": app.config["PHONE"],
            "WHATSAPP": app.config["WHATSAPP"],
        }

    @app.cli.command("init-db")
    def init_db():
        """Create tables, seed categories, sizes and site settings."""
        from app.models import seed_defaults
        db.create_all()
        seed_defaults()
        click.echo("Database initialised.")


    @app.cli.command("create-admin")
    @click.option("--username", prompt=True)
    @click.password_option(confirmation_prompt=True)
    def create_admin(username, password):
        """Create an admin account (password is typed, never stored in a file)."""
        if len(password) < 10:
            click.echo("Password must be at least 10 characters.")
            return
        if Admin.query.filter_by(username=username).first():
            click.echo("That admin already exists.")
            return
        a = Admin(username=username)
        a.set_password(password)
        db.session.add(a)
        db.session.commit()
        click.echo(f"Admin '{username}' created.")


    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template("404.html"), 404

    @app.errorhandler(413)
    def too_large(e):
        from flask import flash, redirect, request
        flash("Image is too large. Maximum size is 5 MB.", "danger")
        return redirect(request.referrer or "/admin/")

    return app