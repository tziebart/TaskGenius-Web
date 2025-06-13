import os
import sqlite3
import uuid
from flask import Flask, request, jsonify, session, flash, render_template, redirect, url_for, g
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError
from flask_cors import CORS
# --- App Initialization ---
app = Flask(__name__)
CORS(app)

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
# In app.py, find your old task API routes and replace them with this block.
# This should go after your Project API route.

# --- Task API Endpoints (SQLAlchemy Version) ---

# In app.py
# Make sure you have these TWO separate functions for the same URL path.

# --- Task API Endpoints (SQLAlchemy Version) ---

@app.route('/api/v1/projects/<project_id>/tasks', methods=['GET'])
def get_tasks_api_v2(project_id):
    # <<< ADD THIS UNIQUE LOGGING LINE >>>
    print("--- EXECUTING get_tasks_api_v2 (the GET route) ---")
    """This function handles ONLY GET requests to list tasks."""

    if 'current_user' not in session: return jsonify({"error": "Unauthorized"}), 401

    try:
        # This query does NOT look at request.json
        tasks_db = db.session.query(Task, User.name.label('assignee_name'))\
            .outerjoin(User, Task.assignee_id == User.id)\
            .filter(Task.project_id == project_id)\
            .order_by(Task.created_at.desc()).all()

        tasks_list = []
        for task_obj, assignee_name in tasks_db:
            tasks_list.append({
                'id': task_obj.id, 'title': task_obj.title, 'description': task_obj.description,
                'status': task_obj.status, 'is_completed': task_obj.status == 'Done',
                'priority': task_obj.priority, 'due_date': task_obj.due_date,
                'assignee_id': task_obj.assignee_id, 'assignee_name': assignee_name
            })
        return jsonify(tasks_list)
    except Exception as e:
        print(f"Error fetching tasks: {e}")
        return jsonify({"error": "Server error while fetching tasks."}), 500


@app.route('/api/v1/projects/<project_id>/tasks', methods=['POST'])
def add_task_api_v2(project_id):
    # <<< ADD THIS UNIQUE LOGGING LINE >>>
    print("--- EXECUTING add_task_api_v2 (thePost route) ---")
    """This function handles ONLY POST requests to create a new task."""
    if 'current_user' not in session: return jsonify({"error": "Unauthorized"}), 401

    data = request.json # This is correct here, because it's a POST request
    title = data.get('title')
    if not title or not title.strip():
        return jsonify({"error": "Title is required"}), 400

    creator_id = session['current_user']['id']
    assignee_id = data.get('assignee_id') or creator_id

    try:
        new_task = Task(
            project_id=project_id,
            title=title.strip(),
            description=data.get('description', '').strip(),
            due_date=data.get('due_date'),
            priority=data.get('priority', 'Medium'),
            creator_id=creator_id,
            assignee_id=assignee_id
        )
        db.session.add(new_task)
        db.session.commit()

        # ... logic to return the newly created task ...
        assignee = User.query.get(new_task.assignee_id)
        return jsonify({
            'id': new_task.id, 'title': new_task.title, # etc.
            'assignee_name': assignee.name if assignee else None
        }), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error adding task: {e}")
        return jsonify({"error": "Server error while adding task."}), 500

@app.route('/api/v1/tasks/<int:task_id>', methods=['PUT'])
def update_task_api_v2(task_id): # Renamed function
    if 'current_user' not in session: return jsonify({"error": "Unauthorized"}), 401

    task_to_update = Task.query.get(task_id)
    if not task_to_update:
        return jsonify({"error": "Task not found"}), 404

    # Add security check here to ensure user can edit this task

    data = request.json
    task_to_update.title = data.get('title', task_to_update.title)
    task_to_update.description = data.get('description', task_to_update.description)
    task_to_update.status = data.get('status', task_to_update.status)
    task_to_update.priority = data.get('priority', task_to_update.priority)
    task_to_update.due_date = data.get('due_date', task_to_update.due_date)
    task_to_update.assignee_id = data.get('assignee_id', task_to_update.assignee_id)

    try:
        db.session.commit()
        # Re-fetch with join to get assignee name for response
        response_data = db.session.query(Task, User.name.label('assignee_name'))\
            .outerjoin(User, Task.assignee_id == User.id)\
            .filter(Task.id == task_id).first()

        task_obj, assignee_name = response_data
        return jsonify({
            'id': task_obj.id, 'title': task_obj.title, 'description': task_obj.description,
            'status': task_obj.status, 'is_completed': task_obj.status == 'Done',
            'priority': task_obj.priority, 'due_date': task_obj.due_date,
            'assignee_id': task_obj.assignee_id, 'assignee_name': assignee_name
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error updating task: {e}")
        return jsonify({"error": "Server error while updating task."}), 500


@app.route('/api/v1/tasks/<int:task_id>', methods=['DELETE'])
def delete_task_api_v2(task_id): # Renamed function
    if 'current_user' not in session: return jsonify({"error": "Unauthorized"}), 401

    task_to_delete = Task.query.get(task_id)
    if not task_to_delete:
        return jsonify({"error": "Task not found"}), 404

    # Add security check here

    try:
        db.session.delete(task_to_delete)
        db.session.commit()
        return jsonify({"message": "Task deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting task: {e}")
        return jsonify({"error": "Server error while deleting task."}), 500

if __name__ == '__main__':
    # Using app.cli.command is preferred, so this block is just for local dev run
    app.run(host='0.0.0.0', debug=True)