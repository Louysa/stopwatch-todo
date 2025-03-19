from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from database import init_db, add_task, get_tasks, toggle_task, delete_task, log_time, get_time_logs, get_daily_stats
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
    device_id = db.Column(db.String(36), nullable=False, index=True)

class Task(db.Model):
    __tablename__ = 'task'
    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    device_id = db.Column(db.String(36), nullable=False, index=True)
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

# Create all tables
def init_db():
    with app.app_context():
        # Drop all tables first (be careful with this in production!)
        db.drop_all()
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")

# Initialize database tables
init_db()

# One-time cleanup route (protected by admin password)
@app.route('/api/admin/initial-cleanup', methods=['POST'])
def initial_cleanup():
    auth = request.authorization
    if not auth or auth.password != os.environ.get('ADMIN_PASSWORD'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Clear all existing data
        TimeLog.query.delete()
        Task.query.delete()
        db.session.commit()
        return jsonify({'message': 'Database cleaned successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    device_id = get_device_id()
    tasks = Task.query.filter_by(device_id=device_id).order_by(Task.created_at.desc()).all()
    stats = get_daily_stats()
    time_logs = get_time_logs()
    return render_template('index.html', tasks=tasks, stats=stats, time_logs=time_logs)

@app.route('/api/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    task_id = add_task(data['task'])
    return jsonify({'id': task_id, 'task': data['task'], 'completed': False})

@app.route('/api/tasks/<int:task_id>/toggle', methods=['POST'])
def toggle_task_route(task_id):
    toggle_task(task_id)
    return jsonify({'success': True})

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task_route(task_id):
    delete_task(task_id)
    return jsonify({'success': True})

@app.route('/api/time-logs', methods=['POST'])
def create_time_log():
    data = request.get_json()
    log_time(data.get('description', ''), data['start_time'], data['end_time'])
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
