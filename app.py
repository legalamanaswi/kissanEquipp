from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session,flash
from flask_mysqldb import MySQL

app = Flask(__name__)

# ✅ ADD HERE
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Secret key for sessions
app.secret_key = "kissan_secret"

# MySQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'manaswi'
app.config['MYSQL_DB'] = 'kissanequipp'

mysql = MySQL(app)


# ===============================
# HOME PAGE
# ===============================

@app.route('/')
def home():
    return render_template("index.html")

#about 
@app.route('/about')
def about():
    return render_template('about.html')


# ===============================
# REGISTER PAGE
# ===============================

@app.route('/register', methods=['GET','POST'])
def register():

    if request.method == 'POST':

        name = request.form['name']
        mobile = request.form['mobile']
        village = request.form.get('village')
        district = request.form.get('district')
        state = request.form.get('state')
        land = request.form.get('land_acres')
        equipment = request.form.get('equipment_type')
        password = request.form['password']
        role = request.form['role']

        cursor = mysql.connection.cursor()

        cursor.execute("""
        INSERT INTO users
        (name, mobile, village, district, state, land_acres, equipment_type, password, role)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,(name, mobile, village, district, state, land, equipment, password, role))

        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('login'))

    # VERY IMPORTANT
    return render_template("register.html")




@app.route('/login', methods=['GET','POST'])
def login():

    if request.method == 'POST':

        mobile = request.form['mobile']
        password = request.form['password']
        role = request.form['role']

        cursor = mysql.connection.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE mobile=%s AND password=%s AND role=%s",
            (mobile, password, role)
        )

        user = cursor.fetchone()

        cursor.close()

        if user:
            session['loggedin'] = True
            session['user_id'] = user[0]
            session['name'] = user[1]
            session['role'] = user[9]

            if role == "owner":
                return redirect(url_for('owner_dashboard'))
            else:
                return redirect(url_for('farmer_dashboard'))

        else:
            return "Invalid Login"

    return render_template("login.html")

# ===============================
# OWNER DASHBOARD
# ===============================

@app.route('/owner_dashboard')
def owner_dashboard():

    if 'loggedin' in session and session['role'] == "owner":

        cursor = mysql.connection.cursor()

        owner_id = session['user_id']

        # Total equipment
        cursor.execute(
            "SELECT COUNT(*) FROM equipment WHERE owner_id=%s",
            (owner_id,)
        )
        total_equipment = cursor.fetchone()[0]

        # Pending bookings
        cursor.execute(
            "SELECT COUNT(*) FROM bookings WHERE owner_id=%s AND status='pending'",
            (owner_id,)
        )
        pending_bookings = cursor.fetchone()[0]

        # Total bookings
        cursor.execute(
            "SELECT COUNT(*) FROM bookings WHERE owner_id=%s",
            (owner_id,)
        )
        total_bookings = cursor.fetchone()[0]

        # Equipment list
        cursor.execute(
            "SELECT id,name,price,location FROM equipment WHERE owner_id=%s",
            (owner_id,)
        )
        equipment = cursor.fetchall()

        # Recent bookings
        cursor.execute("""
        SELECT farmer_name,equipment_name,booking_date,amount,status
        FROM bookings
        WHERE owner_id=%s
        ORDER BY booking_date DESC
        LIMIT 5
        """,(owner_id,))

        bookings = cursor.fetchall()

        cursor.close()

        return render_template(
            "owner_dashboard.html",
            name=session['name'],
            total_equipment=total_equipment,
            total_bookings=total_bookings,
            pending_bookings=pending_bookings,
            equipment=equipment,
            bookings=bookings
        )

    return redirect(url_for('login'))
# ===============================
# FARMER DASHBOARD
# ===============================

@app.route('/farmer_dashboard')
def farmer_dashboard():

    if 'loggedin' in session and session['role'] == "farmer":

        cursor = mysql.connection.cursor()

        # GET EQUIPMENT WITH OWNER NAME
        cursor.execute("""
        SELECT e.id, e.name, e.category, e.price, u.name
        FROM equipment e
        JOIN users u ON e.owner_id = u.id
        """)
        equipment = cursor.fetchall()

        # GET BOOKINGS (ONLY IMPORTANT COLUMNS)
        cursor.execute("""
        SELECT equipment_name, booking_date, status
        FROM bookings
        WHERE farmer_name=%s
        ORDER BY booking_date DESC
        """, (session['name'],))
        bookings = cursor.fetchall()

        # COUNT PENDING
        pending_count = sum(1 for b in bookings if b[2] == 'pending')

        cursor.close()

        return render_template(
            "farmer_dashboard.html",
            bookings=bookings,
            equipment=equipment,
            pending_count=pending_count   # IMPORTANT
        )

    return redirect(url_for('login'))






# ===============================
# BOOK EQUIPMENT
# ===============================

# ===============================
# BOOK EQUIPMENT
# ===============================

@app.route('/book_equipment/<int:equipment_id>')
def book_equipment(equipment_id):

    if 'loggedin' in session and session['role'] == "farmer":

        cursor = mysql.connection.cursor()

        # get equipment details
        cursor.execute("""
        SELECT name, price, owner_id 
        FROM equipment 
        WHERE id=%s
        """, (equipment_id,))

        equipment = cursor.fetchone()

        if not equipment:
            return "Equipment not found"

        equipment_name = equipment[0]
        amount = equipment[1]
        owner_id = equipment[2]

        # insert booking
        cursor.execute("""
        INSERT INTO bookings
        (equipment_id, farmer_name, equipment_name, amount, owner_id, booking_date, status)
        VALUES (%s,%s,%s,%s,%s,NOW(),'pending')
        """, (equipment_id, session['name'], equipment_name, amount, owner_id))

        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('farmer_dashboard'))

    return redirect(url_for('login'))

# add equiptment
import os
from werkzeug.utils import secure_filename

# create upload folder config (add at top of file once)
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# add equipment
import os
from werkzeug.utils import secure_filename

@app.route('/add_equipment', methods=['GET', 'POST'])
def add_equipment():

    if 'loggedin' not in session or session['role'] != "owner":
        return redirect(url_for('login'))

    if request.method == 'POST':

        # 📥 FORM DATA
        name = request.form.get('equipment_name')
        category = request.form.get('category')
        price = request.form.get('price_per_day')
        horsepower = request.form.get('horsepower')
        status = request.form.get('status')
        description = request.form.get('description')

        # 📍 LOCATION (NEW)
        lat = request.form.get('lat')
        lng = request.form.get('lng')
        if not lat or not lng:
           return "Please select location on map"
        # 🖼 IMAGE HANDLING
        file = request.files.get('image')
        filename = None

        if file and file.filename != "":
            filename = secure_filename(file.filename)

            upload_folder = app.config.get('UPLOAD_FOLDER', 'static/uploads')

            # create folder if not exists
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            file.save(os.path.join(upload_folder, filename))

        # 👤 OWNER
        owner_id = session['user_id']

        # 💾 DATABASE INSERT
        cursor = mysql.connection.cursor()

        cursor.execute("""
        INSERT INTO equipment
        (name, category, price, horsepower, status, description, owner_id, image, latitude, longitude)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            name,
            category,
            price,
            horsepower,
            status,
            description,
            owner_id,
            filename,
            lat,
            lng
        ))

        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('my_equipment'))

    return render_template("add_equipment.html")


# ===============================
# OWNER BOOKINGS
# ===============================

@app.route('/owner_bookings')
def owner_bookings():

    if 'loggedin' in session and session['role'] == "owner":

        cursor = mysql.connection.cursor()

        owner_id = session['user_id']

        cursor.execute("""
        SELECT id, farmer_name, equipment_name, booking_date, amount, status
        FROM bookings
        WHERE owner_id=%s
        ORDER BY booking_date DESC
        """,(owner_id,))

        bookings = cursor.fetchall()

        cursor.close()

        return render_template(
            "owner_bookings.html",
            bookings=bookings,
            name=session['name']
        )

    return redirect(url_for('login'))


@app.route('/approve_booking/<int:booking_id>')
def approve_booking(booking_id):
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE bookings SET status='confirmed' WHERE id=%s", (booking_id,))
    mysql.connection.commit()
    cursor.close()
    return redirect(url_for('owner_bookings'))


@app.route('/reject_booking/<int:booking_id>')
def reject_booking(booking_id):
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE bookings SET status='cancelled' WHERE id=%s", (booking_id,))
    mysql.connection.commit()
    cursor.close()
    return redirect(url_for('owner_bookings'))


# ===============================
# OWNER EARNINGS
# ===============================

@app.route('/earnings')
def earnings():

    if 'loggedin' in session and session['role'] == "owner":

        cursor = mysql.connection.cursor()

        owner_id = session['user_id']

        # total earnings from approved bookings
        cursor.execute("""
        SELECT SUM(amount)
        FROM bookings
        WHERE owner_id=%s AND status='approved'
        """,(owner_id,))

        total_earnings = cursor.fetchone()[0]

        if total_earnings is None:
            total_earnings = 0

        # recent earning transactions
        cursor.execute("""
        SELECT farmer_name,equipment_name,amount,booking_date
        FROM bookings
        WHERE owner_id=%s AND status='approved'
        ORDER BY booking_date DESC
        """,(owner_id,))

        earnings_list = cursor.fetchall()

        cursor.close()

        return render_template(
            "earnings.html",
            total_earnings=total_earnings,
            earnings_list=earnings_list,
            name=session['name']
        )

    return redirect(url_for('login'))

#

# ===============================
# MY EQUIPMENT
# ===============================

@app.route('/my_equipment')
def my_equipment():

    if 'loggedin' in session and session['role'] == "owner":

        cursor = mysql.connection.cursor()

        owner_id = session['user_id']

        cursor.execute("""
        SELECT id, name, price, location, image, horsepower, description
        FROM equipment
        WHERE owner_id=%s
        """,(owner_id,))
        equipment = cursor.fetchall()

        cursor.close()

        return render_template(
            "owner_equipment.html",   # your template name
            equipment=equipment,
            name=session['name']
        )

    return redirect(url_for('login'))


#owner 
@app.route('/owner_equipment')
def owner_equipment():
    return my_equipment()

#-------profile
@app.route('/profile')
def profile():

    if 'loggedin' in session:

        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT name, mobile, village
            FROM users
            WHERE id = %s
        """, (session['user_id'],))

        user = cursor.fetchone()
        cursor.close()

        return render_template(
            "profile.html",
            name=user[0],
            phone=user[1],
            location=user[2]   # village passed as location
        )

    return redirect(url_for('login'))




#farmer bookings..............

import MySQLdb.cursors

@app.route('/farmer_bookings')
def farmer_bookings():

    if 'loggedin' not in session or session['role'] != "farmer":
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    print("Session Name:", session['name'])

    cursor.execute("""
    SELECT
        b.id,
        e.name AS equipment_name,
        e.category,
        b.start_date,
        b.end_date,
        b.status,
        u.name AS owner_name,
        u.mobile AS owner_phone,
        IFNULL(e.price, 0) AS price_per_day,
        CONCAT(b.village, ', ', b.district) AS location,
        b.booking_date AS created_at,
        IFNULL(DATEDIFF(b.end_date, b.start_date) + 1, 1) AS total_days,
        (IFNULL(e.price,0) * IFNULL(DATEDIFF(b.end_date, b.start_date) + 1, 1)) AS total_amount
    FROM bookings b
    LEFT JOIN equipment e ON b.equipment_id = e.id
    LEFT JOIN users u ON e.owner_id = u.id
    WHERE b.farmer_name = %s
    ORDER BY b.id DESC
    """, (session['name'],))

    bookings = cursor.fetchall()   # ✅ correct position
    cursor.close()

    print("BOOKINGS:", bookings)   # 🔥 ADD THIS

    return render_template(
        "farmer_bookings.html",
        bookings=bookings
    )

# ===============================
# LOGOUT
# ===============================

@app.route('/logout')
def logout():

    session.clear()

    return redirect(url_for('home'))




#--------- equiptment list

@app.route('/equipment_list')
def equipment_list():

    if 'loggedin' in session:

        cursor = mysql.connection.cursor()

        cursor.execute("SELECT * FROM equipment")
        equipment = cursor.fetchall()

        # ✅ ADD THIS HERE 👇
        prices = [e[3] for e in equipment if e[3] is not None]
        avg_price = int(sum(prices) / len(prices)) if prices else 0
        # ✅ END

        cursor.close()

        return render_template(
            "equipment_list.html",
            equipment=equipment,
            name=session['name'],
            avg_price=avg_price   # ✅ ALSO ADD THIS
        )

    return redirect(url_for('login'))



#--update profile
@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'loggedin' in session:

        data = request.get_json()

        name = data['name']
        phone = data['phone']
        village = data['village']
        user_id = session['user_id']

        cursor = mysql.connection.cursor()

        cursor.execute("""
            UPDATE users 
            SET name=%s, mobile=%s, village=%s 
            WHERE id=%s
        """, (name, phone, village, user_id))

        mysql.connection.commit()
        cursor.close()

        # update session also
        session['name'] = name
        session['village'] = village

        return {"success": True}

    return {"success": False}

#browseequiptment -----------------------


import math

@app.route('/browse_equipment')
def browse_equipment():

    if 'loggedin' in session and session['role'] == "farmer":

        cursor = mysql.connection.cursor()

        lat = request.args.get('lat')
        lng = request.args.get('lng')

        # 🔥 IF LOCATION PROVIDED → FILTER NEARBY
        if lat and lng:
            lat = float(lat)
            lng = float(lng)

            cursor.execute("""
            SELECT id, name, price, location, status, horsepower, category, latitude, longitude
            FROM equipment
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            """)

            data = cursor.fetchall()
            nearby = []

            for e in data:
                elat = e[7]
                elng = e[8]

                if elat and elng:
                    distance = math.sqrt((lat - elat)**2 + (lng - elng)**2) * 111

                    if distance <= 10:  # 🔥 10 KM RADIUS
                        nearby.append((*e, round(distance, 2)))

            equipment = nearby

        else:
            # NORMAL LIST
            cursor.execute("""
            SELECT id, name, price, location, status, horsepower, category, latitude, longitude
            FROM equipment
            """)
            equipment = cursor.fetchall()

        cursor.close()

        return render_template(
            "equipment_list.html",
            equipment=equipment,
            name=session['name']
        )

    return redirect(url_for('login'))

#update farmer profile


@app.route('/farmer/update_profile', methods=['POST'])
def update_farmer_profile():

    if 'loggedin' in session and session['role'] == "farmer":

        data = request.get_json()

        name = data.get('name')
        phone = data.get('phone')
        village = data.get('village')
        farm_size = data.get('farm_size')
        try:
          farm_size = int(farm_size)
        except:
          farm_size = None  # 👈 important

        user_id = session['user_id']

        cursor = mysql.connection.cursor()

        cursor.execute("""
            UPDATE users 
            SET name=%s, mobile=%s, village=%s, land_acres=%s
            WHERE id=%s
        """, (name, phone, village, farm_size, user_id))

        mysql.connection.commit()
        cursor.close()

        # update session also
        session['name'] = name

        return {"success": True}

    return {"success": False}

#booking page ________________________

@app.route('/booking/<int:equipment_id>', methods=['GET','POST'])
def booking_page(equipment_id):

    # ✅ REDIRECT IF NOT LOGGED IN
    if 'loggedin' not in session or session['role'] != "farmer":
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()

    # =========================
    # 🔥 HANDLE FORM SUBMIT
    # =========================
    if request.method == 'POST':

        farmer_name = session['name']
        phone = request.form['farmer_phone']
        village = request.form['farmer_village']
        district = request.form['farmer_district']
        start_date = request.form['start_date']
        end_date = request.form['end_date']

        print("Equipment ID:", equipment_id)

        # 🔍 Get equipment details
        cursor.execute("""
        SELECT name, price, owner_id 
        FROM equipment 
        WHERE id=%s
        """, (equipment_id,))

        eq = cursor.fetchone()
        print("EQ RESULT:", eq)

        # ✅ HANDLE NONE ERROR
        if eq is None:
            cursor.close()
            return "Equipment not found", 404

        equipment_name = eq[0]
        price = eq[1]
        owner_id = eq[2]

        # =========================
        # 📅 DATE VALIDATION
        # =========================
        from datetime import datetime

        try:
            d1 = datetime.strptime(start_date, "%Y-%m-%d")
            d2 = datetime.strptime(end_date, "%Y-%m-%d")
        except:
            cursor.close()
            return "Invalid date format"

        if d2 < d1:
            cursor.close()
            return "End date cannot be before start date"

        days = (d2 - d1).days + 1
        amount = price * days

        print("DAYS:", days)
        print("AMOUNT:", amount)

        # =========================
        # 💾 INSERT BOOKING
        # =========================
        cursor.execute("""
INSERT INTO bookings
(equipment_id, farmer_name, equipment_name, amount, owner_id, start_date, end_date, booking_date, status, village, district)
VALUES (%s,%s,%s,%s,%s,%s,%s,NOW(),'pending',%s,%s)
""", (equipment_id, farmer_name, equipment_name, amount, owner_id, start_date, end_date, village, district))
        from flask import flash

        mysql.connection.commit()
        cursor.close()


        flash("Booking successful!", "success")
        return redirect(url_for('booking_page', equipment_id=equipment_id))

    # =========================
    # 🔥 NORMAL PAGE LOAD (GET)
    # =========================
    cursor.execute("""
    SELECT e.id, e.name, e.category, e.price, e.location, e.status, u.name
    FROM equipment e
    JOIN users u ON e.owner_id = u.id
    WHERE e.id=%s
    """, (equipment_id,))

    equipment = cursor.fetchone()
    cursor.close()

    if not equipment:
        return "Equipment not found", 404

    return render_template(
        "booking_page.html",
        equipment=equipment,
        equipment_id=equipment_id
    )
#farmer profile
@app.route('/farmer/profile')
def farmer_profile():

    if 'loggedin' in session and session['role'] == "farmer":

        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT name, mobile, village, land_acres 
            FROM users
            WHERE id = %s
        """, (session['user_id'],))

        farmer = cursor.fetchone()

        # 🔴 ADD THESE 2 LINES HERE
        print("USER ID:", session['user_id'])
        print("FARMER DATA:", farmer)

        cursor.close()

        return render_template(
            "farmer_profile.html",
             name=farmer[0],
    phone=farmer[1],
    location=farmer[2],
    farm_size=farmer[3]

        )

    return redirect(url_for('login'))



#edit and delete equiptment  
@app.route('/edit_equipment/<int:id>', methods=['GET', 'POST'])
def edit_equipment(id):

    if 'loggedin' not in session or session['role'] != "owner":
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()

    # 👉 POST (UPDATE)
    if request.method == 'POST':

        name = request.form['equipment_name']
        category = request.form['category']
        price = request.form['price_per_day']
        horsepower = request.form['horsepower']
        status = request.form['status']
        description = request.form['description']

        cursor.execute("""
        UPDATE equipment
        SET name=%s, category=%s, price=%s, horsepower=%s, status=%s, description=%s
        WHERE id=%s AND owner_id=%s
        """, (name, category, price, horsepower, status, description, id, session['user_id']))

        mysql.connection.commit()

        return redirect(url_for('my_equipment'))

    # 👉 GET (FETCH DATA)
    cursor.execute("""
    SELECT id, name, category, price, horsepower, status, description
    FROM equipment
    WHERE id=%s AND owner_id=%s
    """, (id, session['user_id']))

    equipment = cursor.fetchone()
    cursor.close()

    # 🔒 Safety check
    if not equipment:
        return "Equipment not found ❌"

    return render_template("add_equipment.html", equipment=equipment, edit=True)

@app.route('/delete_equipment/<int:id>', methods=['POST'])
def delete_equipment(id):

    if 'loggedin' not in session or session['role'] != "owner":
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()

    cursor.execute("""
    DELETE FROM equipment 
    WHERE id=%s AND owner_id=%s
    """, (id, session['user_id']))

    mysql.connection.commit()
    cursor.close()

    return redirect(url_for('my_equipment'))

#cancel booking 

@app.route('/cancel_booking/<int:booking_id>')
def cancel_booking(booking_id):

    cursor = mysql.connection.cursor()

    cursor.execute(
        "UPDATE bookings SET status='cancelled' WHERE id=%s",
        (booking_id,)
    )

    mysql.connection.commit()
    cursor.close()

    return redirect(url_for('farmer_bookings'))

#view_booking details
@app.route('/view_booking/<int:id>')
def view_booking(id):

    if 'loggedin' not in session or session['role'] != "owner":
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()

    cursor.execute("""
    SELECT b.id, u.name, u.mobile, e.name, e.category,
           b.start_date, b.end_date, b.status, b.amount
    FROM bookings b
    JOIN users u ON b.farmer_name = u.name
    JOIN equipment e ON b.equipment_id = e.id
    WHERE b.id=%s
    """, (id,))

    booking = cursor.fetchone()
    cursor.close()

    return render_template("view_booking.html", booking=booking)


# ===============================
# RUN SERVER
# ===============================

if __name__ == "__main__":
    app.run(debug=True)

