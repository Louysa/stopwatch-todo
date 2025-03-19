from flask import session
import uuid
from datetime import datetime

def get_device_id():
    if 'device_id' not in session:
        session['device_id'] = str(uuid.uuid4())
    return session['device_id']

# Note: All database operations are now handled in app.py using SQLAlchemy models

