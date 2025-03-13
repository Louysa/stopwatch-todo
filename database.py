import sqlite3
from datetime import datetime

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

def get_time_logs():
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()

    cursor.execute('''
        SELECT 
            id,
            description,
            start_time,
            end_time,
            strftime('%Y-%m-%d', start_time) as date,
            strftime('%H:%M:%S', start_time) as start_time_formatted,
            strftime('%H:%M:%S', end_time) as end_time_formatted,
            ROUND((julianday(end_time) - julianday(start_time)) * 24 * 60 * 60) as duration
        FROM time_logs 
        ORDER BY start_time DESC
    ''')
    logs = [{
        'id': row[0],
        'description': row[1],
        'start_time': row[2],
        'end_time': row[3],
        'date': row[4],
        'start_time_formatted': row[5],
        'end_time_formatted': row[6],
        'duration': row[7]
    } for row in cursor.fetchall()]
    connection.close()
    return logs

def get_daily_stats():
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()

    cursor.execute('''
        SELECT 
            strftime('%Y-%m-%d', start_time) as date,
            COUNT(*) as sessions,
            ROUND(SUM((julianday(end_time) - julianday(start_time)) * 24 * 60 * 60)) as total_duration
        FROM time_logs 
        GROUP BY date 
        ORDER BY date DESC
    ''')
    stats = [{
        'date': row[0],
        'sessions': row[1],
        'total_duration': row[2]
    } for row in cursor.fetchall()]
    connection.close()
    return stats

