from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import random
import firebase_admin
from firebase_admin import credentials, firestore
import pyrebase

firebaseConfig = {
    "apiKey": "AIzaSyDHFyB_NyN9oLfOSDDcLMwlyWRKhj0oLj0",
    "authDomain": "proapp-5d45e.firebaseapp.com",
    "projectId": "proapp-5d45e",
    "storageBucket": "proapp-5d45e.firebasestorage.app",
    "messagingSenderId": "253077536591",
    "appId": "1:253077536591:web:88ac06c53ee377b1700f3a",
    "measurementId": "G-9QK0MPFER6",
    "databaseURL":"https://proapp-5d45e-default-rtdb.firebaseio.com/",
}

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

# Initialize Firebase Admin SDK
cred = credentials.Certificate('serviceAccountKey.json')  # Update your path here
firebase_admin.initialize_app(cred)
db = firestore.client()

# -------------------- TASKS ROUTES --------------------

@app.route('/tasks')
def tasks():
    # Order by created_at descending to get recent tasks first
    tasks_ref = db.collection('tasks').order_by('created_at', direction=firestore.Query.DESCENDING)
    tasks_docs = tasks_ref.stream()
    tasks = []

    def random_pastel_color():
        r = lambda: random.randint(150, 255)
        return f'rgb({r()},{r()},{r()})'

    for doc in tasks_docs:
        task = doc.to_dict()
        task['id'] = doc.id

        # Convert Firestore timestamps to Python datetime
        if 'deadline' in task and task['deadline']:
            if hasattr(task['deadline'], 'to_pydatetime'):
                task['deadline'] = task['deadline'].to_pydatetime()
        if 'started_at' in task and task['started_at']:
            if hasattr(task['started_at'], 'to_pydatetime'):
                task['started_at'] = task['started_at'].to_pydatetime()

        # Assign a random pastel color to each task
        task['color'] = random_pastel_color()

        # Check if all subtasks are done
        subtasks = task.get('subtasks', [])
        all_subtasks_done = True
        if subtasks:
            all_subtasks_done = all(subtask.get('is_done', False) for subtask in subtasks)
        task['all_subtasks_done'] = all_subtasks_done

        tasks.append(task)

    return render_template('tasks.html', tasks=tasks)



@app.route('/toggle/<task_id>')
def toggle_task(task_id):
    task_ref = db.collection('tasks').document(task_id)
    task = task_ref.get()
    if task.exists:
        current_status = task.to_dict().get('is_done', False)
        task_ref.update({'is_done': not current_status})
    return redirect(url_for('tasks'))

@app.route('/delete/<task_id>')
def delete_task(task_id):
    db.collection('tasks').document(task_id).delete()
    return redirect(url_for('tasks'))

from datetime import datetime, timezone

@app.route('/start/<task_id>')
def start_task(task_id):
    task_ref = db.collection('tasks').document(task_id)
    task = task_ref.get()
    if task.exists:
        task_data = task.to_dict()
        if not task_data.get('started_at'):
            from datetime import timezone
            task_ref.update({'started_at': datetime.now(timezone.utc)})
    # After starting, go straight to focus mode
    return redirect(url_for('focus_task', task_id=task_id))

@app.route('/add_subtask/<task_id>', methods=['POST'])
def add_subtask(task_id):
    subtask_title = request.form['subtask_title']
    task_ref = db.collection('tasks').document(task_id)
    task = task_ref.get()
    if task.exists:
        subtasks = task.to_dict().get('subtasks', [])
        subtasks.append({'title': subtask_title, 'is_done': False})
        task_ref.update({'subtasks': subtasks})
    return redirect(url_for('index'))

@app.route('/toggle_subtask/<task_id>/<int:subtask_index>')
def toggle_subtask(task_id, subtask_index):
    task_ref = db.collection('tasks').document(task_id)
    task = task_ref.get()
    if task.exists:
        subtasks = task.to_dict().get('subtasks', [])
        if 0 <= subtask_index < len(subtasks):
            subtasks[subtask_index]['is_done'] = not subtasks[subtask_index]['is_done']
            task_ref.update({'subtasks': subtasks})
    return redirect(url_for('tasks'))

# --------------------- FOCUS TASKS --------------------------
@app.route('/add_task', methods=['POST'])
def add_task():
    title = request.form.get('title')
    deadline_str = request.form.get('deadline')
    duration = request.form.get('duration')

    if not title:
        # You can handle errors better here
        return redirect(url_for('tasks'))

    # Convert deadline string to datetime if provided
    deadline = None
    if deadline_str:
        try:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
        except ValueError:
            deadline = None  # Ignore or handle invalid date format

    # Convert duration to int if provided
    duration_minutes = None
    if duration:
        try:
            duration_minutes = int(duration)
        except ValueError:
            duration_minutes = None

    # Prepare task data
    task_data = {
        'title': title,
        'created_at': datetime.utcnow(),
        'is_done': False,
        'subtasks': [],
        'deadline': deadline,
        'duration_minutes': duration_minutes,
        'started_at': None,
    }

    # Save to Firestore
    db.collection('tasks').add(task_data)

    return redirect(url_for('tasks'))

@app.route('/focus/<task_id>')
def focus(task_id):
    tasks_ref = db.collection('tasks').stream()
    tasks = []
    for t in tasks_ref:
        task_data = t.to_dict()
        task_data['id'] = t.id
        tasks.append(task_data)
    
    return render_template('tasks.html', tasks=tasks, focus_task_id=task_id)

# -------------------- WEEKLY GOALS ROUTES --------------------

def random_pastel_color():
    r = lambda: random.randint(150, 255)
    return f'rgb({r()},{r()},{r()})'

@app.route('/goals', methods=['GET'])
def show_goals():
    goals_ref = db.collection('weekly_goals').order_by('created_at', direction=firestore.Query.DESCENDING)
    goals_docs = goals_ref.stream()
    goals = []
    for doc in goals_docs:
        goal = doc.to_dict()
        goal['id'] = doc.id
        if 'created_at' in goal and goal['created_at']:
            if hasattr(goal['created_at'], 'to_pydatetime'):
                goal['created_at'] = goal['created_at'].to_pydatetime()
        goals.append(goal)
    return render_template('goals.html', goals=goals)

@app.route('/add_goal', methods=['POST'])
def add_goal():
    title = request.form.get('goal_title')
    if title:
        color = random_pastel_color()
        goal_data = {
            'title': title,
            'created_at': datetime.utcnow(),
            'color': color
        }
        db.collection('weekly_goals').add(goal_data)
    return redirect(url_for('show_goals'))

@app.route('/delete_goal/<goal_id>', methods=['POST'])
def delete_goal(goal_id):
    db.collection('weekly_goals').document(goal_id).delete()
    return redirect(url_for('show_goals'))

# -------------------- AUTH ROUTES --------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            user = auth.sign_in_with_email_and_password(email, password)
            session['firebase_user'] = user['idToken']
            return redirect(url_for('tasks'))  # Or 'index' if you prefer
        except Exception as e:
            print("Login failed:", e)
            return render_template('login.html', error="Invalid email or password.")
    else:
        return render_template('login.html')




@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop("firebase_user", None)
    return redirect(url_for('home'))

# -------------------- HOME -------------------

@app.route('/')
def home():
    if 'firebase_user' in session:
        return redirect(url_for('tasks'))  # already logged in, go to index
    return render_template('home.html')  # not logged in, stay on home


# -------------------- RUN --------------------

if __name__ == '__main__':
    app.run(debug=True)
