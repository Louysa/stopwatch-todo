from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import uuid
from functools import wraps

app = Flask(__name__)

# Configure database
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///stopwatch.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24).hex())

db = SQLAlchemy(app)

# Models
class TimeLog(db.Model):
    __tablename__ = 'time_log'
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    date = db.Column(db.Date, nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    device_id = db.Column(db.String(36), nullable=False)

class Task(db.Model):
    __tablename__ = 'task'
    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    device_id = db.Column(db.String(36), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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

# Initialize database
with app.app_context():
    db.create_all()
    print("Database tables created successfully!")

@app.route('/')
def index():
    device_id = get_device_id()
    tasks = Task.query.filter_by(device_id=device_id).order_by(Task.created_at.desc()).all()
    time_logs = TimeLog.query.filter_by(device_id=device_id).order_by(TimeLog.date.desc()).all()
    
    # Calculate stats
    stats = []
    dates_processed = set()
    for log in time_logs:
        date_str = log.date.strftime('%Y-%m-%d')
        if date_str not in dates_processed:
            dates_processed.add(date_str)
            daily_logs = TimeLog.query.filter_by(
                device_id=device_id,
                date=log.date
            ).all()
            total_duration = sum(log.duration for log in daily_logs)
            stats.append({
                'date': date_str,
                'total_duration': total_duration,
                'sessions': len(daily_logs)
            })
    
    return render_template('index.html', tasks=tasks, time_logs=time_logs, stats=stats)

@app.route('/api/tasks', methods=['GET', 'POST'])
def handle_tasks():
    device_id = get_device_id()
    
    if request.method == 'POST':
        data = request.get_json()
        new_task = Task(
            task=data['task'],
            device_id=device_id
        )
        db.session.add(new_task)
        db.session.commit()
        return jsonify({
            'id': new_task.id,
            'task': new_task.task,
            'completed': new_task.completed
        })
    
    tasks = Task.query.filter_by(device_id=device_id).order_by(Task.created_at.desc()).all()
    return jsonify([{
        'id': task.id,
        'task': task.task,
        'completed': task.completed
    } for task in tasks])

@app.route('/api/tasks/<int:task_id>/toggle', methods=['POST'])
def toggle_task(task_id):
    device_id = get_device_id()
    task = Task.query.filter_by(id=task_id, device_id=device_id).first_or_404()
    task.completed = not task.completed
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    device_id = get_device_id()
    task = Task.query.filter_by(id=task_id, device_id=device_id).first_or_404()
    db.session.delete(task)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/time-logs', methods=['POST'])
def create_time_log():
    device_id = get_device_id()
    data = request.get_json()
    
    start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
    end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
    duration = int((end_time - start_time).total_seconds())
    
    time_log = TimeLog(
        start_time=start_time,
        end_time=end_time,
        date=start_time.date(),
        duration=duration,
        device_id=device_id
    )
    
    db.session.add(time_log)
    db.session.commit()
    
    return jsonify({'success': True})

# Add these new routes for database management
@app.route('/api/admin/truncate', methods=['POST'])
@admin_required
def truncate_database():
    try:
        # Delete all records but keep tables
        TimeLog.query.delete()
        Task.query.delete()
        db.session.commit()
        return jsonify({'message': 'Database truncated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def database_stats():
    try:
        stats = {
            'total_tasks': Task.query.count(),
            'total_time_logs': TimeLog.query.count(),
            'unique_devices': db.session.query(db.func.count(db.distinct(TimeLog.device_id))).scalar(),
            'device_breakdown': []
        }
        
        # Get stats per device
        devices = db.session.query(TimeLog.device_id).distinct().all()
        for device in devices:
            device_id = device[0]
            device_stats = {
                'device_id': device_id,
                'tasks': Task.query.filter_by(device_id=device_id).count(),
                'time_logs': TimeLog.query.filter_by(device_id=device_id).count()
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
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
