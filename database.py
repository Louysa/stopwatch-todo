import sqlite3

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
    task_id INTEGER NOT NULL,
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


def log_time(task_id, start_time, end_time):
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()

    cursor.execute('INSERT INTO time_logs (task_id, start_time, end_time) VALUES (?, ?, ?)', (task_id, start_time, end_time))
    connection.commit()
    connection.close()

