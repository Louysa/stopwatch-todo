from flask import Flask, render_template, request, jsonify, session
from datetime import datetime
import os
import uuid
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24).hex())

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
    device_id = get_device_id()
    device_tasks = tasks.get(device_id, [])
    device_logs = time_logs.get(device_id, [])
    
    # Calculate stats
    stats = []
    dates_processed = set()
    
    for log in device_logs:
        date_str = log['date']
        if date_str not in dates_processed:
            dates_processed.add(date_str)
            daily_logs = [l for l in device_logs if l['date'] == date_str]
            total_duration = sum(l['duration'] for l in daily_logs)
            stats.append({
                'date': date_str,
                'total_duration': total_duration,
                'sessions': len(daily_logs)
            })
    
    return render_template('index.html', tasks=device_tasks, time_logs=device_logs, stats=stats)

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

if __name__ == '__main__':
    app.run(debug=True)
