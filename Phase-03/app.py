import sqlite3
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user 
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt 

app = Flask(__name__)
conn = sqlite3.connect('instance/data.sqlite', check_same_thread=False)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.sqlite'
app.config['SECRET_KEY'] = 'super secret key' 
db = SQLAlchemy(app)

login_manager = LoginManager(app) 
login_manager.login_view = 'login' # Correct endpoint name (matches function name)
bcrypt = Bcrypt(app) # Needed for hashing passwords



# ----------------------------------------------------------------------------------------------------------------------
# --- USER MODEL AND USER LOADER  ---
# ----------------------------------------------------------------------------------------------------------------------

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



# ----------------------------------------------------------------------------------------------------------------------
# --- LOGIN AND SIGN UP  ---
# ----------------------------------------------------------------------------------------------------------------------

# -- Sign up  --
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


# -- Initialize default routes --
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('home', username=current_user.username))
    return redirect(url_for('login'))

# -- Login and Logout --
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
        return redirect(url_for('home', username=current_user.username))
    else:
        error = 'Invalid login ID or password'
        return render_template('login.html', error=error)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))



# ----------------------------------------------------------------------------------------------------------------------
# --- HOME PAGE ROUTES  ---
# ----------------------------------------------------------------------------------------------------------------------

# -- Home page route --
@app.route('/home')
@login_required
def home():
    return render_template("home.html", username=current_user.username)

# -- Redirect to map page --
@app.route('/map')
@login_required
def map_page():
    return render_template("map.html", username=current_user.username)

# -- Redirect to view vehicles page (under vehicle functions) --


# -- Redirect to view permit page (under permit functions) --



# ----------------------------------------------------------------------------------------------------------------------
# --- VIEW/REGISTER VEHICLE PAGE  ---
# ----------------------------------------------------------------------------------------------------------------------

# -- Display the users vehicle information --
@app.route('/view_vehicles')
@login_required
def view_vehicles():
    # Query database and show list of vehicles
    conn = sqlite3.connect('instance/data.sqlite')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT v_vehicleskey, v_plateno, v_platestate, v_maker, v_model, v_color
        FROM vehicles WHERE v_userkey = ?
    """
    , [current_user.u_userkey])
    vehicles = cursor.fetchall()
    conn.close()
    
    return render_template("view_vehicles.html", vehicles=vehicles, username=current_user.username)

# -- Redirect user to the page to register a vehicle --
@app.route('/reg_vehicle', methods=['GET', 'POST'])
@login_required
def reg_vehicle():
    if request.method == 'GET':
        return render_template("reg_vehicle.html", username=current_user.username)
    
    # POST: Process vehicle registration
    plate_no = request.form.get('plate_no')
    plate_state = request.form.get('plate_state')
    maker = request.form.get('maker')
    model = request.form.get('model')
    color = request.form.get('color')
    
    # Validation
    if not all([plate_no, plate_state, maker, model, color]):
        error = "All fields are required."
        return render_template('reg_vehicle.html', error=error, username=current_user.username)
    
    conn = sqlite3.connect('instance/data.sqlite')
    cursor = conn.cursor()
    
    # Check for duplicate plate number for this user
    cursor.execute("""
        SELECT COUNT(*) FROM vehicles 
        WHERE v_userkey = ? AND v_plateno = ?
    """
    , [current_user.u_userkey, plate_no])
    
    if cursor.fetchone()[0] > 0:
        conn.close()
        error = "You already have a vehicle registered with this plate number."
        return render_template('reg_vehicle.html', error=error, username=current_user.username)
    
    # Get the next vehicle key (auto-increment)
    cursor.execute("SELECT MAX(v_vehicleskey) FROM vehicles")
    max_key = cursor.fetchone()[0]
    new_vehicle_key = (max_key or 0) + 1
    
    # Insert new vehicle
    sql = """
        INSERT INTO vehicles(v_vehicleskey, v_userkey, v_plateno, v_platestate, v_maker, v_model, v_color)
        VALUES(?, ?, ?, ?, ?, ?, ?)
    """
    cursor.execute(sql, [new_vehicle_key, current_user.u_userkey, plate_no, plate_state, maker, model, color])
    conn.commit()
    conn.close()
    
    # Success - redirect to view vehicles
    return redirect(url_for('view_vehicles'))



# ----------------------------------------------------------------------------------------------------------------------
# --- VIEW/APPLY FOR PERMIT PAGES  ---
# ----------------------------------------------------------------------------------------------------------------------

# -- Display the users permit information --
@app.route('/view_permit')
@login_required
def view_permit():
    conn = sqlite3.connect('instance/data.sqlite')
    cursor = conn.cursor()
    
    # Get user's permits
    cursor.execute("""
        SELECT v.v_plateno, v.v_maker, v.v_model, v.v_color,
               pt.pt_category, pt.pt_duration, p.p_permitnum, 
               p.p_issuedate, p.p_expirationdate
        FROM permit p
        JOIN permitType pt ON pt.pt_permittypekey = p.p_permittypekey
        JOIN vehicles v ON p.p_vehicleskey = v.v_vehicleskey
        WHERE p.p_userkey = ? AND p.p_expirationdate >= DATE('now')
     """
    , [current_user.u_userkey])
    permits = cursor.fetchall()
    conn.close()
    
    has_permit = len(permits) > 0
    
    return render_template('view_permit.html', permits=permits, has_permit=has_permit, username=current_user.username)

# -- Redirect user to the page to apply for a permit --
@app.route('/apply_permit', methods=['GET', 'POST'])
@login_required
def apply_permit():
    return render_template("apply_permit.html", username=current_user.username)



# ----------------------------------------------------------------------------------------------------------------------
# --- MAP PAGE  ---
# ----------------------------------------------------------------------------------------------------------------------



# ----------------------------------------------------------------------------------------------------------------------
# --- APP EXECUTION  ---
# ----------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    resetTheTable = False  

    with app.app_context():
        if (resetTheTable):
            db.drop_all()
        db.create_all()

    print("running locally")
    app.run(port=5001, debug=True)