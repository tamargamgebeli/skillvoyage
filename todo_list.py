import os
from flask import Flask, request, render_template
from datetime import datetime
from twilio.rest import Client
from flask_mail import Mail, Message

app = Flask(__name__)

datetoday2 = datetime.now().strftime('%d-%B-%Y')  # დღე/თვე/წელი

# Twilio Credentials (შეიცვალეთ თქვენი მონაცემებით)
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
from_phone = os.getenv('TWILIO_PHONE_NUMBER')

# Flask-Mail კონფიგურაცია
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = os.getenv('MAIL_PORT')
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')   # თქვენი Gmail მისამართი
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')  # თქვენი Gmail პაროლი

mail = Mail(app)

# Twilio SMS გაგზავნის ფუნქცია
def send_sms(to_phone, body):
    client = Client(account_sid, auth_token)
    message = client.messages.create(
        body=body,
        from_=from_phone,
        to=to_phone
    )
    print(f"SMS sent successfully: {message.sid}")

# Flask-Mail ელ. ფოსტის გაგზავნის ფუნქცია
def send_email(email, task, deadline):
    subject = "მოახლოებული დედლაინი"
    body = f"მოგესალმებით!\n\n თქვენ მიერ შერჩეული პროექტზე: {task}\nრეგისტრაცია სრულდება {deadline}.\n\n გისურვებთ წარმატებებს!"
    
    msg = Message(subject, recipients=[email], body=body)
    try:
        mail.send(msg)
        print("Email sent successfully")
    except Exception as e:
        print(f"Error sending email: {e}")  # შეცდომის ტექსტის გადაცემისას
        return f"Error sending email: {e}"  # რეტურნი ემილზე, თუ ვერ გაიგზავნა

# დავალების სიის ამოღება ფაილიდან
def gettasklist():
    tasklist = []
    if os.path.exists('tasks.txt'):
        with open('tasks.txt', 'r') as f:
            for line in f.readlines():
                task_data = line.strip().split('|')
                if len(task_data) == 4:
                    tasklist.append({
                        'project': task_data[0],
                        'email': task_data[1],
                        'phone': task_data[2],
                        'deadline': task_data[3]
                    })
    return tasklist

# დავალებების ჩამონათვალის შენახვა
def save_tasklist(tasklist):
    with open('tasks.txt', 'w') as f:
        for task in tasklist:
            f.write(f"{task['project']}|{task['email']}|{task['phone']}|{task['deadline']}\n")

# დავალების სიის განახლება
def updatetasklist(tasklist):
    save_tasklist(tasklist)

# მთავარი გვერდი
@app.route('/')
def home():
    return render_template('home.html', datetoday2=datetoday2, tasklist=gettasklist(), l=len(gettasklist()))

# დავალების დასამატებლად
@app.route('/addtask', methods=['POST'])
def add_task():
    task = request.form.get('newtask')
    user_email = request.form.get('email')  # ელ. ფოსტის მისამართი
    user_phone = request.form.get('phone')  # ტელეფონის ნომრის მიღება
    deadline = request.form.get('deadline')  # დედლაინი

    # დავალებების ჩამონათვალის მიღება
    tasklist = gettasklist()

    # ახალი დავალების დამატება
    tasklist.append({
        'project': task,
        'email': user_email,
        'phone': user_phone,
        'deadline': deadline
    })

    # SMS და ელ. ფოსტის გაგზავნა
    if user_phone:
        send_sms(user_phone, f"მოგესალმებით! თქვენ მიერ შერჩეულ პროექტზე {task}\nრეგისტრაცია სრულდება {deadline}. გისურვებთ წარმატებებს!")
    if user_email:
        send_email(user_email, task, deadline)

    # დავალებების განახლება
    updatetasklist(tasklist)

    return render_template('home.html', datetoday2=datetoday2, tasklist=gettasklist(), l=len(gettasklist()))

# დავალების წაშლის ფუნქცია
@app.route('/deltask', methods=['GET'])
def remove_task():
    task_index = int(request.args.get('deltaskid'))
    tasklist = gettasklist()

    if 0 <= task_index < len(tasklist):
        removed_task = tasklist.pop(task_index)
        updatetasklist(tasklist)
        print(f"Task removed: {removed_task}")
    else:
        print("Invalid task index")

    return render_template('home.html', datetoday2=datetoday2, tasklist=tasklist, l=len(tasklist))

# დავალებების გასუფთავება
@app.route('/clear', methods=['GET'])
def clear_list():
    tasklist = []
    save_tasklist(tasklist)
    return render_template('home.html', datetoday2=datetoday2, tasklist=tasklist, l=len(tasklist))

@app.route('/test_email')
def test_email():
    try:
        send_email('test_email@example.com', 'Test Task', '2025-02-15')
        return 'Email sent successfully'
    except Exception as e:
        return f'Error sending email: {e}'


if __name__ == '__main__':
    app.run(debug=True, port=5001)
