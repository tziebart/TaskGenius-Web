import os
import sqlite3
import uuid
from flask import Flask, request, jsonify, session, flash, render_template, redirect, url_for, g
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError

# --- App Initialization ---
app = Flask(__name__)

# --- Configuration ---
# Reads the DATABASE_URL from Render's environment variables.
# The second argument is a default for local testing if the env var isn't set.
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'postgresql://user:password@host:port/dbname?sslmode=require' # Replace with your local PG or Supabase URL for local testing
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_default_dev_secret_key_that_is_long_and_secure')

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# --- Database Models ---
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Text, primary_key=True)
    email = db.Column(db.Text, unique=True, nullable=False)
    name = db.Column(db.Text, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Text, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Text, db.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())
    updated_at = db.Column(db.TIMESTAMP, server_default=db.func.now(), onupdate=db.func.now())

class ProjectMember(db.Model):
    __tablename__ = 'project_members'
    project_id = db.Column(db.Text, db.ForeignKey('projects.id', ondelete='CASCADE'), primary_key=True)
    user_id = db.Column(db.Text, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Text, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.Text, nullable=False, default='To Do')
    priority = db.Column(db.Text, nullable=False, default='Medium')
    due_date = db.Column(db.Text)
    creator_id = db.Column(db.Text, db.ForeignKey('users.id', ondelete='SET NULL'))
    assignee_id = db.Column(db.Text, db.ForeignKey('users.id', ondelete='SET NULL'))
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())
    updated_at = db.Column(db.TIMESTAMP, server_default=db.func.now(), onupdate=db.func.now())

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Text, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=False)
    comment_text = db.Column(db.Text, nullable=False)
    is_alert = db.Column(db.Integer, nullable=False, default=0)
    media_attachments = db.Column(db.Text)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Text, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=False)
    message_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())


# --- Database Initialization Command ---
@app.cli.command('init-db')
def init_db_command():
    """Creates the database tables and seeds initial data."""
    db.drop_all()
    db.create_all()
    hashed_password = bcrypt.generate_password_hash('password123').decode('utf-8')
    owner = User(id='owner01', email='owner@workbuddy.pro', name='Owner User', password_hash=hashed_password, role='Owner')
    foreman = User(id='foremanA', email='alice@workbuddy.pro', name='Foreman Alice', password_hash=hashed_password, role='Foreman')
    worker1 = User(id='workerX', email='bob@workbuddy.pro', name='Worker Bob', password_hash=hashed_password, role='Worker')
    project_alpha = Project(id='proj_alpha', name='Project Alpha - Downtown Renovation', description='Complete renovation.', owner_id='owner01')
    db.session.add_all([owner, foreman, worker1, project_alpha])
    db.session.commit()
    member1 = ProjectMember(project_id='proj_alpha', user_id='owner01')
    member2 = ProjectMember(project_id='proj_alpha', user_id='foremanA')
    member3 = ProjectMember(project_id='proj_alpha', user_id='workerX')
    db.session.add_all([member1, member2])
    db.session.commit()
    print('Initialized the database and seeded mock data.')


# --- HTML Serving Routes (for our prototype pages) ---
@app.route('/')
def home_page():
    return render_template('login.html')

@app.route('/projects')
def project_select_page():
    if 'current_user' not in session: return redirect(url_for('home_page'))
    # This logic is now handled by the API, but the route can render a base page if needed
    return render_template('project_select.html', user=session['current_user'])

@app.route('/project/<project_id>/tasks')
def tasks_page_for_project(project_id):
    if 'current_user' not in session: return redirect(url_for('home_page'))
    # This route now primarily serves the main HTML shell for the React Native app to work within for the prototype
    # For the real native app, this route isn't strictly needed
    user = session.get('current_user')
    project = Project.query.get(project_id) # Example of getting project details
    users_for_assignment = User.query.all()
    return render_template('index.html', user=user, project=project, assignable_users=users_for_assignment)


# --- API v1 Routes ---

# Auth
@app.route('/login', methods=['POST']) # This URL is now ambiguous, better to move all APIs under /api
def login_route(): # This should be renamed to login_api to avoid confusion
    data = request.json
    email = data.get('email')
    password = data.get('password')
    user = User.query.filter_by(email=email).first()
    if user and bcrypt.check_password_hash(user.password_hash, password):
        user_data = {'id': user.id, 'name': user.name, 'email': user.email, 'role': user.role}
        session['current_user'] = user_data
        return jsonify({"success": True, "user": user_data}), 200
    else:
        return jsonify({"error": "Invalid email or password."}), 401

@app.route('/logout')
def logout_route():
    session.clear()
    return redirect(url_for('home_page'))

@app.route('/select_project/<project_id>') # This should be a POST API call
def select_project_route(project_id):
    if 'current_user' not in session: return redirect(url_for('home_page'))
    project = Project.query.get(project_id)
    if project:
        session['current_project'] = {'id': project.id, 'name': project.name}
        return redirect(url_for('tasks_page_for_project', project_id=project_id))
    return redirect(url_for('project_select_page'))

# Projects API
@app.route('/api/v1/projects', methods=['GET'])
def get_projects_api():
    if 'current_user' not in session: return jsonify({"error": "Unauthorized"}), 401
    # In real app, filter projects by user membership from project_members table
    projects_db = Project.query.order_by(Project.name).all()
    projects_list = [{'id': p.id, 'name': p.name, 'description': p.description} for p in projects_db]
    return jsonify(projects_list)

# Tasks API
@app.route('/api/v1/projects/<project_id>/tasks', methods=['GET'])
def get_tasks(project_id):
    # ... full implementation from before ...
    if 'current_user' not in session: return jsonify({"error": "Unauthorized"}), 401
    tasks_db = Task.query.filter_by(project_id=project_id).order_by(Task.created_at.desc()).all()
    tasks_list = []
    for t in tasks_db:
        assignee = User.query.get(t.assignee_id) if t.assignee_id else None
        tasks_list.append({
            'id': t.id, 'title': t.title, 'description': t.description,
            'is_completed': (t.status == 'Done'), # Translate status to boolean for client
            'status': t.status, 'priority': t.priority, 'due_date': t.due_date,
            'assignee_id': t.assignee_id, 'assignee_name': assignee.name if assignee else None
        })
    return jsonify(tasks_list)

# ... All other POST, PUT, DELETE APIs for Tasks and Comments go here ...
# Their logic would need to be updated to use SQLAlchemy:
# e.g., for add_task:
# new_task = Task(title=..., project_id=...)
# db.session.add(new_task)
# db.session.commit()

if __name__ == '__main__':
    # Using app.cli.command is preferred, so this block is just for local dev run
    app.run(host='0.0.0.0', debug=True)