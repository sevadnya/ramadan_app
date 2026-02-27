from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from apscheduler.schedulers.background import BackgroundScheduler
import requests
from datetime import datetime

import calendar

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ================= DATABASE =================

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ================= LOCATION DETECTION =================

def get_location():
    try:
        response = requests.get("http://ip-api.com/json/")
        data = response.json()
        return data["city"], data["country"]
    except:
        return "Pune", "India"  # fallback

@app.route("/calendar")
@login_required
def monthly_calendar():
    city, country = get_location()

    now = datetime.now()
    month = now.month
    year = now.year

    url = "http://api.aladhan.com/v1/calendarByCity"
    params = {
         "city": "Pune",
        "country": "India",
          "method": 2,
        "month": month,
        "year": year
    }

    response = requests.get(url, params=params)
    data = response.json()

    calendar_data = data["data"]

    return render_template(
        "calendar.html",
        calendar_data=calendar_data,
        city=city,
        country=country,
        month=calendar.month_name[month],
        year=year
    )

# ================= PRAYER API =================

def get_prayer_times(city, country):
    url = "http://api.aladhan.com/v1/timingsByCity"
    params = {"city": city, "country": country, "method": 2}
    response = requests.get(url, params=params)
    data = response.json()
    return data["data"]["timings"]

# ================= ROUTES =================

@app.route("/")
@login_required
def home():
    city, country = get_location()
    timings = get_prayer_times(city, country)
    today = datetime.now().strftime("%d %B %Y")

    return render_template(
        "index.html",
        timings=timings,
        today=today,
        city=city,
        country=country
    )

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        hashed_pw = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        user = User(username=request.form['username'], password=hashed_pw)
        db.session.add(user)
        db.session.commit()
        flash("Account created! Please login.")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form['username']).first()
        if user and bcrypt.check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for("home"))
        flash("Login failed")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ================= MAIN =================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)
