# In a new file named connection_test.py

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

# --- App Initialization ---
app = Flask(__name__)

# --- Configuration ---
# This will read the DATABASE_URL you set in the Render environment variables.
# It includes a default value for local testing, but the Render env var will override it.
DATABASE_CONNECTION_URI = os.environ.get(
    'DATABASE_URL',
    'YOUR_SUPABASE_CONNECTION_URL_WITH_SSLMODE_GOES_HERE'
)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_CONNECTION_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# --- Main and Only Route ---
@app.route('/')
def test_db_connection():
    """
Tries to connect to the database and run a simple query.
Returns a success or failure message.
    """
    try:
        # The 'with app.app_context()' is important for running DB operations in Flask
        with app.app_context():
            # Use SQLAlchemy's engine to perform a raw, simple query.
            # 'SELECT 1' is a standard way to check if a DB connection is alive.
            db.session.execute(text('SELECT 1'))

        # If the line above doesn't throw an error, the connection is good.
        print("SUCCESS: Database connection test was successful.")
        return "SUCCESS: Successfully connected to the database."

    except Exception as e:
        # If any error occurs during connection or query, we print it and return it.
        print(f"--- DATABASE CONNECTION FAILED ---")
        print(f"ERROR: {e}")
        print(f"--- END OF ERROR ---")
        return f"DATABASE CONNECTION FAILED.<br><br>ERROR: <pre>{e}</pre>", 500

if __name__ == '__main__':
    # This part is for running locally for a quick test if you want.
    # The production server will use Gunicorn.
    app.run(host='0.0.0.0', debug=True)