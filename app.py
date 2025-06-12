# In app.py - NEW VERSION USING SQLAlchemy and PostgreSQL

import os
from flask import Flask, request, jsonify, session, flash, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError
import uuid # For generating user IDs

# --- App Initialization ---
app = Flask(__name__)
# IMPORTANT: This will be set from an environment variable in production
# For local dev, we can set it directly for now if we don't use a .env file
# The URL you copied from Supabase goes here.
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:GfjYpfc03onizwZU@db.yoboblatndnmcxvkzblc.supabase.co:5432/postgres')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://postgres.yoboblatndnmcxvkzblc:GfjYpfc03onizwZU@aws-0-ca-central-1.pooler.supabase.com:5432/postgres')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_very_secret_key_here'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# --- Database Models (Defines our tables as Python classes) ---

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
    owner_id = db.Column(db.Text, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())
    updated_at = db.Column(db.TIMESTAMP, server_default=db.func.now(), onupdate=db.func.now())

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

# ... We would also add models for Comments and Messages here ...

# --- Helper function to create/reset the database ---
@app.cli.command('init-db')
def init_db_command():
    """Creates the database tables and seeds initial data."""
    db.drop_all()
    db.create_all()

    # Seed mock data
    hashed_password = bcrypt.generate_password_hash('password123').decode('utf-8')
    # ... Create and add mock users and projects using the new class structure ...
    owner = User(id='owner01', email='owner@workbuddy.pro', name='Owner User', password_hash=hashed_password, role='Owner')
    project_alpha = Project(id='proj_alpha', name='Project Alpha - Downtown Renovation', owner_id='owner01')
    db.session.add(owner)
    db.session.add(project_alpha)

    db.session.commit()
    print('Initialized the database and seeded mock data.')

# In app.py

# ... (keep all your existing imports, app setup, db setup, and Models) ...

# <<< ADD THIS NEW DEBUGGING ROUTE >>>
@app.route('/test-db')
def test_db_connection():
    try:
        # Try to perform a simple query to confirm the connection works
        user_count = db.session.query(User).count()
        # If the above line works, the connection is good.
        return f"SUCCESS: Successfully connected to the database. Found {user_count} users."
    except Exception as e:
        # If it fails, print the exact error to the Render logs and return it in the browser
        print(f"--- DATABASE CONNECTION ERROR ---")
        print(str(e))
        print(f"--- END DATABASE CONNECTION ERROR ---")
        return f"Failed to connect to the database. The specific error is: <pre>{e}</pre>", 500

# <<< MODIFY YOUR EXISTING /login ROUTE TO ADD LOGGING >>>
@app.route('/login', methods=['POST'])
def login_route():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    print(f"Login attempt received for email: {email}") # Log the attempt

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    try:
        user = User.query.filter_by(email=email).first()
    except Exception as e:
        print(f"Error querying database for user '{email}': {e}")
        return jsonify({"error": "A database error occurred during login."}), 500

    if user and bcrypt.check_password_hash(user.password_hash, password):
        print(f"Login successful for user: {email}")
        user_data = {'id': user.id, 'name': user.name, 'email': user.email, 'role': user.role}
        session['current_user'] = user_data
        return jsonify({"success": True, "user": user_data}), 200
    else:
        print(f"Login failed for user: {email}. User found in DB: {user is not None}")
        return jsonify({"error": "Invalid email or password."}), 401

# ... (rest of your app.py) ...

if __name__ == '__main__':
    # When running locally, you'd first run `flask init-db` in your terminal
    # Then you'd run the app
    app.run(host='0.0.0.0', debug=True)
