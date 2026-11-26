import re
from urllib.parse import quote
from flask import Blueprint, render_template, send_from_directory, current_app, abort
from app import db
from app.models import Category, FrameSize, Product, SiteSettings

main_bp = Blueprint("main", __name__)


@main_bp.app_template_global()
def wa_link(message="Hello, I would like to enquire about your frames."):
    number = re.sub(r"\D", "", SiteSettings.get().whatsapp or "")
    return f"https://wa.me/{number}?text={quote(message)}"


@main_bp.app_template_global()
def tel_link():
    number = re.sub(r"[^\d+]", "", SiteSettings.get().phone or "")
    return f"tel:{number}"


def active_products():
    return (Product.query.join(Category).join(FrameSize)
            .filter(Product.is_active.is_(True), Category.is_active.is_(True)))


@main_bp.route("/")
def index():
    categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order).all()
    return render_template("index.html", categories=categories)


@main_bp.route("/products")
def products():
    categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order).all()
    sizes = FrameSize.query.order_by(FrameSize.sort_order, FrameSize.id).all()
    return render_template("products.html", categories=categories, sizes=sizes)


@main_bp.route("/category/<slug>")
def category(slug):
    cat = Category.query.filter_by(slug=slug, is_active=True).first_or_404()
    rows = (active_products()
            .filter(Product.category_id == cat.id)
            .order_by(FrameSize.sort_order, Product.created_at.desc()).all())
    groups = {}
    for p in rows:
        groups.setdefault(p.size, []).append(p)
    return render_template("category.html", cat=cat, groups=groups)


@main_bp.route("/size/<int:size_id>")
def size_gallery(size_id):
    size = db.get_or_404(FrameSize, size_id)
    rows = (active_products()
            .filter(Product.size_id == size.id)
            .order_by(Category.sort_order, Product.created_at.desc()).all())
    groups = {}
    for p in rows:
        groups.setdefault(p.category, []).append(p)  # empty categories never appear
    return render_template("size_gallery.html", size=size, groups=groups)


@main_bp.route("/about")
def about():
    return render_template("about.html")




@main_bp.route("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)