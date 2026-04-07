from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class Admin(UserMixin, db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Photo(db.Model):
    __tablename__ = 'photos'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(256), nullable=False)
    caption = db.Column(db.String(256), default='')
    category = db.Column(db.String(64), default='general')  # general, event, achievement
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def url(self):
        return f'/static/uploads/gallery/{self.filename}'


class Story(db.Model):
    __tablename__ = 'stories'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    slug = db.Column(db.String(256), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(256), default='')
    category = db.Column(db.String(64), default='news')  # news, achievement, event
    is_featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def image_url(self):
        if self.image_filename:
            return f'/static/uploads/stories/{self.image_filename}'
        return '/static/images/default-story.jpg'


class Program(db.Model):
    __tablename__ = 'programs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, default='')
    age_group = db.Column(db.String(64), default='')
    fee = db.Column(db.String(64), default='')
    duration = db.Column(db.String(64), default='')
    batch_time = db.Column(db.String(128), default='4:00 PM – 7:00 PM')
    is_active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)


class Inquiry(db.Model):
    __tablename__ = 'inquiries'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), default='')
    phone = db.Column(db.String(32), default='')
    message = db.Column(db.Text, default='')
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
