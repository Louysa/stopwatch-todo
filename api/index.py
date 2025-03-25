from flask import Flask, render_template, request, jsonify, make_response, redirect, url_for
from supabase import create_client
from datetime import datetime
import os
import uuid

app = Flask(__name__,
    template_folder='../templates',
    static_folder='../static',
    static_url_path='/static'
)

# Supabase configuration
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)

@app.route('/')
def index():
    device_id = request.cookies.get('device_id')
    response = make_response(render_template('index.html', 
        title="Gothic Stopwatch",  # Keep your gothic themed title
        panel_title="Tasks of the Night"  # Keep your gothic themed panel title
    ))
    
    if not device_id:
        device_id = str(uuid.uuid4())
        response.set_cookie('device_id', device_id, max_age=31536000)
    
    return response

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            return redirect(url_for('index'))
        except Exception as e:
            return render_template('login.html', 
                error="Invalid credentials",
                title="Gothic Login"  # Keep gothic theme in login
            )
    return render_template('login.html', title="Gothic Login")

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            response = supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            return redirect(url_for('login'))
        except Exception as e:
            return render_template('signup.html', 
                error="Signup failed",
                title="Gothic Signup"  # Keep gothic theme in signup
            )
    return render_template('signup.html', title="Gothic Signup")

@app.route('/logout')
def logout():
    try:
        supabase.auth.sign_out()
        response = make_response(redirect(url_for('login')))
        # Clear any auth cookies if you're using them
        return response
    except Exception as e:
        return redirect(url_for('index'))

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
        return jsonify({"success": True, "message": "Time logged in the shadows"})
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
