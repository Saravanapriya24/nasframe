from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Admin, int(user_id))


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    image_filename = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    products = db.relationship("Product", backref="category", lazy=True)


class FrameSize(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(20), unique=True, nullable=False)  # "12 × 8"
    sort_order = db.Column(db.Integer, default=0)
    products = db.relationship("Product", backref="size", lazy=True)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(150), nullable=False)
    image_filename = db.Column(db.String(255), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    size_id = db.Column(db.Integer, db.ForeignKey("frame_size.id"), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
@property
def code(self):
        return f"NAS-{self.id:04d}"


class SiteSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(120), default="NAS Frame Works")
    tagline = db.Column(db.String(200), default="Beautiful Photos for Divine Memories")
    logo_filename = db.Column(db.String(255))
    banner_filename = db.Column(db.String(255))
    welcome_text = db.Column(db.Text, default=(
        "Discover beautiful devotional photo frames in elegant styles and sizes, "
        "created to bring divine memories into your home."))
    about_text = db.Column(db.Text, default=(
        "NAS Frame Works is dedicated to offering beautiful devotional photo frames "
        "that bring elegance and a spiritual touch to your surroundings."))
    phone = db.Column(db.String(30), default="+91 9751510089")
    whatsapp = db.Column(db.String(30), default="+91 8056560326")

    @staticmethod
    def get():
        s = SiteSettings.query.first()
        if not s:
            s = SiteSettings()
            db.session.add(s)
            db.session.commit()
        return s


def seed_defaults():
    cats = ["Glass Frames", "Mat Frames", "Lamination Frames",
            "3D Image Frames", "PVC Frames"]
    for i, name in enumerate(cats):
        if not Category.query.filter_by(name=name).first():
            slug = name.lower().replace(" ", "-")
            db.session.add(Category(name=name, slug=slug, sort_order=i))
    sizes = ["6 × 4", "9 × 6", "12 × 4", "12 × 8", "18 × 12",
             "20 × 7", "28 × 10", "2 × 1", "28 × 20", "3 × 2"]
    for i, label in enumerate(sizes):
        if not FrameSize.query.filter_by(label=label).first():
            db.session.add(FrameSize(label=label, sort_order=i))
    SiteSettings.get()
    db.session.commit()