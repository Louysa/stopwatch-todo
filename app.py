from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from database import init_db, add_task, get_tasks, toggle_task, delete_task, log_time, get_time_logs, get_daily_stats
from datetime import datetime
import os

app = Flask(__name__)

# Configure database
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///stopwatch.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class TimeLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    date = db.Column(db.Date, nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # duration in seconds

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)

# Create tables
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    tasks = get_tasks()
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
