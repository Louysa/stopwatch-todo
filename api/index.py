from flask import Flask, render_template, request, jsonify, make_response, redirect, url_for, session, flash
from supabase import create_client
from datetime import datetime
import os
import uuid
from functools import wraps

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

def get_supabase():
    """Get a new Supabase client instance"""
    return create_client(
        supabase_url,
        supabase_key
    )

def get_authenticated_supabase():
    """Get a Supabase client instance with current session"""
    client = create_client(
        supabase_url,
        supabase_key
    )
    
    # Set the session if we have one
    if session.get('access_token'):
        try:
            client.auth.set_session(session['access_token'], session.get('refresh_token'))
            print(f"Session set successfully with access token: {session['access_token'][:10]}...")
        except Exception as e:
            print(f"Error setting session: {str(e)}")
            # Clear invalid session
            session.clear()
            return None
    
    return client

# Initialize base Supabase client without session
supabase = get_supabase()

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
            # Get a fresh Supabase client
            current_supabase = get_supabase()
            response = current_supabase.auth.sign_in_with_password({
                'email': email,
                'password': password
            })
            
            if response.user:
                # Store user ID and session in session
                session['user_id'] = response.user.id
                session['email'] = response.user.email
                session['access_token'] = response.session.access_token
                session['refresh_token'] = response.session.refresh_token
                print(f"User logged in successfully: {response.user.id}")
                
                return redirect(url_for('index'))
            else:
                flash('Invalid email or password')
        except Exception as e:
            print(f"Login error: {str(e)}")
            flash('Invalid email or password')
    
    return render_template('login.html')

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

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401
            
        print(f"Fetching tasks for user: {user_id}")
        response = supabase.table('tasks').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
        return jsonify(response.data)
    except Exception as e:
        print(f"Error in get_tasks: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks', methods=['POST'])
def create_task():
    try:
        user_id = session.get('user_id')
        if not user_id:
            print("No user_id in session")
            return jsonify({'error': 'User not authenticated'}), 401

        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'Task text is required'}), 400

        print(f"Creating task for user {user_id}: {data['text']}")
        
        # Create task for the current user
        task_data = {
            'user_id': user_id,
            'text': data['text'],
            'completed': False
        }
        
        # Use the global supabase client since RLS is disabled
        print(f"Task data being sent to Supabase: {task_data}")
        
        try:
            response = supabase.table('tasks').insert(task_data).execute()
            print(f"Supabase response: {response}")
            
            if not response.data:
                print("No data returned from Supabase insert")
                return jsonify({'error': 'Failed to create task'}), 500
                
            print(f"Task created successfully: {response.data[0]}")
            return jsonify(response.data[0])
        except Exception as e:
            print(f"Supabase insert error: {str(e)}")
            raise e
            
    except Exception as e:
        print(f"Error in create_task: {str(e)}")
        return jsonify({
            'error': str(e),
            'details': getattr(e, 'details', None),
            'hint': getattr(e, 'hint', None),
            'code': getattr(e, 'code', None)
        }), 500

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        print(f"Updating task {task_id} for user {user_id}")
        
        # Update task for the current user
        response = supabase.table('tasks').update(data).eq('id', task_id).eq('user_id', user_id).execute()
        
        if not response.data:
            return jsonify({'error': 'Task not found'}), 404
            
        print(f"Task updated successfully: {response.data[0]}")
        return jsonify(response.data[0])
    except Exception as e:
        print(f"Error in update_task: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        # Use the global supabase client since RLS is disabled
        response = supabase.table('tasks').delete().eq('id', task_id).execute()
        
        if not response.data:
            return jsonify({'error': 'Task not found'}), 404
            
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error deleting task: {str(e)}")
        return jsonify({
            'error': str(e),
            'details': getattr(e, 'details', None),
            'hint': getattr(e, 'hint', None),
            'code': getattr(e, 'code', None)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
