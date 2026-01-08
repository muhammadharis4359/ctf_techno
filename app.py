from flask import Flask, request, render_template, session, redirect, jsonify, send_from_directory
import os
import sqlite3
import subprocess  

app = Flask(__name__)
app.secret_key = 'secretkey'  # Use a real secret key for production

# ---------------------------
# Database Setup (SQLite)
# ---------------------------
def get_db():
    conn = sqlite3.connect('storex.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

db = get_db()
cur = db.cursor()

# Create users and products tables
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    password TEXT
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    name TEXT
)
""")

# Insert some seed data (only if they don't exist)
cur.execute("INSERT OR IGNORE INTO products (id, name) VALUES (1, 'Product 1: Awesome Product')")
cur.execute("INSERT OR IGNORE INTO products (id, name) VALUES (2, 'Product 2: Another Product')")
cur.execute("SELECT 1 FROM users WHERE username='admin'")
if not cur.fetchone():
    cur.execute("INSERT INTO users (username, password) VALUES ('admin', 'password123')")
db.commit()


# ---------------------------
# Routes
# ---------------------------

# Home route (Login Page)
@app.route('/')
def index():
    return render_template('index.html')

# SQL Injection Vulnerability (Login Route)
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    
    # Vulnerable query: Using string formatting in SQL query
    query = f"SELECT id, username FROM users WHERE username = '{username}' AND password = '{password}'"
    print(f"[DEBUG] Executing query: {query}")  # Print for debugging

    try:
        row = db.execute(query).fetchone()
    except Exception as e:
        return f"SQL error: {e}", 400

    if row:
        session['user'] = row['username']
        return redirect('/dashboard')

    return 'Invalid credentials', 401

# Dashboard route after login
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    return render_template('dashboard.html', user=session['user'])

# SQL Injection Vulnerability (Product Page)
@app.route('/product')
def product():
    product_id = request.args.get('id', '1')

    # Vulnerable query: Using string formatting in SQL query
    query = f"SELECT id, name FROM products WHERE id = {product_id}"
    print(f"[DEBUG] Executing query: {query}")  # Print for debugging

    try:
        rows = db.execute(query).fetchall()
    except Exception as e:
        return f"SQL error: {e}", 400

    if not rows:
        return "Product not found", 404

    out = "<h2>Products result</h2><ul>"
    for r in rows:
        out += f"<li>{r['id']}: {r['name']}</li>"
    out += "</ul><p><a href='/dashboard'>Back</a></p>"
    return out

# File upload (vulnerable to malicious uploads)

UPLOAD_FOLDER = './upload'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ---------------------------
# Serve files from uploads directory
# ---------------------------
@app.route('/upload/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ---------------------------
# File Upload (Python-based command execution)
# ---------------------------
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user' not in session:
        return redirect('/')

    if request.method == 'POST':
        f = request.files.get('file')
        if not f:
            return "No file", 400

        # Save uploaded file
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], f.filename)
        f.save(save_path)

        # Check if file is a Python file and execute it (simulate PHP command execution)
        if f.filename.endswith('.py'):
            # Simulating Python file execution
            try:
                result = subprocess.check_output(['python', save_path], stderr=subprocess.STDOUT, text=True)
                return f"File uploaded and executed successfully. Output: {result}<br><a href='/dashboard'>Back</a>"
            except subprocess.CalledProcessError as e:
                return f"Error executing file: {e.output}<br><a href='/dashboard'>Back</a>"
        else:
            return f"File uploaded but not executed (non-Python file).<br><a href='/dashboard'>Back</a>"

    return render_template('upload.html')


# @app.route('/upload', methods=['GET', 'POST'])
# def upload():
#     if 'user' not in session:
#         return redirect('/')

#     if request.method == 'POST':
#         f = request.files.get('file')
#         if not f:
#             return "No file", 400

#         # Save uploaded file
#         save_path = os.path.join(app.config['UPLOAD_FOLDER'], f.filename)
#         f.save(save_path)

#         # Check if file is a Python file and execute it (simulate PHP command execution)
#         if f.filename.endswith('.py'):
#             # Simulating Python file execution
#             try:
#                 result = subprocess.check_output(['python', save_path], stderr=subprocess.STDOUT, text=True)
#                 return f"File uploaded and executed successfully. Output: {result}<br><a href='/dashboard'>Back</a>"
#             except subprocess.CalledProcessError as e:
#                 return f"Error executing file: {e.output}<br><a href='/dashboard'>Back</a>"
#         else:
#             return f"File uploaded but not executed (non-Python file).<br><a href='/dashboard'>Back</a>"

#     return render_template('upload.html')



# CSRF vulnerability (No CSRF token)
@app.route('/change-password', methods=['POST'])
def change_password():
    if 'user' not in session:
        return redirect('/')

    new_password = request.form.get('new_password', '')
    db.execute(f"UPDATE users SET password = '{new_password}' WHERE username = 'admin'")
    db.commit()
    return "Password updated (admin).<br><a href='/dashboard'>Back</a>"

# OTP Vulnerability (Bypass via Burp Suite)
@app.route('/otp', methods=['POST'])
def otp():
    otp_val = request.form.get('otp')
    if otp_val == '123456':  # Hardcoded OTP
        return jsonify({"message": "OTP validated successfully!", "flag": "CTF{hidden_flag}"})
    return "Invalid OTP", 400

# Logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ---------------------------
# Main block
# ---------------------------
if __name__ == '__main__':
    # Ensure uploads directory exists
    if not os.path.exists('/upload'):
        os.makedirs('/upload')

    # Set the correct config for uploads folder
    app.config['UPLOAD_FOLDER'] = '/upload'

    app.run(debug=True, host='0.0.0.0', port=5000)
