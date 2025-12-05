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
# --- HOME PAGE ROUTE  ---
# ----------------------------------------------------------------------------------------------------------------------

# -- Home page route --
@app.route('/home')
@login_required
def home():
    return render_template("home.html", username=current_user.username)



# ----------------------------------------------------------------------------------------------------------------------
# --- MAP PAGE  ---
# ----------------------------------------------------------------------------------------------------------------------

# -- Redirect user to map page --
@app.route('/map')
@login_required
def map_page():
    return render_template("map.html", username=current_user.username)



# ----------------------------------------------------------------------------------------------------------------------
# --- VIEW/REGISTER VEHICLE PAGE  ---
# ----------------------------------------------------------------------------------------------------------------------

# -- Redirect user to page to display their registered vehicles --
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

# -- Redirect user to page that displays their permit information --
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
        WHERE p.p_userkey = ? AND p.p_expirationdate >= DATE('now', '-08:00')
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
    conn = sqlite3.connect('instance/data.sqlite')
    cursor = conn.cursor()
    
    if request.method == 'GET':
        # Check if user already has an active permit
        cursor.execute("""
            SELECT COUNT(*) FROM permit 
            WHERE p_userkey = ? AND p_expirationdate >= DATE('now', '-08:00')
        """
        , [current_user.u_userkey])
        
        # Check if user has registered any vehicles
        cursor.execute("""
            SELECT COUNT(*) FROM vehicles WHERE v_userkey = ?
        """
        , [current_user.u_userkey])
        
        # Get user's vehicles
        cursor.execute("""
            SELECT v_vehicleskey, v_plateno, v_maker, v_model
            FROM vehicles WHERE v_userkey = ?
            ORDER BY v_vehicleskey DESC
        """
        , [current_user.u_userkey])
        vehicles = cursor.fetchall()
        
        # Get ALL permit types
        cursor.execute("""
            SELECT pt_permittypekey, pt_category, pt_duration 
            FROM permitType
            ORDER BY 
                CASE pt_category
                    WHEN 'Faculty' THEN 1
                    WHEN 'On-Campus Student' THEN 2
                    WHEN 'Off-Campus Student' THEN 3
                    WHEN 'Guest' THEN 4
                END,
                CASE pt_duration
                    WHEN 'Yearly' THEN 1
                    WHEN 'Semester' THEN 2
                    WHEN 'Daily' THEN 3
                    WHEN 'Hourly' THEN 4
                END
        """)
        permit_types = cursor.fetchall()
        
        conn.close()
        
        return render_template('apply_permit.html', vehicles=vehicles, permit_types=permit_types, username=current_user.username)
    
    # POST: Process permit application
    vehicle_key = request.form.get('vehicle_key')
    permit_type_key = request.form.get('permit_type_key')
    permit_category = request.form.get('permit_category')  # We get this too now
    
    if not all([vehicle_key, permit_type_key, permit_category]):
        error = "Please complete all steps: select vehicle, category, and duration."
        
        cursor.execute("""
            SELECT v_vehicleskey, v_plateno, v_maker, v_model
            FROM vehicles WHERE v_userkey = ?
        """, [current_user.u_userkey])
        vehicles = cursor.fetchall()
        
        cursor.execute("""
            SELECT pt_permittypekey, pt_category, pt_duration 
            FROM permitType
            ORDER BY pt_category, pt_duration
        """)
        permit_types = cursor.fetchall()
        
        conn.close()
        
        return render_template('apply_permit.html', vehicles=vehicles, permit_types=permit_types, error=error, username=current_user.username)
    
    # Verify vehicle belongs to user
    cursor.execute("""
        SELECT COUNT(*) FROM vehicles 
        WHERE v_vehicleskey = ? AND v_userkey = ?
    """, [vehicle_key, current_user.u_userkey])
    
    if cursor.fetchone()[0] == 0:
        conn.close()
        return render_template('error.html', message="Invalid vehicle selection.", username=current_user.username)
    
    # Get the permit type to verify category matches and get duration
    cursor.execute("""
        SELECT pt_category, pt_duration FROM permitType 
        WHERE pt_permittypekey = ?
    """, [permit_type_key])
    
    result = cursor.fetchone()
    if not result:
        conn.close()
        return render_template('error.html', message="Invalid permit type selection.", username=current_user.username)
    
    db_category, permit_duration = result
    
    # Verify the category matches (security check)
    if db_category != permit_category:
        conn.close()
        return render_template('error.html', message="Permit type does not match selected category.", username=current_user.username)
    
    # Determine expiration date based on duration
    if permit_duration == 'Yearly':
        expiration_date = '2026-05-19'
    elif permit_duration == 'Semester':
        expiration_date = '2025-12-23'
    elif permit_duration == 'Daily':
        expiration_date = "DATE('now', '-08:00', '+1 day')"
    elif permit_duration == 'Hourly':
        expiration_date = "DATE('now', '-08:00')"
    else:
        conn.close()
        return render_template('error.html', message="Unknown permit duration type.", username=current_user.username)
    
    # Get next permit key
    cursor.execute("SELECT MAX(p_permitkey) FROM permit")
    max_key = cursor.fetchone()[0]
    new_permit_key = (max_key or 0) + 1
    
    # Generate permit number
    permit_num = f'PRM{new_permit_key:04d}'
    
    # Insert permit with correct expiration date
    if permit_duration in ['Yearly', 'Semester']:
        sql = """
            INSERT INTO permit(p_permitkey, p_userkey, p_vehicleskey, p_permittypekey, 
                              p_permitnum, p_issuedate, p_expirationdate)
            VALUES(?, ?, ?, ?, ?, DATE('now', '-08:00'), ?)
        """
        cursor.execute(sql, [new_permit_key, current_user.u_userkey, vehicle_key, 
                            permit_type_key, permit_num, expiration_date])
    else:
        sql = f"""
            INSERT INTO permit(p_permitkey, p_userkey, p_vehicleskey, p_permittypekey, 
                              p_permitnum, p_issuedate, p_expirationdate)
            VALUES(?, ?, ?, ?, ?, DATE('now', '-08:00'), {expiration_date})
        """
        cursor.execute(sql, [new_permit_key, current_user.u_userkey, vehicle_key, 
                            permit_type_key, permit_num])
    
    conn.commit()
    conn.close()
    
    return redirect(url_for('view_permit'))



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