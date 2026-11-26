from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import Admin, Category, FrameSize, Product, SiteSettings
from app.utils import (save_image, delete_image_if_unused, normalize_size,
                       UploadError)

admin_bp = Blueprint("admin", __name__)


# ---------- auth ----------
@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))
    if request.method == "POST":
        user = Admin.query.filter_by(
            username=request.form.get("username", "").strip()).first()
        if user and user.check_password(request.form.get("password", "")):
            login_user(user)
            nxt = request.args.get("next", "")
            if nxt.startswith("/") and not nxt.startswith("//"):
                return redirect(nxt)
            return redirect(url_for("admin.dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("admin/login.html")


@admin_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("admin.login"))


# ---------- dashboard ----------
@admin_bp.route("/")
@login_required
def dashboard():
    return render_template(
        "admin/dashboard.html",
        total_products=Product.query.count(),
        total_categories=Category.query.count(),
        total_sizes=FrameSize.query.count(),
        recent=Product.query.order_by(Product.created_at.desc()).limit(8).all())


# ---------- products ----------
@admin_bp.route("/products")
@login_required
def products():
    items = Product.query.order_by(Product.created_at.desc()).all()
    return render_template("admin/products.html", products=items)


def _form_options():
    return (Category.query.order_by(Category.sort_order).all(),
            FrameSize.query.order_by(FrameSize.sort_order, FrameSize.id).all())


def _read_product_form():
    data = {
        "name": request.form.get("product_name", "").strip(),
        "category_id": request.form.get("category_id", type=int),
        "size_id": request.form.get("size_id", type=int),
        "description": request.form.get("description", "").strip(),
        "is_active": request.form.get("is_active") == "on",
    }
    errors = []
    if len(data["name"]) > 150:
        errors.append("Design name is too long (max 150 characters).")
    if not db.session.get(Category, data["category_id"] or 0):
        errors.append("Please choose a valid category.")
    if not db.session.get(FrameSize, data["size_id"] or 0):
        errors.append("Please choose a valid size.")
    return data, errors


@admin_bp.route("/products/add", methods=["GET", "POST"])
@login_required
def add_product():
    categories, sizes = _form_options()
    if request.method == "POST":
        data, errors = _read_product_form()
        filename = None
        if not errors:
            try:
                filename = save_image(request.files.get("image"))
            except UploadError as e:
                errors.append(str(e))
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("admin/product_form.html", product=None, data=data,
                                   categories=categories, sizes=sizes)
        p = Product(product_name=data["name"], image_filename=filename,
                    category_id=data["category_id"], size_id=data["size_id"],
                    description=data["description"], is_active=data["is_active"])
        db.session.add(p)
        db.session.commit()
        flash("Product added. It is now live on the website.", "success")
        return redirect(url_for("admin.products"))
    return render_template("admin/product_form.html", product=None,
                           data={"is_active": True}, categories=categories, sizes=sizes)


@admin_bp.route("/products/<int:pid>/edit", methods=["GET", "POST"])
@login_required
def edit_product(pid):
    p = db.get_or_404(Product, pid)
    categories, sizes = _form_options()
    if request.method == "POST":
        data, errors = _read_product_form()
        new_file = None
        upload = request.files.get("image")
        if not errors and upload and upload.filename:
            try:
                new_file = save_image(upload)
            except UploadError as e:
                errors.append(str(e))
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("admin/product_form.html", product=p, data=data,
                                   categories=categories, sizes=sizes)
        old_file = p.image_filename
        p.product_name = data["name"]
        p.category_id = data["category_id"]
        p.size_id = data["size_id"]
        p.description = data["description"]
        p.is_active = data["is_active"]
        if new_file:
            p.image_filename = new_file
        db.session.commit()
        if new_file:
            delete_image_if_unused(old_file)
        flash("Product updated.", "success")
        return redirect(url_for("admin.products"))
    data = {"name": p.product_name, "category_id": p.category_id, "size_id": p.size_id,
            "description": p.description or "", "is_active": p.is_active}
    return render_template("admin/product_form.html", product=p, data=data,
                           categories=categories, sizes=sizes)


@admin_bp.route("/products/<int:pid>/delete", methods=["POST"])
@login_required
def delete_product(pid):
    p = db.get_or_404(Product, pid)
    filename = p.image_filename
    db.session.delete(p)
    db.session.commit()
    delete_image_if_unused(filename)
    flash("Product deleted.", "success")
    return redirect(url_for("admin.products"))


# ---------- categories ----------
@admin_bp.route("/categories")
@login_required
def categories():
    items = Category.query.order_by(Category.sort_order).all()
    return render_template("admin/categories.html", categories=items)


@admin_bp.route("/categories/<int:cid>/edit", methods=["POST"])
@login_required
def edit_category(cid):
    c = db.get_or_404(Category, cid)
    name = request.form.get("name", "").strip()
    if not name:
        flash("Category name cannot be empty.", "danger")
        return redirect(url_for("admin.categories"))
    clash = Category.query.filter(Category.name == name, Category.id != c.id).first()
    if clash:
        flash("Another category already has that name.", "danger")
        return redirect(url_for("admin.categories"))
    new_file = None
    upload = request.files.get("image")
    if upload and upload.filename:
        try:
            new_file = save_image(upload)
        except UploadError as e:
            flash(str(e), "danger")
            return redirect(url_for("admin.categories"))
    old_file = c.image_filename
    if c.name != name:
        c.name = name
        c.slug = name.lower().replace(" ", "-")
  
    c.is_active = request.form.get("is_active") == "on"
    if new_file:
        c.image_filename = new_file
    db.session.commit()
    if new_file:
        delete_image_if_unused(old_file)
    flash("Category updated.", "success")
    return redirect(url_for("admin.categories"))


# ---------- sizes ----------
@admin_bp.route("/sizes")
@login_required
def sizes():
    items = FrameSize.query.order_by(FrameSize.sort_order, FrameSize.id).all()
    return render_template("admin/sizes.html", sizes=items)


@admin_bp.route("/sizes/add", methods=["POST"])
@login_required
def add_size():
    label = normalize_size(request.form.get("label"))
    if not label:
        flash("Enter a size like 12 x 8 (numbers only).", "danger")
    elif FrameSize.query.filter_by(label=label).first():
        flash(f"{label} already exists.", "danger")
    else:
        last = db.session.query(db.func.max(FrameSize.sort_order)).scalar() or 0
        db.session.add(FrameSize(label=label, sort_order=last + 1))
        db.session.commit()
        flash(f"Size {label} added.", "success")
    return redirect(url_for("admin.sizes"))


@admin_bp.route("/sizes/<int:sid>/edit", methods=["POST"])
@login_required
def edit_size(sid):
    s = db.get_or_404(FrameSize, sid)
    label = normalize_size(request.form.get("label"))
    if not label:
        flash("Enter a size like 12 x 8 (numbers only).", "danger")
    elif FrameSize.query.filter(FrameSize.label == label, FrameSize.id != s.id).first():
        flash(f"{label} already exists.", "danger")
    else:
        s.label = label
        db.session.commit()
        flash("Size updated.", "success")
    return redirect(url_for("admin.sizes"))


@admin_bp.route("/sizes/<int:sid>/delete", methods=["POST"])
@login_required
def delete_size(sid):
    s = db.get_or_404(FrameSize, sid)
    if s.products:
        flash(f"{s.label} is used by {len(s.products)} product(s). "
              "Move or delete those products first.", "danger")
    else:
        db.session.delete(s)
        db.session.commit()
        flash("Size removed.", "success")
    return redirect(url_for("admin.sizes"))


# ---------- site settings ----------
@admin_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    s = SiteSettings.get()
    if request.method == "POST":
        for field in ("business_name", "tagline", "welcome_text",
                      "about_text", "phone", "whatsapp"):
            setattr(s, field, request.form.get(field, "").strip())
        old_files = []
        for field, key in (("logo_filename", "logo"), ("banner_filename", "banner")):
            upload = request.files.get(key)
            if upload and upload.filename:
                try:
                    new_file = save_image(upload)
                except UploadError as e:
                    flash(f"{key.title()}: {e}", "danger")
                    db.session.rollback()
                    return redirect(url_for("admin.settings"))
                old_files.append(getattr(s, field))
                setattr(s, field, new_file)
        db.session.commit()
        for f in old_files:
            delete_image_if_unused(f)
        flash("Website content saved.", "success")
        return redirect(url_for("admin.settings"))
    return render_template("admin/settings.html", s=s)