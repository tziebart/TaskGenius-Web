import os
import uuid
from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from sqlalchemy.exc import IntegrityError

# --- App Initialization & Config ---
app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# This reads the DATABASE_URL from Render's environment variables.
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_long_and_super_secret_dev_key_for_local_use')
# <<< ADD THIS BLOCK FOR DATABASE CONNECTION POOLING >>>
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}
# <<< END OF NEW BLOCK >>>
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

# In app.py, add this class with your other models

class Invitation(db.Model):
    __tablename__ = 'invitations'
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.Text, unique=True, nullable=False)
    email = db.Column(db.Text, nullable=False)
    project_id = db.Column(db.Text, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    role = db.Column(db.Text, nullable=False)
    status = db.Column(db.Text, nullable=False, default='pending') # pending, accepted
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())
    accepted_at = db.Column(db.TIMESTAMP)
    accepted_by_user_id = db.Column(db.Text, db.ForeignKey('users.id', ondelete='SET NULL'))

# --- Database Initialization Command ---
@app.cli.command('init-db')
def init_db_command():
    """Creates all database tables and seeds mock data."""
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
# In app.py, replace all your existing @app.route functions with this block

# --- API Routes ---

@app.route('/')
def index():
    """A simple status endpoint to confirm the API is running."""
    return jsonify({"status": "TaskGenius API is running."})

# --- Auth APIs ---
@app.route('/api/v1/login', methods=['POST'])
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

@app.route('/api/v1/logout', methods=['POST'])
def logout_api():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."})

# --- User APIs ---

@app.route('/api/v1/users/<user_id>', methods=['DELETE'])
def delete_user_api(user_id):
    # --- Authorization ---
    if 'current_user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    # CRITICAL: This is a highly privileged action. Only allow a user with the 'Owner' role.
    if session['current_user']['role'] != 'Owner':
        return jsonify({"error": "Forbidden. You do not have permission to delete users."}), 403

    # Add a check to prevent an owner from deleting their own account.
    if session['current_user']['id'] == user_id:
        return jsonify({"error": "Owners cannot delete their own account via the API."}), 400

    try:
        user_to_delete = User.query.get(user_id)

        if not user_to_delete:
            return jsonify({"error": "User not found"}), 404

        # Our database schema is set up with 'ON DELETE SET NULL' for task creators/assignees
        # and 'ON DELETE CASCADE' for project memberships, so the database will handle
        # cleaning up all the references correctly when we delete the user from the 'users' table.
        db.session.delete(user_to_delete)
        db.session.commit()

        return jsonify({"message": f"User '{user_to_delete.name}' has been deleted successfully."}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error deleting user {user_id}: {e}")
        return jsonify({"error": "A server error occurred while deleting the user."}), 500

# --- Invitation APIs ---

@app.route('/api/v1/projects/<project_id>/invitations', methods=['POST'])
def create_invitation_api(project_id):
    # --- Authorization ---
    if 'current_user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if session['current_user']['role'] != 'Owner':
        return jsonify({"error": "Forbidden. Only Owners can send invitations."}), 403

    data = request.json
    email = data.get('email')
    role = data.get('role')

    # --- Validation ---
    if not email or not role:
        return jsonify({"error": "Email and role are required."}), 400
    if role not in ['Foreman', 'Worker']:
        return jsonify({"error": "Invalid role specified. Must be 'Foreman' or 'Worker'."}), 400

    # Check if a user with this email already exists in the system
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "A user with this email already exists."}), 409 # 409 Conflict code

    # Check if a pending invitation for this email already exists
    if Invitation.query.filter_by(email=email, status='pending').first():
        return jsonify({"error": "An invitation for this email is already pending."}), 409

    try:
        # Generate a unique, secure token for the invitation link
        token = str(uuid.uuid4())

        new_invitation = Invitation(
            token=token,
            email=email,
            project_id=project_id,
            role=role
        )
        db.session.add(new_invitation)
        db.session.commit()

        # In a real app, you would now trigger an email to be sent to the user.
        # For our API, we can return the generated token/link for testing purposes.
        invite_link = f"https://YourAppDomain.com/register?token={token}"

        return jsonify({
            "message": "Invitation created successfully.",
            "email": email,
            "role": role,
            "invite_link_for_testing": invite_link
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"Error creating invitation: {e}")
        return jsonify({"error": "A server error occurred while creating the invitation."}), 500

# --- Project APIs ---
@app.route('/api/v1/projects', methods=['GET'])
def get_projects_api():
    if 'current_user' not in session: return jsonify({"error": "Unauthorized"}), 401
    # In a real app, you would filter projects based on the user's membership in the project_members table.
    # For now, we return all projects.
    projects_db = Project.query.order_by(Project.name).all()
    projects_list = [{'id': p.id, 'name': p.name, 'description': p.description} for p in projects_db]
    return jsonify(projects_list)

# In app.py, add this new API route

@app.route('/api/v1/projects/<project_id>/members', methods=['GET'])
def get_project_members_api(project_id):
    if 'current_user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    # In a real app, first verify the current user is also a member of this project

    try:
        # This query joins our three tables: project_members, users, and projects
        # to find all users for a given project_id.
        members = db.session.query(User).join(ProjectMember, User.id == ProjectMember.user_id).filter(ProjectMember.project_id == project_id).all()

        members_list = []
        for member in members:
            members_list.append({
                "id": member.id,
                "name": member.name,
                "role": member.role
            })

        return jsonify(members_list)

    except Exception as e:
        print(f"Error fetching members for project {project_id}: {e}")
        return jsonify({"error": "Server error while fetching project members."}), 500

@app.route('/api/v1/select-project/<project_id>', methods=['POST'])
def select_project_api(project_id):
    if 'current_user' not in session: return jsonify({"error": "Unauthorized"}), 401
    project = Project.query.get(project_id)
    if project:
        # Here too, you'd verify the user is a member of this project.
        session['current_project'] = {'id': project.id, 'name': project.name}
        return jsonify({"success": True, "project": session['current_project']})
    return jsonify({"error": "Project not found"}), 404

# --- Task APIs ---
@app.route('/api/v1/projects/<project_id>/tasks', methods=['GET'])
def get_tasks_api(project_id):
    if 'current_user' not in session: return jsonify({"error": "Unauthorized"}), 401
    # Add authorization check here
    try:
        tasks_with_assignee = db.session.query(Task, User.name.label('assignee_name'))\
            .outerjoin(User, Task.assignee_id == User.id)\
            .filter(Task.project_id == project_id).order_by(Task.created_at.desc()).all()
        tasks_list = []
        for task_obj, assignee_name in tasks_with_assignee:
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
def add_task_api(project_id):
    if 'current_user' not in session: return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    if not data or not data.get('title') or not data.get('title').strip():
        return jsonify({"error": "Title is required"}), 400
    try:
        creator_id = session['current_user']['id']
        assignee_id = data.get('assignee_id') or creator_id
        new_task = Task(project_id=project_id, title=data['title'].strip(), description=data.get('description', '').strip(),
                        due_date=data.get('due_date'), priority=data.get('priority', 'Medium'),
                        creator_id=creator_id, assignee_id=assignee_id)
        db.session.add(new_task)
        db.session.commit()
        return jsonify({'id': new_task.id, 'message': 'Task created successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Server error while creating task.", "details": str(e)}), 500

# In app.py, add this to your Task APIs section

@app.route('/api/v1/tasks/<int:task_id>', methods=['GET'])
def get_task_detail_api(task_id):
    if 'current_user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        # Fetch the specific task and join with the User table to get the assignee's name
        task_data = db.session.query(Task, User.name.label('assignee_name'))\
            .outerjoin(User, Task.assignee_id == User.id)\
            .filter(Task.id == task_id).first()

        if not task_data:
            return jsonify({"error": "Task not found"}), 404

        # In a real app, you would add a security check here to ensure the current user
        # is a member of the project that this task belongs to.

        task_obj, assignee_name = task_data

        # Convert the task object to a dictionary for JSON response
        task_dict = {
            'id': task_obj.id,
            'title': task_obj.title,
            'description': task_obj.description,
            'status': task_obj.status,
            'priority': task_obj.priority,
            'due_date': task_obj.due_date,
            'assignee_id': task_obj.assignee_id,
            'assignee_name': assignee_name
            # We can add creator info here too if needed
        }
        return jsonify(task_dict)

    except Exception as e:
        print(f"Error fetching detail for task {task_id}: {e}")
        return jsonify({"error": "Server error while fetching task details."}), 500

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

# --- Comment APIs ---
@app.route('/api/v1/tasks/<int:task_id>/comments', methods=['GET'])
def get_comments_api(task_id):
    if 'current_user' not in session: return jsonify({"error": "Unauthorized"}), 401
    comments_with_user = db.session.query(Comment, User.name.label('user_name'))\
        .join(User, Comment.user_id == User.id)\
        .filter(Comment.task_id == task_id).order_by(Comment.created_at.asc()).all()
    comments_list = []
    for comment, user_name in comments_with_user:
        comments_list.append({ 'id': comment.id, 'comment_text': comment.comment_text, 'user_name': user_name, 'created_at': comment.created_at.isoformat() })
    return jsonify(comments_list)

@app.route('/api/v1/tasks/<int:task_id>/comments', methods=['POST'])
def add_comment_api(task_id):
    if 'current_user' not in session: return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    if not data or not data.get('comment_text') or not data.get('comment_text').strip():
        return jsonify({"error": "Comment text cannot be empty"}), 400
    try:
        new_comment = Comment(task_id=task_id, user_id=session['current_user']['id'], comment_text=data['comment_text'].strip())
        db.session.add(new_comment)
        db.session.commit()
        return jsonify({'id': new_comment.id, 'message': 'Comment added successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Server error while adding comment.", "details": str(e)}), 500
        
# --- The rest of your Task and Comment API routes would follow the same pattern ---
# For brevity, I'm omitting the full text for PUT/DELETE tasks and GET/POST comments,
# but ensure they are present in your file as we designed them.
# In app.py, add this new section for Chat API Endpoints

# --- Chat API Endpoints ---

@app.route('/api/v1/chat/<conversation_id>/messages', methods=['GET'])
def get_chat_messages(conversation_id):
    # Security check: Ensure user is logged in
    if 'current_user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    # In a real app, we would also add a security check here to ensure
    # the logged-in user is a valid participant in this conversation.

    try:
        # Fetch messages, joining with the users table to get the sender's name
        messages_from_db = db.session.query(Message, User.name.label('user_name'))\
            .join(User, Message.user_id == User.id)\
            .filter(Message.conversation_id == conversation_id)\
            .order_by(Message.created_at.asc()).all()

        messages_list = []
        for message, user_name in messages_from_db:
            messages_list.append({
                'id': message.id,
                'conversation_id': message.conversation_id,
                'user_id': message.user_id,
                'user_name': user_name,
                'message_text': message.message_text,
                'created_at': message.created_at.isoformat()
            })

        return jsonify(messages_list)
    except Exception as e:
        print(f"Error fetching messages for conversation {conversation_id}: {e}")
        return jsonify({"error": "Server error while fetching messages."}), 500

@app.route('/api/v1/chat/<conversation_id>/messages', methods=['POST'])
def post_chat_message(conversation_id):
    if 'current_user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    # Add conceptual security check here for conversation participation

    data = request.json
    message_text = data.get('message_text')
    user_id = session['current_user']['id']

    if not message_text or not message_text.strip():
        return jsonify({"error": "Message text cannot be empty"}), 400

    try:
        new_message = Message(
            conversation_id=conversation_id,
            user_id=user_id,
            message_text=message_text.strip()
        )
        db.session.add(new_message)
        db.session.commit()

        # Fetch the user's name to include in the response
        user = User.query.get(user_id)
        user_name = user.name if user else "Unknown User"

        # Return the newly created message object so the client can display it
        return jsonify({
            'id': new_message.id,
            'conversation_id': new_message.conversation_id,
            'user_id': new_message.user_id,
            'user_name': user_name,
            'message_text': new_message.message_text,
            'created_at': new_message.created_at.isoformat()
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"Error posting message to conversation {conversation_id}: {e}")
        return jsonify({"error": "Server error while posting message."}), 500
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)