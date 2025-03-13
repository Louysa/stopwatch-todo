from flask import Flask, render_template, request, jsonify
from database import init_db, add_task, get_tasks, toggle_task, delete_task, log_time, get_time_logs, get_daily_stats
from datetime import datetime


app = Flask(__name__)

init_db()

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

if __name__ == "__main__":
    app.run(debug=True)
