from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from supabase import create_client
from datetime import datetime, timedelta
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24).hex())

# Supabase configuration
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)

# Configure session to use filesystem
app.config['SESSION_TYPE'] = 'filesystem'
app.permanent_session_lifetime = timedelta(days=30)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember')
        
        try:
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            session['user'] = {
                'id': auth_response.user.id,
                'email': auth_response.user.email
            }
            
            # Set session permanent if remember me is checked
            if remember:
                session.permanent = True
                app.permanent_session_lifetime = timedelta(days=30)
            
            return redirect(url_for('index'))
        except Exception as e:
            flash('Invalid login credentials', 'error')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            auth_response = supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            flash('Please check your email to verify your account')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Error creating account')
            return render_template('signup.html')
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route("/log_time", methods=["POST"])
@login_required
def log_time():
    try:
        data = request.json
        time_log = {
            "start_time": datetime.fromtimestamp(data["startTime"] / 1000).isoformat(),
            "end_time": datetime.fromtimestamp(data["endTime"] / 1000).isoformat(),
            "date": datetime.now().date().isoformat(),
            "duration": data["duration"],  # This is now in seconds
            "user_id": session['user']['id']
        }
        
        result = supabase.table('time_logs').insert(time_log).execute()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error logging time: {str(e)}")  # Add logging for debugging
        return jsonify({"error": str(e)}), 500

@app.route("/get_logs")
@login_required
def get_logs():
    try:
        result = supabase.table('time_logs')\
            .select("*")\
            .eq('user_id', session['user']['id'])\
            .order('created_at', desc=True)\
            .execute()
        
        return jsonify(result.data)
    except Exception as e:
        print(f"Error getting logs: {str(e)}")  # Add logging for debugging
        return jsonify({"error": str(e)}), 500

# Health check endpoint for Vercel
@app.route("/health")
def health_check():
    try:
        # Test database connection
        supabase.table('time_logs').select("count(*)").execute()
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
