import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from slugify import slugify
from PIL import Image
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from models import db, Admin, Photo, Story, Program, Inquiry

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'bala-skating-secret-change-in-prod')

# Database: use PostgreSQL (DATABASE_URL) in production, SQLite locally
_db_url = os.environ.get('DATABASE_URL', '')
if _db_url.startswith('postgres://'):          # Railway uses the old prefix
    _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = _db_url or f"sqlite:///{os.path.join(BASE_DIR, 'bala_skating.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_GALLERY'] = os.path.join(BASE_DIR, 'static', 'uploads', 'gallery')
app.config['UPLOAD_STORIES'] = os.path.join(BASE_DIR, 'static', 'uploads', 'stories')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'admin_login'
login_manager.login_message = 'Please log in to access the admin panel.'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(file, folder, max_size=(1200, 900)):
    """Save uploaded image, resize if needed, return unique filename."""
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(folder, filename)
    img = Image.open(file)
    img = img.convert('RGB')
    img.thumbnail(max_size, Image.LANCZOS)
    img.save(filepath, quality=85, optimize=True)
    return filename


def unique_slug(title, model):
    base = slugify(title)
    slug = base
    counter = 1
    while model.query.filter_by(slug=slug).first():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


# ---------------------------------------------------------------------------
# Context processor – inject site-wide data into every template
# ---------------------------------------------------------------------------

@app.context_processor
def inject_site():
    return dict(
        site_name='Bala Skating Academy',
        site_phone='+91 91592 17517',
        site_address='Satellite City, Bypass Road, Kappalur, Tamil Nadu 625008',
        site_timings='Monday – Sunday: 5:30 PM – 7:00 PM',
        site_whatsapp='919159217517',
        now=datetime.utcnow(),
        unread_count=Inquiry.query.filter_by(is_read=False).count() if app.config.get('SQLALCHEMY_DATABASE_URI') else 0
    )


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    featured_stories = Story.query.filter_by(is_featured=True).order_by(Story.created_at.desc()).limit(3).all()
    recent_photos = Photo.query.order_by(Photo.uploaded_at.desc()).limit(8).all()
    programs = Program.query.filter_by(is_active=True).order_by(Program.display_order).all()
    return render_template('index.html',
                           featured_stories=featured_stories,
                           recent_photos=recent_photos,
                           programs=programs)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/programs')
def programs():
    all_programs = Program.query.filter_by(is_active=True).order_by(Program.display_order).all()
    return render_template('programs.html', programs=all_programs)


@app.route('/gallery')
def gallery():
    category = request.args.get('category', 'all')
    if category == 'all':
        photos = Photo.query.order_by(Photo.uploaded_at.desc()).all()
    else:
        photos = Photo.query.filter_by(category=category).order_by(Photo.uploaded_at.desc()).all()
    categories = db.session.query(Photo.category).distinct().all()
    categories = [c[0] for c in categories]
    return render_template('gallery.html', photos=photos, categories=categories, active_category=category)


@app.route('/stories')
def stories():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', 'all')
    query = Story.query
    if category != 'all':
        query = query.filter_by(category=category)
    pagination = query.order_by(Story.created_at.desc()).paginate(page=page, per_page=6)
    return render_template('stories.html', pagination=pagination, active_category=category)


@app.route('/stories/<slug>')
def story_detail(slug):
    story = Story.query.filter_by(slug=slug).first_or_404()
    related = Story.query.filter(Story.id != story.id).order_by(Story.created_at.desc()).limit(3).all()
    return render_template('story_detail.html', story=story, related=related)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        message = request.form.get('message', '').strip()
        if not name or not message:
            flash('Name and message are required.', 'danger')
        else:
            inquiry = Inquiry(name=name, email=email, phone=phone, message=message)
            db.session.add(inquiry)
            db.session.commit()
            flash('Thank you! We will get back to you soon.', 'success')
            return redirect(url_for('contact'))
    return render_template('contact.html')


# ---------------------------------------------------------------------------
# Admin – auth
# ---------------------------------------------------------------------------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            login_user(admin)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin_dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('admin/login.html')


@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('admin_login'))


# ---------------------------------------------------------------------------
# Admin – dashboard
# ---------------------------------------------------------------------------

@app.route('/admin')
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    stats = {
        'photos': Photo.query.count(),
        'stories': Story.query.count(),
        'programs': Program.query.filter_by(is_active=True).count(),
        'inquiries': Inquiry.query.count(),
        'unread': Inquiry.query.filter_by(is_read=False).count(),
    }
    recent_inquiries = Inquiry.query.order_by(Inquiry.created_at.desc()).limit(5).all()
    return render_template('admin/dashboard.html', stats=stats, recent_inquiries=recent_inquiries)


# ---------------------------------------------------------------------------
# Admin – Gallery
# ---------------------------------------------------------------------------

@app.route('/admin/gallery')
@login_required
def admin_gallery():
    photos = Photo.query.order_by(Photo.uploaded_at.desc()).all()
    return render_template('admin/gallery.html', photos=photos)


@app.route('/admin/gallery/upload', methods=['POST'])
@login_required
def admin_gallery_upload():
    files = request.files.getlist('photos')
    caption = request.form.get('caption', '').strip()
    category = request.form.get('category', 'general')
    uploaded = 0
    for file in files:
        if file and allowed_file(file.filename):
            filename = save_image(file, app.config['UPLOAD_GALLERY'])
            photo = Photo(filename=filename, caption=caption, category=category)
            db.session.add(photo)
            uploaded += 1
    db.session.commit()
    flash(f'{uploaded} photo(s) uploaded successfully.', 'success')
    return redirect(url_for('admin_gallery'))


@app.route('/admin/gallery/delete/<int:photo_id>', methods=['POST'])
@login_required
def admin_gallery_delete(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    filepath = os.path.join(app.config['UPLOAD_GALLERY'], photo.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    db.session.delete(photo)
    db.session.commit()
    flash('Photo deleted.', 'success')
    return redirect(url_for('admin_gallery'))


# ---------------------------------------------------------------------------
# Admin – Stories
# ---------------------------------------------------------------------------

@app.route('/admin/stories')
@login_required
def admin_stories():
    stories = Story.query.order_by(Story.created_at.desc()).all()
    return render_template('admin/stories.html', stories=stories)


@app.route('/admin/stories/new', methods=['GET', 'POST'])
@login_required
def admin_story_new():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        category = request.form.get('category', 'news')
        is_featured = 'is_featured' in request.form
        image_filename = ''
        file = request.files.get('image')
        if file and allowed_file(file.filename):
            image_filename = save_image(file, app.config['UPLOAD_STORIES'])
        slug = unique_slug(title, Story)
        story = Story(title=title, slug=slug, content=content,
                      category=category, is_featured=is_featured,
                      image_filename=image_filename)
        db.session.add(story)
        db.session.commit()
        flash('Story published!', 'success')
        return redirect(url_for('admin_stories'))
    return render_template('admin/story_form.html', story=None)


@app.route('/admin/stories/edit/<int:story_id>', methods=['GET', 'POST'])
@login_required
def admin_story_edit(story_id):
    story = Story.query.get_or_404(story_id)
    if request.method == 'POST':
        story.title = request.form.get('title', '').strip()
        story.content = request.form.get('content', '').strip()
        story.category = request.form.get('category', 'news')
        story.is_featured = 'is_featured' in request.form
        file = request.files.get('image')
        if file and allowed_file(file.filename):
            # Remove old image
            if story.image_filename:
                old = os.path.join(app.config['UPLOAD_STORIES'], story.image_filename)
                if os.path.exists(old):
                    os.remove(old)
            story.image_filename = save_image(file, app.config['UPLOAD_STORIES'])
        db.session.commit()
        flash('Story updated!', 'success')
        return redirect(url_for('admin_stories'))
    return render_template('admin/story_form.html', story=story)


@app.route('/admin/stories/delete/<int:story_id>', methods=['POST'])
@login_required
def admin_story_delete(story_id):
    story = Story.query.get_or_404(story_id)
    if story.image_filename:
        filepath = os.path.join(app.config['UPLOAD_STORIES'], story.image_filename)
        if os.path.exists(filepath):
            os.remove(filepath)
    db.session.delete(story)
    db.session.commit()
    flash('Story deleted.', 'success')
    return redirect(url_for('admin_stories'))


# ---------------------------------------------------------------------------
# Admin – Programs
# ---------------------------------------------------------------------------

@app.route('/admin/programs')
@login_required
def admin_programs():
    programs = Program.query.order_by(Program.display_order).all()
    return render_template('admin/programs.html', programs=programs)


@app.route('/admin/programs/new', methods=['GET', 'POST'])
@login_required
def admin_program_new():
    if request.method == 'POST':
        program = Program(
            name=request.form.get('name', '').strip(),
            description=request.form.get('description', '').strip(),
            age_group=request.form.get('age_group', '').strip(),
            fee=request.form.get('fee', '').strip(),
            duration=request.form.get('duration', '').strip(),
            batch_time=request.form.get('batch_time', '4:00 PM – 7:00 PM').strip(),
            is_active='is_active' in request.form,
            display_order=int(request.form.get('display_order', 0))
        )
        db.session.add(program)
        db.session.commit()
        flash('Program added!', 'success')
        return redirect(url_for('admin_programs'))
    return render_template('admin/program_form.html', program=None)


@app.route('/admin/programs/edit/<int:program_id>', methods=['GET', 'POST'])
@login_required
def admin_program_edit(program_id):
    program = Program.query.get_or_404(program_id)
    if request.method == 'POST':
        program.name = request.form.get('name', '').strip()
        program.description = request.form.get('description', '').strip()
        program.age_group = request.form.get('age_group', '').strip()
        program.fee = request.form.get('fee', '').strip()
        program.duration = request.form.get('duration', '').strip()
        program.batch_time = request.form.get('batch_time', '4:00 PM – 7:00 PM').strip()
        program.is_active = 'is_active' in request.form
        program.display_order = int(request.form.get('display_order', 0))
        db.session.commit()
        flash('Program updated!', 'success')
        return redirect(url_for('admin_programs'))
    return render_template('admin/program_form.html', program=program)


@app.route('/admin/programs/delete/<int:program_id>', methods=['POST'])
@login_required
def admin_program_delete(program_id):
    program = Program.query.get_or_404(program_id)
    db.session.delete(program)
    db.session.commit()
    flash('Program deleted.', 'success')
    return redirect(url_for('admin_programs'))


# ---------------------------------------------------------------------------
# Admin – Inquiries
# ---------------------------------------------------------------------------

@app.route('/admin/inquiries')
@login_required
def admin_inquiries():
    inquiries = Inquiry.query.order_by(Inquiry.created_at.desc()).all()
    # Mark all as read
    Inquiry.query.filter_by(is_read=False).update({'is_read': True})
    db.session.commit()
    return render_template('admin/inquiries.html', inquiries=inquiries)


@app.route('/admin/inquiries/delete/<int:inquiry_id>', methods=['POST'])
@login_required
def admin_inquiry_delete(inquiry_id):
    inquiry = Inquiry.query.get_or_404(inquiry_id)
    db.session.delete(inquiry)
    db.session.commit()
    flash('Inquiry deleted.', 'success')
    return redirect(url_for('admin_inquiries'))


# ---------------------------------------------------------------------------
# DB init & seed
# ---------------------------------------------------------------------------

def init_db():
    with app.app_context():
        db.create_all()
        # Create default admin if none exists
        if not Admin.query.first():
            admin = Admin(username='admin')
            admin.set_password('bala@2024')
            db.session.add(admin)
        # Seed default programs
        if not Program.query.first():
            default_programs = [
                Program(name='Speed Skating – Beginners', description='Learn the foundations of speed skating — correct posture, balance, stride technique, and safe stopping. Perfect for first-time skaters.',
                        age_group='5 – 12 years', fee='Contact us', duration='3 months',
                        batch_time='5:30 PM – 6:00 PM', display_order=1),
                Program(name='Speed Skating – Advanced', description='High-performance speed training, cornering, race tactics, and competition preparation for serious athletes.',
                        age_group='10+ years', fee='Contact us', duration='Ongoing',
                        batch_time='6:00 PM – 7:00 PM', display_order=2),
                Program(name='Roll Ball', description='Train in the exciting team sport of Roll Ball — combining skating agility with ball-handling and team strategy.',
                        age_group='8+ years', fee='Contact us', duration='Seasonal',
                        batch_time='5:30 PM – 7:00 PM', display_order=3),
                Program(name='Roller Skating Hockey', description='Learn roller hockey skills — skating, stick handling, passing, and match play for aspiring hockey players.',
                        age_group='8+ years', fee='Contact us', duration='Seasonal',
                        batch_time='5:30 PM – 7:00 PM', display_order=4),
            ]
            db.session.add_all(default_programs)
        db.session.commit()


# Run init_db at import time so gunicorn workers also initialise the DB
init_db()

if __name__ == '__main__':
    app.run(debug=True)
