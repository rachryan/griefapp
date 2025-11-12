# app.py — Flask app with auth, DB, Socket.IO chat, REST /api/chat, and seed command
from __future__ import annotations
import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv

from chatbot import GriefSupportBot, BotConfig

# --- Config ---
load_dotenv()  # load .env in dev
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///grief_support.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Extensions ---
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
socketio = SocketIO(app, cors_allowed_origins="*")  # tighten in prod

# --- Bot ---
grief_bot = GriefSupportBot(BotConfig(deterministic=False))

# --- Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    join_date = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

class Blog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.Column(db.String(100), nullable=False)

class Webinar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    link = db.Column(db.String(200), nullable=False)
    host = db.Column(db.String(100), nullable=False)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)

class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    order = db.Column(db.Integer, nullable=False)

class CourseProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, nullable=False)
    completed_modules = db.Column(db.Text, default='')  # comma-separated module IDs
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)

class SelfCareRecommendation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)  # Easy/Medium/Challenging

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes ---
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/resources')
def resources():
    return render_template('home.html')  # placeholder

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('member_dashboard'))
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        if not username or not email or not password:
            flash('All fields are required.')
            return redirect(url_for('register'))
        exists = User.query.filter((User.username == username) | (User.email == email)).first()
        if exists:
            flash('Username or email already exists.')
            return redirect(url_for('register'))
        u = User(username=username, email=email)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('member_dashboard'))
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('member_dashboard'))
        flash('Invalid email or password.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('home'))

@app.route('/member/dashboard')
@login_required
def member_dashboard():
    recs = SelfCareRecommendation.query.order_by(db.func.random()).limit(3).all()
    upcoming = Webinar.query.filter(Webinar.date > datetime.utcnow()).order_by(Webinar.date).limit(2).all()
    latest = Blog.query.order_by(Blog.date_posted.desc()).limit(3).all()
    return render_template('member/dashboard.html', recommendations=recs, webinars=upcoming, blogs=latest)

@app.route('/member/blogs')
@login_required
def member_blogs():
    blogs = Blog.query.order_by(Blog.date_posted.desc()).all()
    return render_template('member/blogs.html', blogs=blogs)

@app.route('/member/blog/<int:blog_id>')
@login_required
def view_blog(blog_id):
    blog = Blog.query.get_or_404(blog_id)
    return render_template('member/blog_single.html', blog=blog)

@app.route('/member/webinars')
@login_required
def member_webinars():
    upcoming = Webinar.query.filter(Webinar.date > datetime.utcnow()).order_by(Webinar.date).all()
    past = Webinar.query.filter(Webinar.date <= datetime.utcnow()).order_by(Webinar.date.desc()).all()
    return render_template('member/webinars.html', upcoming_webinars=upcoming, past_webinars=past)

@app.route('/member/courses')
@login_required
def member_courses():
    courses = Course.query.all()
    return render_template('member/courses.html', courses=courses)

@app.route('/member/course/<int:course_id>')
@login_required
def view_course(course_id):
    course = Course.query.get_or_404(course_id)
    modules = Module.query.filter_by(course_id=course_id).order_by(Module.order).all()
    progress = CourseProgress.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if not progress:
        progress = CourseProgress(user_id=current_user.id, course_id=course_id)
        db.session.add(progress)
        db.session.commit()
    completed = progress.completed_modules.split(',') if progress.completed_modules else []
    return render_template('member/course_single.html', course=course, modules=modules, completed_modules=completed)

@app.route('/member/module/<int:module_id>')
@login_required
def view_module(module_id):
    module = Module.query.get_or_404(module_id)
    progress = CourseProgress.query.filter_by(user_id=current_user.id, course_id=module.course_id).first()
    if not progress:
        progress = CourseProgress(user_id=current_user.id, course_id=module.course_id)
        db.session.add(progress)
    completed = set(progress.completed_modules.split(',')) if progress.completed_modules else set()
    if str(module_id) not in completed:
        completed.add(str(module_id))
        progress.completed_modules = ','.join(sorted([x for x in completed if x]))
        progress.last_accessed = datetime.utcnow()
        db.session.commit()
    return render_template('member/module_single.html', module=module)

@app.route('/member/chat')
@login_required
def chat():
    return render_template('member/chat.html')

# --- REST Chat API (handy for testing without sockets) ---
@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    payload = request.get_json(silent=True) or {}
    msg = (payload.get('message') or '').strip()
    if not msg:
        return jsonify({"error": "Empty message"}), 400
    resp = grief_bot.get_response(msg)
    return jsonify(resp), 200

# --- Socket.IO events (scoped per client) ---
@socketio.on('connect')
def handle_connect():
    if not current_user.is_authenticated:
        # Optional: reject unauthenticated socket connections
        # return False
        pass
    emit('bot_message', {
        'user': 'Grief Support Bot',
        'message': "Hello, I'm here to support you. How are you feeling today?"
    })

@socketio.on('user_message')
def handle_user_message(data):
    if not current_user.is_authenticated:
        return
    user_message = (data or {}).get('message', '').strip()
    if not user_message:
        return
    resp = grief_bot.get_response(user_message)
    emit('bot_message', {
        'user': 'Grief Support Bot',
        'message': resp.get('text', ''),
        'category': resp.get('category', 'default')
    })

# --- DB setup + sample data ---
with app.app_context():
    db.create_all()

@app.cli.command("seed")
def seed():
    """Seed the database with sample content."""
    # Don’t duplicate
    if Blog.query.first():
        print("Already seeded.")
        return

    blogs = [
        Blog(title="Understanding the Stages of Grief",
             content="Grief is a natural response to loss…",
             author="Dr. Emily Johnson"),
        Blog(title="Coping with Loss During Holidays",
             content="The holiday season can be challenging when you’re grieving…",
             author="Sarah Williams, Grief Counselor"),
        Blog(title="The Physical Symptoms of Grief",
             content="Grief can manifest physically: fatigue, sleep issues…",
             author="Dr. Michael Chen")
    ]

    webinars = [
        Webinar(title="Finding Meaning After Loss",
                description="A discussion on meaning and purpose after loss.",
                date=datetime(2025, 3, 15, 18, 0),
                link="https://example.com/webinar/meaning-after-loss",
                host="Dr. Robert Thompson"),
        Webinar(title="Supporting Children Through Grief",
                description="Helping children process and cope with loss.",
                date=datetime(2025, 3, 22, 18, 0),
                link="https://example.com/webinar/children-grief",
                host="Lisa Rodriguez, Child Psychologist")
    ]

    c = Course(title="Journey Through Grief",
               description="A gentle course to companion you through grief.")
    db.session.add(c)
    db.session.flush()
    modules = [
        Module(title="Understanding Grief", content="What grief is…", course_id=c.id, order=1),
        Module(title="Common Reactions", content="Emotional, physical, behavioral…", course_id=c.id, order=2),
        Module(title="Coping Strategies", content="Day-by-day techniques…", course_id=c.id, order=3),
        Module(title="Finding Support", content="People and resources…", course_id=c.id, order=4),
        Module(title="Moving Forward", content="Rebuilding and honoring…", course_id=c.id, order=5),
    ]

    recs = [
        SelfCareRecommendation(category="Physical", title="Gentle Morning Walk",
                               description="15 minutes outside, slow breathing, easy pace.",
                               difficulty="Easy"),
        SelfCareRecommendation(category="Emotional", title="Journaling",
                               description="10 minutes on ‘what hurts most right now’.",
                               difficulty="Easy"),
        SelfCareRecommendation(category="Social", title="Reach Out",
                               description="Text one trusted person for a check-in later today.",
                               difficulty="Medium"),
        SelfCareRecommendation(category="Spiritual", title="5-Minute Meditation",
                               description="Quiet breath practice; count senses (5-4-3-2-1).",
                               difficulty="Easy"),
    ]

    db.session.add_all(blogs + webinars + modules + recs)
    db.session.commit()
    print("Seeded.")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)
