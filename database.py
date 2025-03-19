import sqlite3
from datetime import datetime
from flask import session
import uuid

def init_db():
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()

    cursor.execute(''' CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task TEXT NOT NULL,
        completed BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    cursor.execute(''' CREATE TABLE IF NOT EXISTS time_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT,
        start_time TIMESTAMP NOT NULL,
        end_time TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    connection.commit()
    connection.close()

def add_task(task):
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()

    cursor.execute('INSERT INTO tasks (task) VALUES (?)', (task,))
    task_id = cursor.lastrowid
    connection.commit()
    connection.close()
    return task_id

def toggle_task(task_id):
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()

    cursor.execute('UPDATE tasks SET completed = NOT completed WHERE id = ?', (task_id,))
    connection.commit() 
    connection.close()

def get_tasks():
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()

    cursor.execute('SELECT id, task, completed FROM tasks ORDER BY created_at DESC')
    tasks = [{'id': row[0], 'task': row[1], 'completed': bool(row[2])} for row in cursor.fetchall()]
    connection.close()
    return tasks

def delete_task(task_id):
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()

    cursor.execute('DELETE FROM tasks where id = ? ',(task_id,))
    connection.commit()
    connection.close()

def log_time(description, start_time, end_time):
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()

    cursor.execute('INSERT INTO time_logs (description, start_time, end_time) VALUES (?, ?, ?)', 
                  (description, start_time, end_time))
    connection.commit()
    connection.close()

def get_device_id():
    if 'device_id' not in session:
        session['device_id'] = str(uuid.uuid4())
    return session['device_id']

def get_time_logs():
    from app import TimeLog  # Import here to avoid circular imports
    device_id = get_device_id()
    
    # Get all logs for this device using SQLAlchemy
    logs = TimeLog.query.filter_by(device_id=device_id).order_by(TimeLog.date.desc()).all()
    
    # Format the logs
    formatted_logs = []
    for log in logs:
        formatted_logs.append({
            'date': log.date.strftime('%Y-%m-%d'),
            'start_time': log.start_time.strftime('%H:%M:%S'),
            'end_time': log.end_time.strftime('%H:%M:%S'),
            'duration': log.duration
        })
    
    return formatted_logs

def get_daily_stats():
    from app import TimeLog  # Import here to avoid circular imports
    device_id = get_device_id()
    daily_stats = []
    
    # Get all logs for this device using SQLAlchemy
    logs = TimeLog.query.filter_by(device_id=device_id).order_by(TimeLog.date.desc()).all()
    
    # Process logs by date
    dates_processed = set()
    for log in logs:
        date_str = log.date.strftime('%Y-%m-%d')
        if date_str not in dates_processed:
            dates_processed.add(date_str)
            
            # Get all logs for this date
            daily_logs = TimeLog.query.filter_by(
                device_id=device_id,
                date=log.date
            ).all()
            
            total_duration = sum(log.duration for log in daily_logs)
            
            daily_stats.append({
                'date': date_str,
                'total_duration': total_duration,
                'sessions': len(daily_logs)
            })
    
    return daily_stats

