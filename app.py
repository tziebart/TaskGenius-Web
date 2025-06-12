import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify, g, session, flash # Added session, request, redirect, url_for
from flask_bcrypt import Bcrypt
import os

DATABASE = 'taskgenius.db'

app = Flask(__name__)
app.config['DATABASE'] = DATABASE
app.config['SECRET_KEY'] = 'your_very_secret_key_here' # Important for session management! Change this in a real app.
bcrypt = Bcrypt(app)

# Helper function to get a database connection (no changes needed here)
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row
    return db

# Close the database connection (no changes needed here)
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Database initialization function (no changes needed here, assuming it ran once)
# In app.py, replace your entire init_db() function with this complete version:

def init_db():
    with app.app_context():
        db = get_db()
        # Execute the schema script to create (or re-create) tables
        with open('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit() # Commit the table creation
        print("Database schema has been created.")

        cursor = db.cursor()
        # Check if users table is empty before inserting mock data
        cursor.execute("SELECT COUNT(id) FROM users")
        user_count = cursor.fetchone()[0]

        if user_count == 0:
            print("Users table is empty. Inserting mock data with HASHED passwords...")
            # Mock users with emails and placeholder hashes
            hashed_password = bcrypt.generate_password_hash('password123').decode('utf-8')
            mock_users = [
                ('owner01', 'owner@workbuddy.pro', 'Owner User', hashed_password, 'Owner'),
                ('foremanA', 'alice@workbuddy.pro', 'Foreman Alice', hashed_password, 'Foreman'),
                ('workerX', 'bob@workbuddy.pro', 'Worker Bob', hashed_password, 'Worker'),
                ('workerY', 'carol@workbuddy.pro', 'Worker Carol', hashed_password, 'Worker')
            ]
            cursor.executemany("INSERT INTO users (id, email, name, password_hash, role) VALUES (?, ?, ?, ?, ?)", mock_users)
            print(f"-> {len(mock_users)} mock users inserted.")

            # Mock projects
            mock_projects = [
                ('proj_alpha', 'Project Alpha - Downtown Renovation', 'Complete renovation of the old library building.'),
                ('proj_beta', 'Site Beta - Highway Expansion', 'Phase 2 of the western highway expansion.'),
                ('proj_gamma', 'Project Gamma - New Park Development', 'Landscaping and construction for the new city park.')
            ]
            cursor.executemany("INSERT INTO projects (id, name, description) VALUES (?, ?, ?)", mock_projects)
            print(f"-> {len(mock_projects)} mock projects inserted.")

            db.commit() # CRUCIAL: This commits the data insertion transaction to the database.
            print("-> Mock data committed to database.")
        else:
            print("Users table is not empty. Skipping mock data insertion.")

@app.route('/')
def home_page():
    # The new home page will be the login page
    return render_template('login.html')

@app.route('/login', methods=['POST']) # This route now only accepts POST requests
def login_route():
    # If the mobile app sends JSON, use request.json. If it sends form data, use request.form.
    # Let's assume the client will send JSON.
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400 # Bad Request

    db = get_db()
    user_cursor = db.execute("SELECT * FROM users WHERE email = ?", (email,))
    user_data = user_cursor.fetchone()

    # Securely check the password hash
    if user_data and bcrypt.check_password_hash(user_data['password_hash'], password):
        user = dict(user_data)
        # CRITICAL: Never send the password hash back to the client
        user.pop('password_hash', None)

        # Store user info in the server-side session
        session.clear()
        session['current_user'] = user

        # Return a success response with user data
        return jsonify({"success": True, "user": user}), 200
    else:
        # Return an error response for invalid credentials
        return jsonify({"error": "Invalid email or password."}), 401 # Unauthorized

@app.route('/logout')
def logout_route():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('home_page'))

# In app.py, add this route, for example, after your /logout route

@app.route('/register', methods=['GET', 'POST'])
def register_route():
    if request.method == 'POST':
        # In a real invite system, we'd validate a unique invite token first.
        # For now, we'll let anyone register via this page for development purposes.
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        role = request.form.get('role', 'Worker') # Default new users to 'Worker' role

        # --- Validation ---
        if not all([email, name, password, password_confirm]):
            flash("All fields are required.", "error")
            return redirect(url_for('register_route'))
        if password != password_confirm:
            flash("Passwords do not match.", "error")
            return redirect(url_for('register_route'))

        db = get_db()
        # Check if user already exists
        user_exists = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if user_exists:
            flash("An account with this email already exists.", "error")
            return redirect(url_for('register_route'))

        # --- Create User ---
        # Generate a secure password hash
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        # Generate a simple unique ID for the user
        user_id = name.lower().replace(" ", "") + str(db.execute("SELECT COUNT(*) FROM users").fetchone()[0] + 1)


        try:
            db.execute(
                "INSERT INTO users (id, email, name, password_hash, role) VALUES (?, ?, ?, ?, ?)",
                (user_id, email, name, hashed_password, role)
            )
            db.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login_route'))
        except sqlite3.IntegrityError:
            db.rollback()
            flash("An account with this email or ID already exists.", "error")
            return redirect(url_for('register_route'))
        except Exception as e:
            db.rollback()
            print(f"Error during registration: {e}")
            flash("An unexpected error occurred during registration.", "error")
            return redirect(url_for('register_route'))

    # For a GET request, just show the registration page
    return render_template('register.html')

# ... (keep existing project and task routes) ...
@app.route('/select_user/<user_id>')
def select_user_route(user_id):
    db = get_db()
    user_cursor = db.execute("SELECT id, name, role FROM users WHERE id = ?", (user_id,))
    user = user_cursor.fetchone()
    if user:
        session['current_user'] = dict(user) # Store user details in session
        return redirect(url_for('project_select_page'))
    else:
        # Handle case where user_id is invalid (e.g., redirect back to user selection with an error)
        return redirect(url_for('user_select_page'))

@app.route('/api/v1/projects', methods=['GET'])
def get_projects_api():
    if 'current_user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db()
    projects_cursor = db.execute("SELECT id, name, description FROM projects ORDER BY name")
    projects = [dict(row) for row in projects_cursor.fetchall()]
    return jsonify(projects)

@app.route('/projects')
def project_select_page():
    if 'current_user' not in session:
        return redirect(url_for('user_select_page')) # Redirect if no user selected

    db = get_db()
    projects_cursor = db.execute("SELECT id, name, description FROM projects ORDER BY name")
    projects = projects_cursor.fetchall()

    current_user_name = session['current_user']['name']
    current_user_role = session['current_user']['role']

    return render_template('project_select.html',
                           projects=projects,
                           user_name=current_user_name,
                           user_role=current_user_role)

@app.route('/select_project/<project_id>')
def select_project_route(project_id):
    if 'current_user' not in session:
        return redirect(url_for('user_select_page'))

    db = get_db()
    project_cursor = db.execute("SELECT id, name FROM projects WHERE id = ?", (project_id,))
    project = project_cursor.fetchone()

    if project:
        session['current_project'] = dict(project) # Store project details in session
        # Redirect to a tasks page specific to this project
        return redirect(url_for('tasks_page_for_project', project_id=project_id))
    else:
        # Handle invalid project_id
        return redirect(url_for('project_select_page'))

# Updated tasks page route to be project-specific
@app.route('/project/<project_id>/tasks')
def tasks_page_for_project(project_id):
    # This part checks for valid session context
    if 'current_user' not in session or 'current_project' not in session or session['current_project']['id'] != project_id:
        session.pop('current_project', None)
        return redirect(url_for('project_select_page'))

    db = get_db()

    # <<< THIS PART FETCHES THE USERS FOR THE DROPDOWN >>>
    # It should be present in this function.
    users_cursor = db.execute("SELECT id, name, role FROM users ORDER BY name")
    assignable_users = users_cursor.fetchall()

    current_user = session.get('current_user')
    current_project = session.get('current_project')

    # <<< ENSURE 'assignable_users=assignable_users' IS IN THE RETURN STATEMENT >>>
    return render_template('index.html',
                           user=current_user,
                           project=current_project,
                           assignable_users=assignable_users)# Add this new route to app.py

# In app.py, add this new section for Chat API Endpoints

# --- Chat API Endpoints ---

@app.route('/api/v1/chat/<conversation_id>/messages', methods=['GET'])
def get_messages(conversation_id):
    # Security check: Ensure user is logged in
    if 'current_user' not in session:
        return jsonify({"error": "Unauthorized - User not logged in"}), 401

    # Security check (conceptual): In a real app, we'd also verify this user
    # is allowed to be in this conversation_id (e.g., is a member of the project for a channel,
    # or one of the two users in a DM). We'll keep it simple for this prototype.

    db = get_db()
    messages_cursor = db.execute(
        """
SELECT m.id, m.conversation_id, m.user_id, u.name as user_name, m.message_text, m.created_at
FROM messages m
JOIN users u ON m.user_id = u.id
WHERE m.conversation_id = ?
ORDER BY m.created_at ASC
        """,
        (conversation_id,)
    )
    messages = [dict(row) for row in messages_cursor.fetchall()]
    return jsonify(messages)


@app.route('/api/v1/chat/<conversation_id>/messages', methods=['POST'])
def post_message(conversation_id):
    # Security checks
    if 'current_user' not in session:
        return jsonify({"error": "Unauthorized - User not logged in"}), 401
    # ... (add conceptual check here that user is allowed to post to this conversation) ...

    data = request.json
    message_text = data.get('message_text')
    user_id = session['current_user']['id']

    if not message_text or not message_text.strip():
        return jsonify({"error": "Message text cannot be empty"}), 400

    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO messages (conversation_id, user_id, message_text) VALUES (?, ?, ?)",
            (conversation_id, user_id, message_text.strip())
        )
        db.commit()
        new_message_id = cursor.lastrowid

        # Fetch the newly created message to return to the client
        new_message_cursor = db.execute(
            """
SELECT m.id, m.conversation_id, m.user_id, u.name as user_name, m.message_text, m.created_at
FROM messages m
JOIN users u ON m.user_id = u.id
WHERE m.id = ?
            """,
            (new_message_id,)
        )
        created_message = dict(new_message_cursor.fetchone())
        return jsonify(created_message), 201

    except sqlite3.Error as e:
        db.rollback()
        print(f"Database error in post_message: {e}")
        return jsonify({"error": "Database error occurred while posting message."}), 500

@app.route('/project/<project_id>/chat')
def chat_hub_page(project_id):
    if 'current_user' not in session or session.get('current_project', {}).get('id') != project_id:
        return redirect(url_for('project_select_page'))

    db = get_db()
    # Fetch all users in the project/company to list them for potential DMs
    users_cursor = db.execute("SELECT id, name, role FROM users ORDER BY name")
    users = users_cursor.fetchall()

    # For this prototype, we'll define some mock channels here.
    # In a real app, this would come from the database.
    mock_channels = [
        {'name': '# general', 'last_message': 'Welcome to the project!'},
        {'name': '# materials-and-supplies', 'last_message': 'Remember to log all receipts.'}
    ]

    current_user = session.get('current_user')
    current_project = session.get('current_project')

    return render_template('chat_hub.html',
                           user=current_user,
                           project=current_project,
                           channels=mock_channels,
                           dm_users=users)

@app.route('/project/<project_id>/chat/<chat_name>')
def chat_room_page(project_id, chat_name):
    # Security checks to ensure user is logged in and part of the project
    if 'current_user' not in session or session.get('current_project', {}).get('id') != project_id:
        return redirect(url_for('project_select_page'))

    current_user = session.get('current_user')
    current_project = session.get('current_project')

    # For this prototype, we're just passing the name. A real app would use IDs and fetch chat history.
    return render_template('chat_room.html',
                           user=current_user,
                           project=current_project,
                           chat_name=chat_name)

@app.route('/api/project/<project_id>/tasks', methods=['GET'])
def get_tasks(project_id):
    if 'current_user' not in session or session.get('current_project', {}).get('id') != project_id:
        return jsonify({"error": "Unauthorized or project not selected"}), 401

    db = get_db()
    tasks_cursor = db.execute(
    """
    SELECT t.id, t.title, t.description, t.is_completed, t.due_date, t.priority,
           t.user_id as creator_id, u_creator.name as creator_name,
           t.assignee_id, u_assignee.name as assignee_name
    FROM tasks t
    JOIN users u_creator ON t.user_id = u_creator.id
    LEFT JOIN users u_assignee ON t.assignee_id = u_assignee.id
    WHERE t.project_id = ?
    ORDER BY t.created_at DESC
    """,
    (project_id,)
    )
    tasks = [dict(row) for row in tasks_cursor.fetchall()]
    return jsonify(tasks)

@app.route('/api/project/<project_id>/tasks', methods=['POST'])
def add_task_api(project_id):
    # Check 1: Is there a current_user in the session?
    if 'current_user' not in session:
        print("Error in add_task_api: 'current_user' not found in session.")
        return jsonify({"error": "User not logged in or session expired"}), 401

    current_user_data = session.get('current_user')
    # Check 2: Does the current_user data have an 'id'?
    if not current_user_data or 'id' not in current_user_data:
        print("Error in add_task_api: 'id' not found in current_user_data from session.")
        return jsonify({"error": "User ID not found in session"}), 401

    creator_id = current_user_data['id'] # This is the user_id of the creator

    # Check 3: Is there a current_project in session and does it match the URL's project_id?
    current_project_data = session.get('current_project')
    if not current_project_data or current_project_data.get('id') != project_id:
        print(f"Error in add_task_api: Project context mismatch. Session project: {current_project_data.get('id') if current_project_data else 'None'}, URL project_id: {project_id}")
        return jsonify({"error": "Project context mismatch or project not selected"}), 401

    new_task_data = request.json
    title = new_task_data.get('title')
    description = new_task_data.get('description', '')
    due_date = new_task_data.get('due_date')
    priority = new_task_data.get('priority', 'Medium') # Default priority if not provided
    assignee_id = new_task_data.get('assignee_id')

    if not title or title.strip() == "": # Ensure title is not empty
        return jsonify({"error": "Title is required"}), 400

    # If no assignee_id is provided from the frontend, default to self-assign (assign to the creator)
    if not assignee_id:
        assignee_id = creator_id

    db = get_db()
    try:
        cursor = db.execute(
            """INSERT INTO tasks (title, description, project_id, user_id, due_date, priority, assignee_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (title.strip(), description.strip(), project_id, creator_id, due_date, priority, assignee_id)
        )
        db.commit()
        new_task_id = cursor.lastrowid

        # Fetch the newly created task along with creator and assignee names to return to client
        created_task_cursor = db.execute(
             """
            SELECT t.id, t.title, t.description, t.is_completed, t.due_date, t.priority,
                   t.user_id as creator_id, u_creator.name as creator_name,
                   t.assignee_id, u_assignee.name as assignee_name
            FROM tasks t
            JOIN users u_creator ON t.user_id = u_creator.id
            LEFT JOIN users u_assignee ON t.assignee_id = u_assignee.id
            WHERE t.id = ?
            """, (new_task_id,))
        created_task_data = created_task_cursor.fetchone()

        if not created_task_data:
            print(f"Error in add_task_api: Failed to retrieve task with id {new_task_id} after insertion.")
            return jsonify({"error": "Failed to retrieve newly created task"}), 500

        created_task = dict(created_task_data)
        return jsonify(created_task), 201

    except sqlite3.Error as e:
        db.rollback() # Rollback any changes if a database error occurs
        print(f"Database error in add_task_api for project {project_id}: {e}")
        return jsonify({"error": "Database error occurred while adding task."}), 500
    except Exception as e:
        db.rollback() # Rollback on any other unexpected error
        print(f"Unexpected error in add_task_api for project {project_id}: {e}")
        return jsonify({"error": "An unexpected error occurred."}), 500

# toggle_task_api and delete_task_api don't necessarily need changes for due_date viewing/adding,
# unless we wanted to add functionality to UPDATE the due_date.
# For now, we'll just add it on creation and display it.

# ... (keep existing toggle_task_api, delete_task_api, and other routes, and main execution block) ...
# Ensure your init_db() function is still present and correct in app.py
# The main execution block should re-run init_db() if the database is new/empty

@app.route('/api/tasks/<int:task_id>/toggle_complete', methods=['PUT'])
def toggle_task_api(task_id):
    if 'current_user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    # Check if task exists and belongs to a project the user has access to (simplified for now)
    db = get_db()
    task_cursor = db.execute("SELECT is_completed, project_id FROM tasks WHERE id = ?", (task_id,))
    task = task_cursor.fetchone()

    if not task:
        return jsonify({"error": "Task not found"}), 404

    # Ensure the task's project matches current project in session (important for security)
    if session.get('current_project', {}).get('id') != task['project_id']:
        return jsonify({"error": "Task does not belong to current project"}), 403


    new_status = not task['is_completed']
    db.execute("UPDATE tasks SET is_completed = ? WHERE id = ?", (1 if new_status else 0, task_id))
    db.commit()

    updated_task_cursor = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    updated_task = dict(updated_task_cursor.fetchone())
    return jsonify(updated_task)

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task_api(task_id):
    if 'current_user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db()
    task_cursor = db.execute("SELECT project_id FROM tasks WHERE id = ?", (task_id,))
    task = task_cursor.fetchone()

    if not task:
        return jsonify({"error": "Task not found"}), 404

    if session.get('current_project', {}).get('id') != task['project_id']:
        return jsonify({"error": "Task does not belong to current project"}), 403

    db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    db.commit()
    return jsonify({"message": "Task deleted successfully"}), 200

# ... (keep existing imports, Flask app setup, DB functions, existing routes etc.) ...

# --- Comment API Endpoints ---

# In app.py, add this new section for Comment API Endpoints

# --- Comment API Endpoints ---

@app.route('/api/task/<int:task_id>/comments', methods=['GET'])
def get_comments_for_task(task_id):
    if 'current_user' not in session:
        return jsonify({"error": "Unauthorized - User not logged in"}), 401

    current_project_id = session.get('current_project', {}).get('id')
    db = get_db()

    # Security Check: Verify the requested task belongs to the user's current project
    task_check_cursor = db.execute("SELECT id FROM tasks WHERE id = ? AND project_id = ?", (task_id, current_project_id))
    if task_check_cursor.fetchone() is None:
        return jsonify({"error": "Unauthorized - Task not found in current project"}), 403

    # Fetch comments, joining with the users table to get the commenter's name
    comments_cursor = db.execute(
        """
        SELECT c.id, c.task_id, c.user_id, u.name as user_name, c.comment_text, c.created_at
        FROM comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.task_id = ?
        ORDER BY c.created_at ASC
        """,
        (task_id,)
    )
    comments = [dict(row) for row in comments_cursor.fetchall()]
    return jsonify(comments)

@app.route('/api/task/<int:task_id>/comments', methods=['POST'])
def add_comment_to_task(task_id):
    if 'current_user' not in session:
        return jsonify({"error": "Unauthorized - User not logged in"}), 401

    current_project_id = session.get('current_project', {}).get('id')
    db = get_db()

    # Security Check: Verify the task belongs to the current project
    task_check_cursor = db.execute("SELECT id FROM tasks WHERE id = ? AND project_id = ?", (task_id, current_project_id))
    if task_check_cursor.fetchone() is None:
        return jsonify({"error": "Unauthorized - Task not found in current project"}), 403

    comment_data = request.json
    comment_text = comment_data.get('comment_text')
    user_id = session['current_user']['id']

    if not comment_text or comment_text.strip() == "":
        return jsonify({"error": "Comment text cannot be empty"}), 400

    try:
        cursor = db.execute(
            "INSERT INTO comments (task_id, user_id, comment_text) VALUES (?, ?, ?)",
            (task_id, user_id, comment_text.strip())
        )
        db.commit()
        new_comment_id = cursor.lastrowid

        # Fetch the newly created comment to return to the client
        new_comment_cursor = db.execute(
            """
            SELECT c.id, c.task_id, c.user_id, u.name as user_name, c.comment_text, c.created_at
            FROM comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.id = ?
            """,
            (new_comment_id,)
        )
        created_comment = dict(new_comment_cursor.fetchone())
        return jsonify(created_comment), 201

    except sqlite3.Error as e:
        db.rollback()
        print(f"Database error in add_comment_to_task: {e}")
        return jsonify({"error": "Database error occurred while adding comment."}), 500


@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task_api(task_id):
    if 'current_user' not in session:
        return jsonify({"error": "Unauthorized - User not logged in"}), 401

    # Ensure task belongs to a project the user has access to (via current_project in session)
    current_project_id = session.get('current_project', {}).get('id')
    if not current_project_id:
        return jsonify({"error": "Unauthorized - No project selected"}), 401

    db = get_db()
    # Verify the task exists and belongs to the current project
    task_check_cursor = db.execute("SELECT id FROM tasks WHERE id = ? AND project_id = ?", (task_id, current_project_id))
    if task_check_cursor.fetchone() is None:
        return jsonify({"error": "Task not found or not in current project"}), 404 # Or 403

    updated_task_data = request.json
    # Get all fields that can be updated
    title = updated_task_data.get('title')
    description = updated_task_data.get('description')
    due_date = updated_task_data.get('due_date')
    priority = updated_task_data.get('priority')
    assignee_id = updated_task_data.get('assignee_id')
    # is_completed is handled by toggle_complete for now, but could be included here too.

    if not title or title.strip() == "":
        return jsonify({"error": "Title cannot be empty"}), 400

    # If assignee_id is empty string from frontend, set to NULL or current user.
    # For now, let's assume frontend sends a valid user ID or NULL.
    # If assignee_id comes as empty string, SQLite might store it as empty string.
    # Better to explicitly set to NULL if desired, or handle in client-side.
    # For simplicity, we'll trust the client sends a valid user ID or None/empty if unassigning.
    # If it's an empty string and your FK allows NULLs, it's fine. If not, convert empty string to None.
    if assignee_id == "":
        assignee_id = None


    try:
        db.execute(
            """UPDATE tasks
            SET title = ?, description = ?, due_date = ?, priority = ?, assignee_id = ?
            WHERE id = ?""",
            (title.strip(), description.strip(), due_date, priority, assignee_id, task_id)
        )
        db.commit()

        updated_task_cursor = db.execute(
            """
            SELECT t.id, t.title, t.description, t.is_completed, t.due_date, t.priority,
            t.user_id as creator_id, u_creator.name as creator_name,
            t.assignee_id, u_assignee.name as assignee_name
            FROM tasks t
            JOIN users u_creator ON t.user_id = u_creator.id
            LEFT JOIN users u_assignee ON t.assignee_id = u_assignee.id
            WHERE t.id = ?
            """, (task_id,)) # Re-fetch the task to include assignee_name
        updated_task = dict(updated_task_cursor.fetchone())
        return jsonify(updated_task)

    except sqlite3.Error as e:
        db.rollback()
        print(f"Database error in update_task_api for task {task_id}: {e}")
        return jsonify({"error": "Database error occurred while updating task."}), 500
    except Exception as e:
        db.rollback()
        print(f"Unexpected error in update_task_api for task {task_id}: {e}")
        return jsonify({"error": "An unexpected error occurred."}), 500
# ... (ensure this is before your if __name__ == '__main__': block) ...

if __name__ == '__main__':
    # Ensure init_db is called if the DB/tables are not set up
    # This simple check can be improved (e.g., using Flask CLI command for init-db)
    import os
    if not os.path.exists(DATABASE):
        print("Database not found, initializing...")
        init_db()
    else: # Basic check if tables exist even if file exists
        with app.app_context():
            conn = get_db()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
                if cursor.fetchone() is None:
                    print("Tables not found, re-initializing database...")
                    init_db()
                else:
                    print("Database and tables found.")
                    # Check if mock data needs to be re-inserted (optional, init_db handles this)
                    init_db()
            except Exception as e:
                print(f"Error checking tables, re-initializing: {e}")
                init_db()

    app.run(host='0.0.0.0', debug=True)