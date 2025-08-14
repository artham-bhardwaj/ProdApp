from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import random
import firebase_admin
from firebase_admin import credentials, firestore
import pyrebase

firebaseConfig = {
    "apiKey": "YOUR_API_KEY_HERE",
    "authDomain": "YOUR_AUTH_DOMAIN_HERE",
    "projectId": "YOUR_PROJECT_ID_HERE",
    "storageBucket": "YOUR_STORAGE_BUCKET_HERE",
    "messagingSenderId": "YOUR_MESSAGING_SENDER_ID_HERE",
    "appId": "YOUR_APP_ID_HERE",
    "measurementId": "YOUR_MEASUREMENT_ID_HERE",
    "databaseURL": "YOUR_DATABASE_URL_HERE",
}

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'YOUR_SECRET_KEY_HERE'

# Initialize Firebase Admin SDK
cred = credentials.Certificate('PATH_TO_YOUR_SERVICE_ACCOUNT_KEY_JSON')
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
        return redirect(url_for('tasks'))

    # Convert deadline string to datetime if provided
    deadline = None
    if deadline_str:
        try:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
        except ValueError:
            deadline = None

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
    ifI'll break down the changes into smaller, more manageable sections to ensure they can be applied correctly. 

### Changes to be made in `app.py`:

1. Replace the `apiKey`, `authDomain`, `projectId`, `storageBucket`, `messagingSenderId`, `appId`, `measurementId`, and `databaseURL` in the `firebaseConfig` dictionary with placeholder text.
2. Replace the `SECRET_KEY` with a placeholder.
3. Update the path to the service account key to a placeholder.

I'll start with the first change.

<edit_file>
<path>app.py</path>
<content>
<<<<<<< SEARCH
    "apiKey": "AIzaSyDHFyB_NyN9oLfOSDDcLMwlyWRKhj0oLj0",
=======
    "apiKey": "YOUR_FIREBASE_API_KEY",
