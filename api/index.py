from flask import Flask, render_template, request, jsonify, make_response, redirect, url_for, session
from supabase import create_client
from datetime import datetime
import os
import uuid

app = Flask(__name__,
    template_folder='../templates',
    static_folder='../static',
    static_url_path='/static'
)

# Add secret key for session management
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24).hex())

# Supabase configuration
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

# Add error checking for Supabase credentials
if not supabase_url or not supabase_key:
    print("Warning: Supabase credentials are not set!")

supabase = create_client(supabase_url, supabase_key)

@app.route('/')
def index():
    # Check if user is authenticated
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    response = make_response(render_template('index.html', 
        title="Gothic Stopwatch",
        panel_title="Tasks of the Night"
    ))
    return response

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            # Store user session
            session['user_id'] = response.user.id
            return redirect(url_for('index'))
        except Exception as e:
            return render_template('login.html', 
                error="Invalid credentials",
                title="Gothic Login"
            )
    return render_template('login.html', title="Gothic Login")

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            response = supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            return redirect(url_for('login'))
        except Exception as e:
            return render_template('signup.html', 
                error="Signup failed",
                title="Gothic Signup"  # Keep gothic theme in signup
            )
    return render_template('signup.html', title="Gothic Signup")

@app.route('/logout')
def logout():
    try:
        supabase.auth.sign_out()
        # Clear session
        session.clear()
        response = make_response(redirect(url_for('login')))
        return response
    except Exception as e:
        return redirect(url_for('index'))

@app.route("/log_time", methods=["POST"])
def log_time():
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid request format"}), 400

        data = request.json
        if not all(key in data for key in ["startTime", "endTime", "duration"]):
            return jsonify({"error": "Missing required fields"}), 400

        # Get user from session
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401
        
        time_log = {
            "start_time": datetime.fromtimestamp(data["startTime"] / 1000).isoformat(),
            "end_time": datetime.fromtimestamp(data["endTime"] / 1000).isoformat(),
            "date": datetime.now().date().isoformat(),
            "duration": data["duration"],
            "user_id": user_id  # Changed from device_id to user_id
        }
        
        print(f"Attempting to log time: {time_log}")
        result = supabase.table('time_logs').insert(time_log).execute()
        return jsonify({"success": True, "data": result.data})
    except Exception as e:
        print(f"Error in log_time: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/get_logs")
def get_logs():
    try:
        # Get user from session
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"logs": [], "stats": []})
            
        # Get all logs for the user
        result = supabase.table('time_logs')\
            .select("*")\
            .eq('user_id', user_id)\
            .order('start_time', desc=True)\
            .execute()
        
        logs = result.data

        # Calculate daily statistics
        daily_stats = {}
        for log in logs:
            date = log['date']
            if date not in daily_stats:
                daily_stats[date] = {
                    'date': date,
                    'total_duration': 0,
                    'sessions': 0
                }
            daily_stats[date]['total_duration'] += log['duration']
            daily_stats[date]['sessions'] += 1

        # Convert stats to list and sort by date
        stats = sorted(daily_stats.values(), key=lambda x: x['date'], reverse=True)
        
        return jsonify({
            "logs": logs,
            "stats": stats
        })
    except Exception as e:
        print(f"Error in get_logs: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
