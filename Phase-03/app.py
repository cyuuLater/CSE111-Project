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


# -- Get the parking data --
@app.route('/api/parking-data')
@login_required
def parking_data():
    conn = sqlite3.connect('instance/data.sqlite')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT s.s_num, s.s_latitude, s.s_longitude, s.s_status, s.s_isactive, z.z_type, l.l_name
        FROM spots s
        JOIN zone z ON s.s_zonekey = z.z_zonekey
        JOIN lot l ON s.s_lotkey = l.l_lotkey
        ORDER BY l.l_name, s.s_num
    """)
    
    spots = []
    for row in cursor.fetchall():
        spots.append({
            'spot_num': row[0],
            'latitude': row[1],
            'longitude': row[2],
            'is_occupied': bool(row[3]),  # s_status: 0=available, 1=occupied
            'is_active': bool(row[4]),
            'zone_type': row[5],
            'lot_name': row[6]
        })
    
    conn.close()
    return jsonify(spots)


# -- User claims a spot --
@app.route('/claim-spot/<spot_num>', methods=['POST'])
@login_required
def claim_spot(spot_num):
    
    conn = sqlite3.connect('instance/data.sqlite')
    cursor = conn.cursor()

    # 1. Get Active Permit Details and Vehicle Key
    cursor.execute("""
        SELECT p.p_permitkey, p.p_vehicleskey, pt.pt_category, p.p_expirationdate 
        FROM permit p
        JOIN permitType pt ON p.p_permittypekey = pt.pt_permittypekey
        WHERE p.p_userkey = ? AND p.p_expirationdate >= DATETIME('now', '-08:00')
    """, [current_user.u_userkey])
    
    permit_result = cursor.fetchone()
    if not permit_result:
        conn.close()
        return jsonify({'success': False, 'message': 'You do not have an active permit.'}), 403
    
    permit_key, vehicle_key, permit_category, permit_expiry = permit_result

    # 2. Check if user is already parked somewhere (using the vehicle key)
    cursor.execute("""
        SELECT ph_spotskey, s.s_num
        FROM parkingHistory ph
        JOIN spots s ON ph.ph_spotskey = s.s_spotskey
        WHERE ph_vehicleskey = ? AND ph_departuretime IS NULL
    """, [vehicle_key])
    
    if cursor.fetchone():
        conn.close()
        return jsonify({'success': False, 'message': 'You are already parked elsewhere.'}), 400

    # 3. Get Spot Details and check availability/activation status
    cursor.execute("""
        SELECT s.s_spotskey, s.s_status, s.s_isactive, s.s_zonekey, s.s_lotkey, z.z_type, l.l_name
        FROM spots s
        JOIN zone z ON s.s_zonekey = z.z_zonekey
        JOIN lot l ON s.s_lotkey = l.l_lotkey
        WHERE s.s_num = ?
    """, [spot_num])
    
    spot_result = cursor.fetchone()
    if not spot_result:
        conn.close()
        return jsonify({'success': False, 'message': 'Spot not found.'}), 404
    
    spot_key, is_occupied, is_active, spot_zone_key, lot_key, spot_zone_type, lot_name = spot_result
    
    # Basic Spot Checks
    if is_occupied == 1:
        conn.close()
        return jsonify({'success': False, 'message': 'This spot is already occupied.'}), 400
    if is_active == 0:
        conn.close()
        return jsonify({'success': False, 'message': 'This spot is currently inactive.'}), 400

    # 4. Validate against the zoneAssignment M:N table (Is the assignment active?)
    cursor.execute("""
        SELECT za_isactive
        FROM zoneAssignment
        WHERE za_lotkey = ? AND za_zonekey = ?
    """, [lot_key, spot_zone_key])

    assignment_active = cursor.fetchone()
    if not assignment_active or assignment_active[0] == 0:
        conn.close()
        return jsonify({
            'success': False,
            'message': f'Parking in the {spot_zone_type} Zone of Lot {lot_name} is currently suspended.'
        }), 403

    # 5. Validate against Permit Category (Does the permit allow this zone?) 
    can_park = False
    if spot_zone_type == 'Green':
        can_park = True
    elif spot_zone_type == 'Gold' and permit_category == 'Faculty':
        can_park = True
    elif spot_zone_type == 'H' and permit_category == 'On-Campus Student':
        can_park = True
    
    if not can_park:
        conn.close()
        return jsonify({
            'success': False, 
            'message': f'Your {permit_category} permit does not allow parking in {spot_zone_type} Zone.'
        }), 403
    
    # 6. Claim the Spot (Insert parkingHistory and Update Spot status)
    # Insert into parkingHistory (Find next key)
    cursor.execute("SELECT MAX(ph_parkinghistkey) FROM parkingHistory")
    new_history_key = (cursor.fetchone()[0] or 0) + 1
    
    cursor.execute("""
        INSERT INTO parkingHistory(ph_parkinghistkey, ph_vehicleskey, ph_spotskey, 
                                   ph_arrivaltime, ph_departuretime)
        VALUES(?, ?, ?, DATETIME('now', '-08:00'), NULL)
    """, [new_history_key, vehicle_key, spot_key])
    
    # Update spot status to occupied (1)
    cursor.execute("""
        UPDATE spots
        SET s_status = 1
        WHERE s_spotskey = ?
    """, [spot_key])
    
    conn.commit()
    conn.close()

    return jsonify({
        'success': True, 
        'message': f'Successfully claimed spot {spot_num} in {lot_name}!',
        'spot': spot_num,
        'lot': lot_name,
        'zone': spot_zone_type
    }), 200


# -- User unclaims a spot -- 
@app.route('/unclaim-spot', methods=['POST'])
@login_required
def unclaim_spot():
    conn = sqlite3.connect('instance/data.sqlite')
    cursor = conn.cursor()
    
    # Check if user has an active permit with a vehicle
    cursor.execute("""
        SELECT p.p_vehicleskey
        FROM permit p
        WHERE p.p_userkey = ? AND p.p_expirationdate >= DATETIME('now', '-08:00')
    """, [current_user.u_userkey])
    
    permit_result = cursor.fetchone()
    if not permit_result:
        conn.close()
        return jsonify({'success': False, 'message': 'You do not have an active permit.'}), 403
    
    vehicle_key = permit_result[0]
    
    # Find current parking spot
    cursor.execute("""
        SELECT ph.ph_parkinghistkey, ph.ph_spotskey, s.s_num, l.l_name
        FROM parkingHistory ph
        JOIN spots s ON ph.ph_spotskey = s.s_spotskey
        JOIN lot l ON s.s_lotkey = l.l_lotkey
        WHERE ph.ph_vehicleskey = ? AND ph.ph_departuretime IS NULL
    """, [vehicle_key])
    
    parking_result = cursor.fetchone()
    if not parking_result:
        conn.close()
        return jsonify({'success': False, 'message': 'You are not currently parked anywhere.'}), 400
    
    history_key, spot_key, spot_num, lot_name = parking_result
    
    # Update departure time
    cursor.execute("""
        UPDATE parkingHistory
        SET ph_departuretime = DATETIME('now', '-08:00')
        WHERE ph_parkinghistkey = ?
    """, [history_key])
    
    # Free the spot
    cursor.execute("""
        UPDATE spots
        SET s_status = 0
        WHERE s_spotskey = ?
    """, [spot_key])
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True, 
        'message': f'Successfully unclaimed spot {spot_num} in {lot_name}.',
        'spot': spot_num,
        'lot': lot_name
    })


# -- Get current parking status for logged-in user --
@app.route('/my-parking-status')
@login_required
def my_parking_status():
    conn = sqlite3.connect('instance/data.sqlite')
    cursor = conn.cursor()
    
    # Check if user has active permit
    cursor.execute("""
        SELECT p.p_vehicleskey
        FROM permit p
        WHERE p.p_userkey = ? AND p.p_expirationdate >= DATETIME('now', '-08:00')
    """, [current_user.u_userkey])
    
    permit_result = cursor.fetchone()
    if not permit_result:
        conn.close()
        return jsonify({'has_permit': False, 'is_parked': False})
    
    vehicle_key = permit_result[0]
    
    # Check if currently parked
    cursor.execute("""
        SELECT s.s_num, l.l_name, z.z_type, ph.ph_arrivaltime
        FROM parkingHistory ph
        JOIN spots s ON ph.ph_spotskey = s.s_spotskey
        JOIN lot l ON s.s_lotkey = l.l_lotkey
        JOIN zone z ON s.s_zonekey = z.z_zonekey
        WHERE ph.ph_vehicleskey = ? AND ph.ph_departuretime IS NULL
    """, [vehicle_key])
    
    parking_result = cursor.fetchone()
    conn.close()
    
    if parking_result:
        return jsonify({
            'has_permit': True,
            'is_parked': True,
            'spot': parking_result[0],
            'lot': parking_result[1],
            'zone': parking_result[2],
            'arrival_time': parking_result[3]
        })
    else:
        return jsonify({
            'has_permit': True,
            'is_parked': False
        })



# ----------------------------------------------------------------------------------------------------------------------
# --- VIEW/REGISTER VEHICLE PAGE  ---
# ----------------------------------------------------------------------------------------------------------------------

# -- Redirect user to page to display their registered vehicles --
@app.route('/view_vehicles', methods=['GET', 'POST'])
@login_required
def view_vehicles():
    conn = sqlite3.connect('instance/data.sqlite')
    cursor = conn.cursor()
    error = None
    
    # Handle POST: Delete vehicle
    if request.method == 'POST':
        vehicle_key = request.form.get('vehicle_key')
        
        if vehicle_key:
            # Security: Verify vehicle belongs to current user
            cursor.execute("""
                SELECT COUNT(*) FROM vehicles 
                WHERE v_vehicleskey = ? AND v_userkey = ?
            """, [vehicle_key, current_user.u_userkey])
            
            if cursor.fetchone()[0] == 0:
                error = "Invalid vehicle selection."
            else:
                # Check if vehicle is connected to an active permit
                cursor.execute("""
                    SELECT COUNT(*) FROM permit 
                    WHERE p_vehicleskey = ? AND p_expirationdate >= DATETIME('now', '-08:00')
                """, [vehicle_key])
                
                if cursor.fetchone()[0] > 0:
                    error = "Cannot delete this vehicle. It is connected to an active permit."
                else:
                    # Safe to delete
                    cursor.execute("""
                        DELETE FROM vehicles 
                        WHERE v_vehicleskey = ? AND v_userkey = ?
                    """, [vehicle_key, current_user.u_userkey])
                    conn.commit()
    
    # GET or after POST: Display vehicles
    cursor.execute("""
        SELECT v_vehicleskey, v_plateno, v_platestate, v_maker, v_model, v_color
        FROM vehicles WHERE v_userkey = ?
        ORDER BY v_vehicleskey DESC
    """, [current_user.u_userkey])
    vehicles = cursor.fetchall()
    conn.close()
    
    return render_template("view_vehicles.html", vehicles=vehicles, error=error, username=current_user.username)


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
    
    # Check if plate number already exists ANYWHERE in the system
    cursor.execute("""
        SELECT v_userkey FROM vehicles 
        WHERE v_plateno = ?
    """, [plate_no])
    
    existing_vehicle = cursor.fetchone()
    
    if existing_vehicle:
        conn.close()
        if existing_vehicle[0] == current_user.u_userkey:
            error = "You already have a vehicle registered with this plate number."
        else:
            error = "This plate number is already registered by another user."
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
@app.route('/view_permit', methods=['GET', 'POST'])
@login_required
def view_permit():
    conn = sqlite3.connect('instance/data.sqlite')
    cursor = conn.cursor()
    error = None
    
    # Handle POST: Delete permit
    if request.method == 'POST':
        permit_key = request.form.get('permit_key')
        
        if permit_key:
            # Security: Verify permit belongs to current user
            cursor.execute("""
                SELECT COUNT(*) FROM permit 
                WHERE p_permitkey = ? AND p_userkey = ?
            """, [permit_key, current_user.u_userkey])
            
            if cursor.fetchone()[0] == 0:
                error = "Invalid permit selection."
            else:
                # Check if vehicle is currently parked
                cursor.execute("""
                    SELECT COUNT(*) FROM parkingHistory ph
                    JOIN permit p ON ph.ph_vehicleskey = p.p_vehicleskey
                    WHERE p.p_permitkey = ? AND ph.ph_departuretime IS NULL
                """, [permit_key])

                if cursor.fetchone()[0] > 0:
                    error = "Cannot delete this permit. The associated vehicle is currently parked."
                else:
                    # Safe to delete
                    cursor.execute("""
                        DELETE FROM permit
                        WHERE p_permitkey = ? AND p_userkey = ?
                    """, [permit_key, current_user.u_userkey])
                    conn.commit()
    
    # Get user's permits
    cursor.execute("""
        SELECT p.p_permitkey, v.v_plateno, v.v_maker, v.v_model, v.v_color,
               pt.pt_category, pt.pt_duration, p.p_permitnum, 
               p.p_issuedate, p.p_expirationdate
        FROM permit p
        JOIN permitType pt ON pt.pt_permittypekey = p.p_permittypekey
        JOIN vehicles v ON p.p_vehicleskey = v.v_vehicleskey
        WHERE p.p_userkey = ? AND p.p_expirationdate >= DATETIME('now', '-08:00')
     """
    , [current_user.u_userkey])
    permits = cursor.fetchall()
    conn.close()
    
    has_permit = len(permits) > 0

    return render_template('view_permit.html', permits=permits, has_permit=has_permit, error=error, username=current_user.username)


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
        """, [current_user.u_userkey])
        
        # Check if user has registered any vehicles
        cursor.execute("""
            SELECT COUNT(*) FROM vehicles WHERE v_userkey = ?
        """, [current_user.u_userkey])
        
        # Get user's vehicles
        cursor.execute("""
            SELECT v_vehicleskey, v_plateno, v_maker, v_model
            FROM vehicles WHERE v_userkey = ?
            ORDER BY v_vehicleskey DESC
        """, [current_user.u_userkey])
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
        expiration_date = "DATETIME('now', '-08:00', '+1 day')"
    elif permit_duration == 'Hourly':
        expiration_date = "DATETIME('now', '-08:00', '+1 hour')"
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
            INSERT INTO permit(p_permitkey, p_userkey, p_vehicleskey, p_permittypekey, p_permitnum, p_issuedate, p_expirationdate)
            VALUES(?, ?, ?, ?, ?, DATETIME('now', '-08:00'), ?)
        """
        cursor.execute(sql, [new_permit_key, current_user.u_userkey, vehicle_key, permit_type_key, permit_num, expiration_date])
    else:
        sql = f"""
            INSERT INTO permit(p_permitkey, p_userkey, p_vehicleskey, p_permittypekey, p_permitnum, p_issuedate, p_expirationdate)
            VALUES(?, ?, ?, ?, ?, DATETIME('now', '-08:00'), {expiration_date})
        """
        cursor.execute(sql, [new_permit_key, current_user.u_userkey, vehicle_key, permit_type_key, permit_num])
    
    conn.commit()
    conn.close()
    
    return redirect(url_for('view_permit'))



# ----------------------------------------------------------------------------------------------------------------------
# --- FUNCTIONS THAT EXECUTE ON RUN  ---
# ----------------------------------------------------------------------------------------------------------------------

# -- Delete any expired permits and forcibly unclaim users parked in a zone that changed on run --
def enforce_time_limits_and_cleanups():
    conn = sqlite3.connect('instance/data.sqlite')
    cursor = conn.cursor()
    
    all_records_to_unclaim = {}

    # 1. FIND EXPIRED PERMITS (Standard Cleanup)
    cursor.execute("""
        SELECT ph.ph_parkinghistkey, ph.ph_spotskey, s.s_num
        FROM parkingHistory ph
        JOIN permit p ON ph.ph_vehicleskey = p.p_vehicleskey 
        JOIN spots s ON ph.ph_spotskey = s.s_spotskey
        WHERE ph.ph_departuretime IS NULL 
            AND p.p_expirationdate < DATETIME('now', '-08:00')
    """)
    for hist_key, spot_key, spot_num in cursor.fetchall():
        all_records_to_unclaim[hist_key] = {'spot_key': spot_key, 'spot_num': spot_num, 'reason': 'PERMIT EXPIRED'}


    # 2. FIND ZONE VIOLATIONS AFTER GRACE PERIOD (NEW Logic)
    # Find active parkers who are in a zone they don't have permission for 
    # AND have been parked for more than 30 minutes (grace period expired).
    cursor.execute("""
        SELECT ph.ph_parkinghistkey, ph.ph_spotskey, s.s_num
        FROM parkingHistory ph
        JOIN permit p ON ph.ph_vehicleskey = p.p_vehicleskey
        JOIN permitType pt ON p.p_permittypekey = pt.pt_permittypekey
        JOIN spots s ON ph.ph_spotskey = s.s_spotskey
        JOIN zone z ON s.s_zonekey = z.z_zonekey
        WHERE ph.ph_departuretime IS NULL 
            AND ph_arrivaltime < DATETIME('now', '-08:00', '-30 minutes') 
            AND ((z.z_type = 'Gold' AND pt.pt_category != 'Faculty') 
                OR (z.z_type = 'H' AND pt.pt_category != 'On-Campus Student'))
    """)
    
    for hist_key, spot_key, spot_num in cursor.fetchall():
        if hist_key not in all_records_to_unclaim:
            all_records_to_unclaim[hist_key] = {'spot_key': spot_key, 'spot_num': spot_num, 'reason': 'MAX_STAY_EXCEEDED_WRONG_ZONE'}

    # 4. PROCESS FORCED UNCLAIM
    if not all_records_to_unclaim:
        print("Enforcer: No spots require forced unclaiming.")
        conn.close()
        return

    print(f"Enforcer: Processing {len(all_records_to_unclaim)} records for forced unclaim.")
    
    for history_key, data in all_records_to_unclaim.items():
        # A. Update parkingHistory: Set departure time
        cursor.execute("""
            UPDATE parkingHistory
            SET ph_departuretime = DATETIME('now', '-08:00')
            WHERE ph_parkinghistkey = ?
        """, [history_key])
        
        # B. Update spots: Set status to 0 (available)
        cursor.execute("""
            UPDATE spots
            SET s_status = 0
            WHERE s_spotskey = ?
        """, [data['spot_key']])
        
        print(f"   -> FORCED UNCLAIM Spot {data['spot_num']} (Reason: {data['reason']})")
        
    conn.commit()
    conn.close()
    print("Enforcer: Finished all enforcement and cleanups.")


# -- Update North Bowl zones based on time of day --
def update_time_based_zones():
    conn = sqlite3.connect('instance/data.sqlite')
    cursor = conn.cursor()
    
    # Get current hour (Pacific Time)
    cursor.execute("SELECT CAST(strftime('%H', 'now', '-08:00') AS INTEGER)")
    current_hour = cursor.fetchone()[0]

    # Nighttime = 7 PM (19) to 6 AM (05)
    is_nighttime = (current_hour >= 19 or current_hour < 6)

    # Zone and Lot Keys:
    gold_zone = 2
    green_zone = 1
    north_bowl = 3

    if is_nighttime:
        print("Nighttime rules: North Bowl (Lot 3) → Green Zone (1) only")

        # 1. UPDATE SPOTS: Change the spot's zone key to Green (s_zonekey = 1)
        cursor.execute("""
            UPDATE spots
            SET s_zonekey = ?, s_isactive = 1 
            WHERE s_lotkey = ? 
        """, (green_zone, north_bowl))

        # 2. UPDATE ZONE ASSIGNMENT: Activate Green (1), Deactivate Gold (2) for Lot 3
        cursor.execute("""
            UPDATE zoneAssignment SET za_isactive = 1
            WHERE za_lotkey = ? AND za_zonekey = ?
        """, (north_bowl, green_zone))

        cursor.execute("""
            UPDATE zoneAssignment SET za_isactive = 0
            WHERE za_lotkey = ? AND za_zonekey = ?
        """, (north_bowl, gold_zone))

    else:
        print("Daytime rules: North Bowl (Lot 3) → Gold Zone (2) only")
        
        # 1. UPDATE SPOTS: Change the spot's zone key to Gold (s_zonekey = 2)
        cursor.execute("""
            UPDATE spots
            SET s_zonekey = ?, s_isactive = 1 
            WHERE s_lotkey = ? 
        """, (gold_zone, north_bowl))

        # 2. UPDATE ZONE ASSIGNMENT: Activate Gold (2), Deactivate Green (1) for Lot 3
        cursor.execute("""
            UPDATE zoneAssignment SET za_isactive = 1
            WHERE za_lotkey = ? AND za_zonekey = ?
        """, (north_bowl, gold_zone))

        cursor.execute("""
            UPDATE zoneAssignment SET za_isactive = 0
            WHERE za_lotkey = ? AND za_zonekey = ?
        """, (north_bowl, green_zone))
        
    conn.commit()
    conn.close()


# -- Identifies vehicles that are currently parked but whose permit has expired, --
#    and automatically sets their departure time and frees the spot.             
def unclaim_expired_spots():
    conn = sqlite3.connect('instance/data.sqlite')
    cursor = conn.cursor()
    
    # Find Active Parking Records with Expired Permits
    cursor.execute("""
        SELECT ph.ph_parkinghistkey, ph.ph_spotskey, s.s_num, p.p_permitkey
        FROM parkingHistory ph
        JOIN permit p ON ph.ph_vehicleskey = p.p_vehicleskey 
        JOIN spots s ON ph.ph_spotskey = s.s_spotskey
        WHERE ph.ph_departuretime IS NULL 
            AND p.p_expirationdate < DATETIME('now', '-08:00')
    """)
    
    expired_parked_records = cursor.fetchall()
    
    if not expired_parked_records:
        print("Scheduler: No expired permits found for currently parked vehicles.")
        conn.close()
        return

    print(f"Scheduler: Found {len(expired_parked_records)} expired parked records to unclaim.")
    
    # Process Expirations and Update Database
    for history_key, spot_key, spot_num, permit_key in expired_parked_records:
        # Update parkingHistory: Set departure time
        cursor.execute("""
            UPDATE parkingHistory
            SET ph_departuretime = DATETIME('now', '-08:00')
            WHERE ph_parkinghistkey = ?
        """, [history_key])
        
        # Update spots: Set status to 0 (available)
        cursor.execute("""
            UPDATE spots
            SET s_status = 0
            WHERE s_spotskey = ?
        """, [spot_key])     
        print(f"   -> Automatically unclaimed Spot {spot_num} (History {history_key}, Permit {permit_key})")
        
    conn.commit()
    conn.close()
    print("Scheduler: Finished automatic spot unclaiming.")


# -- Deletes records from parkingHistory where the session is complete AND the departure time is older than 24 hours. --
def delete_old_parking_records():
    conn = sqlite3.connect('instance/data.sqlite')
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM parkingHistory
        WHERE ph_departuretime IS NOT NULL  
            AND ph_departuretime < DATETIME('now', '-08:00', '-24 hours')
    """)
    
    conn.commit()
    conn.close()



# ----------------------------------------------------------------------------------------------------------------------
# --- APP EXECUTION  ---
# ----------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    resetTheTable = False  

    with app.app_context():
        if (resetTheTable):
            db.drop_all()
        db.create_all()

    enforce_time_limits_and_cleanups()
    update_time_based_zones()
    unclaim_expired_spots()
    delete_old_parking_records()

    print("running locally")
    app.run(port=5001, debug=True)