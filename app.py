from flask import Flask, render_template, request, jsonify, session, make_response
from datetime import datetime
import os
import uuid
from functools import wraps
from supabase import create_client

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24).hex())

# Supabase configuration
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)

# Create the time_logs table in Supabase with this SQL:
"""
create table time_logs (
    id bigint generated by default as identity primary key,
    start_time timestamp with time zone,
    end_time timestamp with time zone,
    date date,
    duration integer,
    device_id text
);
"""

# Use a simple in-memory storage for Vercel
tasks = {}
time_logs = {}

# Add admin authentication
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'your-dev-password')  # Change this in Render's environment variables

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.password != ADMIN_PASSWORD:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

def get_device_id():
    if 'device_id' not in session:
        session['device_id'] = str(uuid.uuid4())
    return session['device_id']

@app.route('/')
def index():
    # Check for device_id cookie or create new one
    device_id = request.cookies.get('device_id')
    response = make_response(render_template('index.html'))
    
    if not device_id:
        device_id = str(uuid.uuid4())
        response.set_cookie('device_id', device_id, max_age=31536000)  # 1 year

    return response

@app.route('/api/tasks', methods=['GET', 'POST'])
def handle_tasks():
    device_id = get_device_id()
    if device_id not in tasks:
        tasks[device_id] = []
    
    if request.method == 'POST':
        data = request.get_json()
        task = {
            'id': str(uuid.uuid4()),
            'task': data['task'],
            'completed': False,
            'created_at': datetime.utcnow().isoformat()
        }
        tasks[device_id].append(task)
        return jsonify(task)
    
    return jsonify(tasks.get(device_id, []))

@app.route('/api/tasks/<task_id>/toggle', methods=['POST'])
def toggle_task(task_id):
    device_id = get_device_id()
    device_tasks = tasks.get(device_id, [])
    
    for task in device_tasks:
        if task['id'] == task_id:
            task['completed'] = not task['completed']
            break
    
    return jsonify({'success': True})

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    device_id = get_device_id()
    if device_id in tasks:
        tasks[device_id] = [t for t in tasks[device_id] if t['id'] != task_id]
    return jsonify({'success': True})

@app.route('/api/time-logs', methods=['POST'])
def create_time_log():
    device_id = get_device_id()
    if device_id not in time_logs:
        time_logs[device_id] = []
    
    data = request.get_json()
    start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
    end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
    
    log = {
        'id': str(uuid.uuid4()),
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat(),
        'date': start_time.date().isoformat(),
        'duration': int((end_time - start_time).total_seconds())
    }
    
    time_logs[device_id].append(log)
    return jsonify({'success': True})

# Add these new routes for database management
@app.route('/api/admin/truncate', methods=['POST'])
@admin_required
def truncate_database():
    try:
        # Delete all records but keep tables
        tasks.clear()
        time_logs.clear()
        return jsonify({'message': 'Database truncated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def database_stats():
    try:
        stats = {
            'total_tasks': sum(len(tasks.get(device_id, [])) for device_id in tasks),
            'total_time_logs': sum(len(time_logs.get(device_id, [])) for device_id in time_logs),
            'unique_devices': len(tasks),
            'device_breakdown': []
        }
        
        # Get stats per device
        for device_id, device_tasks in tasks.items():
            device_stats = {
                'device_id': device_id,
                'tasks': len(device_tasks),
                'time_logs': len(time_logs.get(device_id, []))
            }
            stats['device_breakdown'].append(device_stats)
            
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin')
@admin_required
def admin_dashboard():
    return render_template('admin.html')

@app.route("/log_time", methods=["POST"])
def log_time():
    try:
        data = request.json
        device_id = request.cookies.get('device_id', str(uuid.uuid4()))
        
        time_log = {
            "start_time": datetime.fromtimestamp(data["startTime"] / 1000).isoformat(),
            "end_time": datetime.fromtimestamp(data["endTime"] / 1000).isoformat(),
            "date": datetime.now().date().isoformat(),
            "duration": data["duration"],
            "device_id": device_id
        }
        
        result = supabase.table('time_logs').insert(time_log).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get_logs")
def get_logs():
    try:
        device_id = request.cookies.get('device_id')
        if not device_id:
            return jsonify([])
            
        result = supabase.table('time_logs')\
            .select("*")\
            .eq('device_id', device_id)\
            .order('date', desc=True)\
            .execute()
        
        return jsonify(result.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
