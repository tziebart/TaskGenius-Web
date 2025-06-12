import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import uuid

# --- This script is for a ONE-TIME setup of your remote Supabase DB ---

# Create a temporary Flask app instance to establish an application context
app = Flask(__name__)

# --- IMPORTANT: Paste your full Supabase Connection URL here ---
# It's okay to hardcode it here for this one-time setup script since you won't commit it to Git.
# Make sure to replace the password placeholder with your actual DB password.
# Example: 'postgresql://postgres:your_db_password@db.xyz.supabase.co:5432/postgres'
SUPABASE_URL = 'postgresql://postgres:GfjYpfc03onizwZU@db.yoboblatndnmcxvkzblc.supabase.co:5432/postgres'

app.config['SQLALCHEMY_DATABASE_URI'] = SUPABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)


# --- Copy the Database Models from your app.py ---
# This ensures the script knows what tables to create.
# (This is a simplified version; in a real project, models would be in their own file to be imported by both apps)

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

# We need to add all the models we've defined in schema.sql
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

class ProjectMember(db.Model):
    __tablename__ = 'project_members'
    project_id = db.Column(db.Text, db.ForeignKey('projects.id', ondelete='CASCADE'), primary_key=True)
    user_id = db.Column(db.Text, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)


# --- Main function to set up the database ---
# In setup_database.py, replace the setup_database() function with this complete version:

def setup_database():
    with app.app_context():
        print("Connecting to remote database and dropping all existing tables...")
        db.drop_all() # Ensures a clean slate
        print("Creating all new tables...")
        db.create_all() # Creates tables based on the Models defined above
        print("Tables created successfully.")

        print("Seeding database with mock data...")
        hashed_password = bcrypt.generate_password_hash('password123').decode('utf-8')

        # --- Step 1: Create and COMMIT Users FIRST ---
        owner = User(id='owner01', email='owner@workbuddy.pro', name='Owner User', password_hash=hashed_password, role='Owner')
        foreman = User(id='foremanA', email='alice@workbuddy.pro', name='Foreman Alice', password_hash=hashed_password, role='Foreman')
        worker1 = User(id='workerX', email='bob@workbuddy.pro', name='Worker Bob', password_hash=hashed_password, role='Worker')
        worker2 = User(id='workerY', email='carol@workbuddy.pro', name='Worker Carol', password_hash=hashed_password, role='Worker')

        db.session.add_all([owner, foreman, worker1, worker2])
        db.session.commit() # <-- Commit the users to the database
        print(f"-> {db.session.query(User).count()} mock users committed.")

        # --- Step 2: Create and COMMIT Projects SECOND ---
        # Now that the 'owner01' user exists in the database, we can create projects owned by them.
        project_alpha = Project(id='proj_alpha', name='Project Alpha - Downtown Renovation', description='Complete renovation of the old library building.', owner_id='owner01')
        project_beta = Project(id='proj_beta', name='Site Beta - Highway Expansion', description='Phase 2 of the western highway expansion.', owner_id='owner01')

        db.session.add_all([project_alpha, project_beta])
        db.session.commit() # <-- Commit the projects to the database
        print(f"-> {db.session.query(Project).count()} mock projects committed.")

        # --- Step 3: Create and COMMIT Project Members THIRD ---
        # Now that users and projects exist, we can link them.
        member1 = ProjectMember(project_id='proj_alpha', user_id='owner01')
        member2 = ProjectMember(project_id='proj_alpha', user_id='foremanA')
        member3 = ProjectMember(project_id='proj_alpha', user_id='workerX')

        db.session.add_all([member1, member2, member3])
        db.session.commit() # <-- Commit the project memberships
        print(f"-> {db.session.query(ProjectMember).count()} project members committed.")

        print("\nDatabase setup is complete!")
        
if __name__ == '__main__':
    # This ensures your libraries are installed before running
    print("Ensure you have run 'pip install -r requirements.txt'")
    setup_database()