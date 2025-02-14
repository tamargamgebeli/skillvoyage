import os
import json
from flask import Flask, redirect, request, render_template, url_for, jsonify, session
from datetime import date, datetime, timedelta
from flask_mail import Mail, Message
from twilio.rest import Client
from apscheduler.schedulers.background import BackgroundScheduler
from flask_cors import CORS

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your_secret_key")  # Set a default secret key

# APScheduler-ის ინიციალიზაცია
scheduler = BackgroundScheduler()

# CORS კონფიგურაცია
CORS(app)  # ეს გაძლევთ CORS-ის პოვებას ნებისმიერი დომენისგან

# Flask-Mail კონფიგურაცია
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = print('MAIL_PORT') # Provide a default value of 587
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')  
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')  

mail = Mail(app)

# Twilio კონფიგურაცია
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')
client = Client(account_sid, auth_token)

# JSON ფაილის სახელია users.json
filename = 'users.json'

# დრო
datetoday = date.today().strftime("%m_%d_%y")

# JSON ფაილის შექმნა, თუ ის არ არსებობს
if not os.path.exists(filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump([], f, ensure_ascii=False, indent=4)

def get_users():
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []  # თუ ფაილი არ არსებობს, დავაბრუნოთ ცარიელი სია

def save_users(tasklist):
    """შეინახავს ახლანდელ tasklist-ს JSON ფაილში"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(tasklist, f, ensure_ascii=False, indent=4)
        print("Saved task list:", tasklist)  # print statement

def updatetasklist(tasklist):
    with open('users.json', 'w', encoding='utf-8') as f:
        json.dump(tasklist, f, indent=4)

# JSON ფაილის სახელია projects.json
projects_filename = 'projects.json'

# JSON ფაილის შექმნა, თუ ის არ არსებობს
if not os.path.exists(projects_filename):
    with open(projects_filename, 'w', encoding='utf-8') as f:
        json.dump([], f, ensure_ascii=False, indent=4)

def get_projects():
    if os.path.exists(projects_filename):
        with open(projects_filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []  # თუ ფაილი არ არსებობს, დავაბრუნოთ ცარიელი სია

def save_projects(projectlist):
    """შეინახავს ახლანდელ projectlist-ს JSON ფაილში"""
    with open(projects_filename, 'w', encoding='utf-8') as f:
        json.dump(projectlist, f, ensure_ascii=False, indent=4)
        print("Saved project list:", projectlist)  # print statement

################## როუტების ფუნქცია #########################

@app.route('/')
def login_sigup():
    tasklist = get_users()  # no need to pass 'users' anymore
    return render_template('login_signup.html', datetoday=date.today().strftime("%m_%d_%y"), tasklist=tasklist, l=len(tasklist))

@app.route('/home', methods=['GET'])
def home():
    projects = get_projects()
    return render_template('home.html', projects=projects)

# 24 საათით ადრე ელექტრონული ფოსტის გაგზავნა
def send_reminder_email(user_email, project, deadline):
    subject = f"პროექტის დედლაინი {project}"
    body = f"მოგესალმებით,\n\nთქვენ მიერ შერჩეული პროექტის დედლაინი მოახლოვდა. გთხოვთ გაითვალისწინოთ, რომ პროექტზე '{project}' რეგისტრაცია სრულდება: {deadline}.\n წარმატებები!"
    
    send_email(user_email, subject, body)  # Email გაგზავნა

def send_email(to, subject, body):
    msg = Message(subject, recipients=[to], sender='')
    msg.body = body
    mail.send(msg)

def send_sms(to, body):
    message = client.messages.create(
        body=body,
        from_=twilio_phone_number,
        to=to
    )

# ტესტის ელ-ფოსტა
@app.route("/send_test_email")
def send_test_email():
    msg = Message("Hello from Flask", 
                  sender="",  
                  recipients=[""])
    msg.body = "This is a test email sent from Flask."
    mail.send(msg)
    return "Test email sent!"

# ტასკის წაშლა######################################################################3
@app.route('/remove_user', methods=['GET'])
def remove_user_route():
    # Print statement for debugging
    print("Accessed /remove_user route")
    
    # მიიღეთ ელ.ფოსტა URL პარამეტრიდან
    email_to_remove = request.args.get('email')
    print(f"Email to remove: {email_to_remove}")  # Print statement for debugging
    
    if not email_to_remove:
        return jsonify({"success": False, "message": "Email is required"}), 400
    
    # მიიღეთ მომხმარებლების სია
    users = get_users()
    
    # მოძებნეთ მომხმარებელი ელ.ფოსტის მიხედვით და წაშალეთ
    users = [user for user in users if user['email'] != email_to_remove]
    
    # შეინახეთ განახლებული სია JSON ფაილში
    save_users(users)
    
    # Render the home template with the updated user list
    return render_template('home.html', datetoday=date.today().strftime("%m_%d_%y"), tasklist=users, l=len(users))
###########################################################################################
# სიის გასუფთავება
@app.route('/clear')
def clear_list():
    save_users([])  # სიის გასუფთავება
    return render_template('home.html', datetoday=date.today().strftime("%m_%d_%y"), tasklist=[], l=0)

@app.route('/register', methods=['POST'])
def handle_sign_up():
    jsn_dt = request.get_json()

    fullname = jsn_dt.get('fullname')
    age = jsn_dt.get('age')
    phone = jsn_dt.get('phone')
    email = jsn_dt.get('email')
    password = jsn_dt.get('password')
    confirm_password = jsn_dt.get('confirm_password')

    # Validate the input data
    if not fullname or not age or not phone or not email or not password or not confirm_password:
        return jsonify({"success": False, "message": "All fields are required"}), 400

    if password != confirm_password:
        return jsonify({"success": False, "message": "Passwords do not match"}), 400

    from werkzeug.security import generate_password_hash
    hashed_password = generate_password_hash(password)

    # Check if the user already exists
    users = get_users()
    for user in users:
        if user['email'] == email:
            return jsonify({"success": False, "message": "User already exists"}), 400

    # Save the user data
    user_data = {
        "fullname": fullname,
        "age": age,
        "phone": phone,
        "email": email,
        "password": hashed_password,
        "selected_project": None
    }

    users.append(user_data)
    save_users(users)
    return jsonify({"success": True, "message": "Registration successful"})

@app.route('/login_signup')
def login_signup():
    return render_template('login_signup.html')


@app.route('/logo_animation')
def logo_animation():
    return render_template('logo_animation.html')


# Route to display the Login page
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/tutorials')
def tutorials():
    return render_template('tutorials.html')

@app.route('/contact_us')
def contact_us():
    return render_template('contact_us.html')

@app.route('/send_message', methods=['POST'])
def send_message():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')
    # Handle the message sending logic here (e.g., save to database, send email, etc.)
    return redirect(url_for('contact_us'))

@app.route('/underconstruction')
def underconstruction():
    return render_template('underconstruction.html')

# Route to handle Login form submission
@app.route('/login', methods=['POST'])
def login():
    jsn_dt = request.get_json()
    email = jsn_dt.get('email')  
    password = jsn_dt.get('password')

    # Validate the input data
    if not email or not password:
        return jsonify({"success": False, "message": "Missing email or password"}), 400

    # Here you would typically check the email and password against your user database
    # For demonstration purposes, let's assume the login is always successful
    success = True

    # Return a JSON response
    return jsonify({"email": email, "password": password, "success": success})

        
@app.route('/save-user', methods=['POST'])
def save_user():
    data = request.json  # მიიღე მონაცემები JSON ფორმატში
    try:
        with open('users.json', 'a', encoding = 'UTF-8') as file:
            json.dump(data, file)
            file.write('\n')  # ახალი მონაცემი ახალი ხაზით
        return jsonify({"status": "success", "message": "User data saved"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    

@app.route('/search', methods=['POST'])
def search():
    data = request.get_json()  # Get the JSON data from the request
    query = data.get('query')  # Extract the 'query' parameter from the JSON data
 
@app.route('/success')
def success():
    project = request.args.get('project')
    return render_template('success.html', project=project)

@app.route('/logout')
def logout():
    session.clear()  # Clear the session data
    return redirect(url_for('login_signup'))  # Redirect to the login page

@app.route('/delete_user', methods=['POST'])
def delete_user():
    email_to_remove = request.json.get('email')
    if not email_to_remove:
        return jsonify({"success": False, "message": "Email is required"}), 400

    users = get_users()
    users = [user for user in users if user['email'] != email_to_remove]
    save_users(users)
    return jsonify({"success": True, "message": "User deleted successfully"})

@app.route('/select_project', methods=['POST'])
def select_project():
    data = request.json
    email = data.get('email')
    selected_project = data.get('project')

    if not email or not selected_project:
        return jsonify({"success": False, "message": "Email and project are required"}), 400

    users = get_users()
    for user in users:
        if user['email'] == email:
            user['selected_project'] = selected_project
            user_phone = user['phone']  # Get the user's phone number
            break
    else:
        return jsonify({"success": False, "message": "User not found"}), 404

    save_users(users)

    # Schedule email and SMS reminders
    project_deadline = None
    projects = get_projects()
    for project in projects:
        if project['name'] == selected_project:
            project_deadline = project['deadline']
            break

    if project_deadline:
        reminder_time = datetime.strptime(project_deadline, '%Y-%m-%d') - timedelta(days=1)
        scheduler.add_job(send_reminder_email, 'date', run_date=reminder_time, args=[email, selected_project, project_deadline])
        scheduler.add_job(send_sms, 'date', run_date=reminder_time, args=[user_phone, f"Reminder: The deadline for the project '{selected_project}' is approaching on {project_deadline}."])

    return jsonify({"success": True, "message": "Project selected successfully"})

@app.route('/test')
def test_route():
    return "Test route is working!"

if __name__ == '__main__':
    try:
        # APScheduler-ის დაწყება Flask-ის დაწყებამდე
        scheduler.start()
        # Flask აპლიკაციის გაშვება
        app.run(debug=True, port=5000)
    except (KeyboardInterrupt, SystemExit):
        # APScheduler შეწყვეტა Flask-ის გაჩერებისას
        scheduler.shutdown()  # APScheduler-ის შეწყვეტა




