from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from datetime import datetime
from flask import send_from_directory
from werkzeug.utils import secure_filename
from firebase_admin import storage
import os
from google.cloud import exceptions
from functools import wraps
from flask import redirect, url_for, session



# Your Firestore functions
from travel_request import get_all_travel_requests, create_travel_request, get_travel_request, update_travel_request, get_personnel_details, get_travel_request_files
from firebase_admin import firestore

app = Flask(__name__)
app.secret_key = 

# Firebase config
bucket = storage.bucket()

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/home')
def home():
    # Get all travel requests from Firestore
    travel_requests = get_all_travel_requests()
    return render_template('home.html', travel_requests=travel_requests)


@app.route('/reset_password.html', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        # Here you might want to implement the logic for resetting a password.
        # You'll probably want to check the provided email address, generate a
        # reset token, store it somewhere, and send it to the user's email.
        email = request.form['email']  # assuming your form field for email is named 'email'
        try:
            auth.send_password_reset_email(email)
            flash("Password reset email sent")
            return redirect(url_for('home'))
        except exceptions.FirebaseError as e:
            flash("Error resetting password: {}".format(e))
            return render_template('reset_password.html'), 400
    else:
        # If it's a GET request, render the reset password page.
        return render_template('reset_password.html')



@app.route('/upload_file/<string:id>', methods=['POST'])
def upload_file(id):
    if 'file' not in request.files:
        return 'No file part in the request', 400
    file = request.files['file']
    if file.filename == '':
        return 'No file selected for uploading', 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        blob = bucket.blob(f'{id}/{filename}')
        blob.upload_from_string(
            file.read(),
            content_type=file.content_type
        )
        
        # Save file metadata in Firestore
        db = firestore.client()
        file_data = {
            'filename': filename,
            'trip_number': id,  # here we are using 'id' as 'trip_number'
            'uploaded_at': datetime.now().isoformat()  # Store the current timestamp
        }
        db.collection('travel_request_files').add(file_data)
        
        return redirect(url_for('travel_request', id=id))
    else:
        return 'Allowed file types are txt, pdf, png, jpg, jpeg, gif', 400

@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        # Get form data and create a new travel request
        form_data = request.form
        creation_date_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        create_travel_request(
            form_data.get('request_type'),
            form_data.get('trip_number'),
            form_data.get('employee_id'),
            form_data.get('traveller_number'),
            form_data.get('personnel_name'),
            form_data.get('task_order'),
            form_data.get('departure_location'),
            form_data.get('checkin_date'),
            form_data.get('arrival_location'),
            form_data.get('arrival_date'),
            form_data.get('booking_status'),
            creation_date_time,
            form_data.get('created_by')
        )
        return redirect(url_for('home'))
    else:
        return render_template('create.html')

@app.route('/travel_request/<string:id>')
def travel_request(id):
    # Get the travel request from Firestore
    travel_request = get_travel_request(id)

    # Fetch the personnel details from the database
    personnel_details = get_personnel_details(id)
    
    # Fetch the travel request files from Firebase Storage
    travel_request_files = get_travel_request_files(id)

    # Pass it to the template
    return render_template('travel_request.html', travel_request=travel_request, personnel_details=personnel_details, travel_request_files=travel_request_files)

def get_travel_request_files(id):
    # Get a reference to your Firestore client
    db = firestore.client()
    
    # Query the 'travel_request_files' collection for documents where 'trip_number' equals 'id'
    docs = db.collection('travel_request_files').where('trip_number', '==', id).stream()
    
    # Create a list of files from the documents
    files = [doc.to_dict() for doc in docs]
    
    return files

@app.route('/update_travel_request/<string:id>', methods=['GET', 'POST'])
def handle_update_travel_request(id):
    if request.method == 'POST':
        form_data = request.form
        update_travel_request(id, form_data) 
        return redirect(url_for('travel_request', id=id))
    else:
        travel_request = get_travel_request(id)
        return render_template('update_travel_request.html', travel_request=travel_request)


def delete_travel_request_from_db(trip_number):
    db = firestore.client()
    travel_requests = db.collection('travel_requests')
    docs = travel_requests.where('trip_number', '==', trip_number).stream()

    for doc in docs:
        travel_requests.document(doc.id).delete()

@app.route('/delete_travel_request/<trip_number>', methods=['GET', 'POST'])
def delete_travel_request(trip_number):
    if request.method == 'POST':
        delete_travel_request_from_db(trip_number)
        return redirect(url_for('home'))
    else:
        return "This route only accepts POST requests."

from firebase_admin import auth
from flask import request, jsonify

@app.route('/verifyIdToken', methods=['POST'])
def verify_id_token():
    id_token = request.json['idToken']
    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        session['logged_in'] = True  # Set session variable
        session['uid'] = uid  # Set uid in the session
        return jsonify({'uid': uid}), 200
    except ValueError:
        # Invalid token
        return jsonify({'error': 'Invalid token'}), 400


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('logged_in', None)
    return jsonify({'message': 'Logged out'}), 200


@app.route('/protected_route')
def protected_route():
    if 'uid' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    # Proceed with route
@app.route('/download_file/<trip_number>/<filename>')
def download_file(trip_number, filename):
    print(f"Downloading file: {trip_number}/{filename}")
    
    # Create a blob for the file
    blob = bucket.blob(f'{trip_number}/{filename}')
    
    # Create a new file in your local filesystem
    with open(filename, 'wb') as file_obj:
        # Download the file from Firebase Storage
        blob.download_to_file(file_obj)
        print(f"File downloaded to: {os.path.abspath(filename)}")

    return redirect(url_for('travel_request', id=trip_number))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('home', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/loggedin')
@login_required
def loggedin():
    return render_template('loggedin.html')

if __name__ == '__main__':
    app.run(debug=False)
