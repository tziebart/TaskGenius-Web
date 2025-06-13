import os
import sqlite3
import uuid
from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from sqlalchemy import text

# --- App Initialization ---
app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# --- Configuration ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_long_and_super_secret_dev_key')

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
    worker = User(id='workerX', email='bob@workbuddy.pro', name='Worker Bob', password_hash=hashed_password, role='Worker')
    project_alpha = Project(id='proj_alpha', name='Project Alpha - Downtown Renovation', description='Renovation of library.', owner_id='owner01')
    db.session.add_all([owner, foreman, worker, project_alpha])
    db.session.commit()
    member1 = ProjectMember(project_id='proj_alpha', user_id='owner01')
    member2 = ProjectMember(project_id='proj_alpha', user_id='foremanA')
    member3 = ProjectMember(project_id='proj_alpha', user_id='workerX')
    db.session.add_all([member1, member2, member3])
    db.session.commit()
    print('Initialized and seeded the database.')

# --- API Routes ---

@app.route('/login', methods=['POST'])
def login_api():
    data = request.json
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Email and password are required."}), 400
    user = User.query.filter_by(email=data['email']).first()
    if user and bcrypt.check_password_hash(user.password_hash, data['password']):
        user_data = {k: v for k, v in user.__dict__.items() if not k.startswith('_') and k != 'password_hash'}
        session['current_user'] = user_data
        return jsonify({"success": True, "user": user_data}), 200
    return jsonify({"error": "Invalid email or password."}), 401

@app.route('/logout', methods=['POST'])
def logout_api():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."}), 200

@app.route('/api/v1/projects', methods=['GET'])
def get_projects_api():
    if 'current_user' not in session: return jsonify({"error": "Unauthorized"}), 401
    projects = Project.query.order_by(Project.name).all()
    return jsonify([{'id': p.id, 'name': p.name, 'description': p.description} for p in projects])

@app.route('/api/v1/projects/<project_id>/tasks', methods=['GET'])
def get_tasks_api(project_id):
    if 'current_user' not in session: return jsonify({"error": "Unauthorized"}), 401
    tasks_with_assignee = db.session.query(Task, User.name.label('assignee_name'))\
        .outerjoin(User, Task.assignee_id == User.id)\
        .filter(Task.project_id == project_id).order_by(Task.created_at.desc()).all()
    tasks_list = []
    for task, assignee_name in tasks_with_assignee:
        tasks_list.append({
            'id': task.id, 'title': task.title, 'description': task.description,
            'status': task.status, 'is_completed': task.status == 'Done',
            'priority': task.priority, 'due_date': task.due_date,
            'assignee_id': task.assignee_id, 'assignee_name': assignee_name
        })
    return jsonify(tasks_list)

@app.route('/api/v1/projects/<project_id>/tasks', methods=['POST'])
def add_task_api(project_id):
    if 'current_user' not in session: return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    if not data or not data.get('title') or not data.get('title').strip():
        return jsonify({"error": "Title is required"}), 400
    try:
        new_task = Task(project_id=project_id, title=data['title'].strip(), description=data.get('description', '').strip(),
                        due_date=data.get('due_date'), priority=data.get('priority', 'Medium'),
                        creator_id=session['current_user']['id'], assignee_id=data.get('assignee_id') or session['current_user']['id'])
        db.session.add(new_task)
        db.session.commit()
        return jsonify({'id': new_task.id, 'message': 'Task created successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/tasks/<int:task_id>', methods=['PUT'])
def update_task_api(task_id):
    if 'current_user' not in session: return jsonify({"error": "Unauthorized"}), 401
    task = Task.query.get_or_404(task_id)
    # Add authorization logic here: if session['current_user']['id'] can edit task...
    data = request.json
    task.title = data.get('title', task.title)
    task.description = data.get('description', task.description)
    task.status = data.get('status', task.status)
    task.priority = data.get('priority', task.priority)
    task.due_date = data.get('due_date', task.due_date)
    task.assignee_id = data.get('assignee_id', task.assignee_id)
    db.session.commit()
    return jsonify({'id': task.id, 'message': 'Task updated successfully'})

@app.route('/api/v1/tasks/<int:task_id>', methods=['DELETE'])
def delete_task_api(task_id):
    if 'current_user' not in session: return jsonify({"error": "Unauthorized"}), 401
    task = Task.query.get_or_404(task_id)
    # Add authorization logic here
    db.session.delete(task)
    db.session.commit()
    return jsonify({'message': 'Task deleted successfully'}), 200

@app.route('/api/v1/tasks/<int:task_id>/comments', methods=['GET'])
def get_comments_api(task_id):
    if 'current_user' not in session: return jsonify({"error": "Unauthorized"}), 401
    comments = db.session.query(Comment, User.name.label('user_name'))\
        .join(User, Comment.user_id == User.id)\
        .filter(Comment.task_id == task_id).order_by(Comment.created_at.asc()).all()
    comments_list = []
    for comment, user_name in comments:
        comments_list.append({
            'id': comment.id, 'comment_text': comment.comment_text,
            'user_id': comment.user_id, 'user_name': user_name,
            'created_at': comment.created_at.isoformat()
        })
    return jsonify(comments_list)

@app.route('/api/v1/tasks/<int:task_id>/comments', methods=['POST'])
def add_comment_api(task_id):
    if 'current_user' not in session: return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    if not data or not data.get('comment_text') or not data.get('comment_text').strip():
        return jsonify({"error": "Comment text cannot be empty"}), 400
    try:
        new_comment = Comment(task_id=task_id, user_id=session['current_user']['id'],
                              comment_text=data['comment_text'].strip())
        db.session.add(new_comment)
        db.session.commit()
        # You'd ideally return the full object with user name
        return jsonify({'id': new_comment.id, 'message': 'Comment added successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    