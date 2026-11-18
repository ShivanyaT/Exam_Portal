from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User

auth = Blueprint("auth", __name__)


@auth.route("/")
def home():
    if session.get("role"):
        return redirect(url_for(session["role"] + ".dashboard"))
    return redirect(url_for("auth.login"))


@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form["email"].strip().lower()).first()
        if not user or not check_password_hash(user.password, request.form["password"]):
            flash("Wrong email or password.")
        elif user.status in ("Pending", "Deactivated"):
            flash("Your account is " + user.status + ". Please contact the Admin.")
        else:
            session.clear()
            session["user_id"] = user.id
            session["role"] = user.role
            session["name"] = user.name
            return redirect(url_for(user.role + ".dashboard"))
    return render_template("login.html")


@auth.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        f = request.form
        email = f["email"].strip().lower()
        if User.query.filter_by(email=email).first():
            flash("This email is already registered.")
        elif len(f["password"]) < 4:
            flash("Password must have at least 4 characters.")
        else:
            role = f["role"] if f["role"] in ("student", "examiner") else "student"
            status = "Pending" if role == "examiner" else "Active"   # examiners need approval
            db.session.add(User(email=email, name=f["name"].strip(), phone=f["phone"],
                                department=f["department"], role=role, status=status,
                                password=generate_password_hash(f["password"])))
            db.session.commit()
            flash("Registered! " + ("Wait for Admin approval, then log in." if role == "examiner"
                                    else "You can log in now."))
            return redirect(url_for("auth.login"))
    return render_template("register.html")


@auth.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
