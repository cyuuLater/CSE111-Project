# --- IMPORTS ---
import sqlite3
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user 
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt 

# --- 1. APP AND EXTENSION INITIALIZATION ---
app = Flask(__name__)
conn = sqlite3.connect('instance/data.sqlite', check_same_thread=False)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.sqlite'
app.config['SECRET_KEY'] = 'super secret key' 
db = SQLAlchemy(app)

# Initialize Flask Extensions
login_manager = LoginManager(app) 
login_manager.login_view = 'login' # Correct endpoint name (matches function name)
bcrypt = Bcrypt(app) 



# ----------------------------------------------------------------------------------------------------------------------
# --- 2. USER MODEL AND USER LOADER  ---
class User(db.Model, UserMixin): 
    __tablename__ = 'users'
    u_userkey = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), name='u_name', nullable=False) 
    email = db.Column(db.String(60), name='u_email', unique=True, nullable=False) 
    password = db.Column(db.String(120), name='u_password', nullable=False) 

    def get_id(self):
        return str(self.u_userkey)
    def __repr__(self):
        return f'<User {self.username}>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- 3. ROUTES: SIGN UP  ---
@app.route('/signup', methods=['GET'])
def signup():
    return render_template("signup.html") 

@app.route('/signup', methods=['POST']) 
def signup_process():
    username_input = request.form.get('username')
    email_input = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    # Basic validation checks
    if not all([username_input, email_input, password, confirm_password]):
        error = "All fields are required."
        return render_template('signup.html', error=error)
    if password != confirm_password:
        error = "Passwords do not match."
        return render_template('signup.html', error=error)
    
    if User.query.filter_by(username=username_input).first():
        error = "Username already exists. Please choose another."
        return render_template('signup.html', error=error)
    
    if User.query.filter_by(email=email_input).first():
        error = "Email already exists. Please choose another."
        return render_template('signup.html', error=error)
    
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(username=username_input, email=email_input, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return redirect(url_for('login')) 


# --- 4. ROUTES: LOGIN AND LOGOUT ---
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        # Always show the login page
        return render_template("login.html")

    # POST method: process login
    login_id = request.form.get('login_id') 
    password = request.form.get('password')

    # Try to find user by username or email
    user = User.query.filter((User.username == login_id) | (User.email == login_id)).first()

    if user and bcrypt.check_password_hash(user.password, password):
        login_user(user, remember=False)
        return redirect(url_for('home'))
    else:
        error = 'Invalid login ID or password'
        return render_template('login.html', error=error)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- Home page route ---
@app.route('/home')
@login_required
def home():
    return render_template("home.html", username=current_user.username)



# ----------------------------------------------------------------------------------------------------------------------
# --- 5. APP EXECUTION ---
if __name__ == '__main__':
    resetTheTable = False  

    with app.app_context():
        if (resetTheTable):
            db.drop_all()
        db.create_all()

    print("running locally")
    app.run(port=5001, debug=True)