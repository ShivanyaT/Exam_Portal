from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy import or_
from werkzeug.security import generate_password_hash

from models import db, User, Course, Exam, Rubric, Slot, Booking, EXAM_TYPES, EXAM_STATUSES
from helpers import login_required

admin = Blueprint("admin", __name__, url_prefix="/admin")
#dashb
@admin.route("/")
@login_required("admin")
def dashboard():
    counts = {
        "Courses": Course.query.count(),
        "Examinations": Exam.query.count(),
        "Examiners": User.query.filter_by(role="examiner").count(),
        "Students": User.query.filter_by(role="student").count(),
        "Examination Slots": Slot.query.count(),
        "Bookings": Booking.query.count(),
    }
    pending = User.query.filter_by(role="examiner", status="Pending").count()
    return render_template("admin/dashboard.html", counts=counts, pending=pending)


# course
@admin.route("/courses")
@login_required("admin")
def courses():
    return render_template("admin/courses.html", courses=Course.query.all())


@admin.route("/course/new", methods=["GET", "POST"])
@admin.route("/course/<int:id>/edit", methods=["GET", "POST"])
@login_required("admin")
def course_form(id=None):
    course = db.get_or_404(Course, id) if id else None      # None means "new course"
    if request.method == "POST":
        f = request.form
        code = f["code"].strip().upper()
        same_code = Course.query.filter_by(code=code).first()
        if same_code and same_code != course:
            flash("This course code already exists.")
        else:
            if not course:
                course = Course()
                db.session.add(course)
            course.code = code
            course.name = f["name"].strip()
            course.description = f["description"]
            course.status = f["status"]
            db.session.commit()
            flash("Course saved.")
            return redirect(url_for("admin.courses"))
    return render_template("admin/course_form.html", course=course)


@admin.route("/course/<int:id>/delete", methods=["POST"])
@login_required("admin")
def course_delete(id):
    course = db.get_or_404(Course, id)
    if course.exams:
        flash("Cannot delete: this course has examinations. Set it to Inactive instead.")
    else:
        db.session.delete(course)
        db.session.commit()
        flash("Course deleted.")
    return redirect(url_for("admin.courses"))


# exam
@admin.route("/exams")
@login_required("admin")
def exams():
    return render_template("admin/exams.html", exams=Exam.query.all(), statuses=EXAM_STATUSES)


@admin.route("/exam/new", methods=["GET", "POST"])
@admin.route("/exam/<int:id>/edit", methods=["GET", "POST"])
@login_required("admin")
def exam_form(id=None):
    exam = db.get_or_404(Exam, id) if id else None
    if request.method == "POST":
        f = request.form
        d = [date.fromisoformat(f[k]) for k in ("slot_start", "slot_end", "book_start", "book_end")]
        if d[1] < d[0] or d[3] < d[2]:
            flash("An end date cannot be before its start date.")
        else:
            if not exam:
                exam = Exam()
                db.session.add(exam)
            exam.course_id = int(f["course_id"])
            exam.examiner_id = int(f["examiner_id"]) if f["examiner_id"] else None
            exam.name = f["name"].strip()
            exam.exam_type = f["exam_type"]
            exam.duration = int(f["duration"])
            exam.max_marks = int(f["max_marks"])
            exam.slot_start, exam.slot_end, exam.book_start, exam.book_end = d
            db.session.commit()
            flash("Examination saved.")
            return redirect(url_for("admin.exams"))
    examiners = User.query.filter_by(role="examiner", status="Approved").all()
    return render_template("admin/exam_form.html", exam=exam, courses=Course.query.all(),
                           examiners=examiners, types=EXAM_TYPES)


@admin.route("/exam/<int:id>/status", methods=["POST"])
@login_required("admin")
def exam_status(id):
    """Draft -> Slot Creation (examiners can add slots) -> Booking Open (students can book)
       -> Closed -> Completed (results become visible to students)."""
    exam = db.get_or_404(Exam, id)
    if request.form["status"] in EXAM_STATUSES:
        exam.status = request.form["status"]
        db.session.commit()
        flash("Status changed to " + exam.status + ".")
    return redirect(url_for("admin.exams"))


@admin.route("/exam/<int:id>/delete", methods=["POST"])
@login_required("admin")
def exam_delete(id):
    exam = db.get_or_404(Exam, id)
    if exam.slots:
        flash("Cannot delete: this examination already has slots.")
    else:
        for r in exam.rubrics:
            db.session.delete(r)
        db.session.delete(exam)
        db.session.commit()
        flash("Examination deleted.")
    return redirect(url_for("admin.exams"))


#rubrics
@admin.route("/exam/<int:id>/rubrics", methods=["GET", "POST"])
@login_required("admin")
def rubrics(id):
    exam = db.get_or_404(Exam, id)
    if request.method == "POST":
        f = request.form
        db.session.add(Rubric(exam_id=id, name=f["name"], max_marks=int(f["max_marks"]),
                              weightage=int(f["weightage"] or 0), description=f["description"]))
        db.session.commit()
        flash("Criterion added.")
    return render_template("admin/rubrics.html", exam=exam)


@admin.route("/rubric/<int:id>/save", methods=["POST"])
@login_required("admin")
def rubric_save(id):
    r = db.get_or_404(Rubric, id)
    f = request.form
    r.name, r.description = f["name"], f["description"]
    r.max_marks, r.weightage = int(f["max_marks"]), int(f["weightage"] or 0)
    db.session.commit()
    flash("Criterion updated.")
    return redirect(url_for("admin.rubrics", id=r.exam_id))


@admin.route("/rubric/<int:id>/delete", methods=["POST"])
@login_required("admin")
def rubric_delete(id):
    r = db.get_or_404(Rubric, id)
    exam_id = r.exam_id
    db.session.delete(r)
    db.session.commit()
    flash("Criterion deleted.")
    return redirect(url_for("admin.rubrics", id=exam_id))

#Examiners and stds 
@admin.route("/examiners")
@login_required("admin")
def examiners():
    return render_template("admin/examiners.html", examiners=User.query.filter_by(role="examiner").all())


@admin.route("/examiners/add", methods=["POST"])
@login_required("admin")
def examiner_add():
    f = request.form
    email = f["email"].strip().lower()
    if User.query.filter_by(email=email).first():
        flash("This email is already registered.")
    else:
        db.session.add(User(email=email, name=f["name"], phone=f["phone"], department=f["department"],
                            role="examiner", status="Approved",
                            password=generate_password_hash(f["password"])))
        db.session.commit()
        flash("Examiner added and approved.")
    return redirect(url_for("admin.examiners"))


@admin.route("/examiner/<int:id>/status", methods=["POST"])
@login_required("admin")
def examiner_status(id):
    user = db.get_or_404(User, id)
    if user.role == "examiner" and request.form["status"] in ("Approved", "Deactivated"):
        user.status = request.form["status"]
        db.session.commit()
        flash("Examiner is now " + user.status + ".")
    return redirect(url_for("admin.examiners"))


@admin.route("/students")
@login_required("admin")
def students():
    return render_template("admin/students.html", students=User.query.filter_by(role="student").all())


# slots and bookings 
@admin.route("/slots")
@login_required("admin")
def slots():
    examiners = User.query.filter_by(role="examiner", status="Approved").all()
    return render_template("admin/slots.html", slots=Slot.query.all(), examiners=examiners)


@admin.route("/slot/<int:id>/examiner", methods=["POST"])
@login_required("admin")
def slot_examiner(id):
    """Exceptional situation: give a slot to another examiner."""
    slot = db.get_or_404(Slot, id)
    slot.examiner_id = int(request.form["examiner_id"])
    db.session.commit()
    flash("Examiner changed for slot " + str(id) + ".")
    return redirect(url_for("admin.slots"))


@admin.route("/bookings")
@login_required("admin")
def bookings():
    return render_template("admin/bookings.html", bookings=Booking.query.order_by(Booking.id.desc()).all())


@admin.route("/booking/<int:id>/reschedule", methods=["GET", "POST"])
@login_required("admin")
def reschedule(id):
    booking = db.get_or_404(Booking, id)
    if booking.status != "Booked":
        flash("Only active bookings can be rescheduled.")
        return redirect(url_for("admin.bookings"))
    if request.method == "POST":
        new = db.get_or_404(Slot, int(request.form["slot_id"]))
        if new.exam_id != booking.exam_id or new.status != "Available" or new.seats_left() < 1:
            flash("That slot cannot be used.")
        else:
            old = booking.slot
            booking.slot_id = new.id
            if old.status == "Full":
                old.status = "Available"          # the old slot has a free seat again
            if new.seats_left() == 0:
                new.status = "Full"
            db.session.commit()
            flash("Booking moved to slot " + str(new.id) + ".")
            return redirect(url_for("admin.bookings"))
    options = Slot.query.filter(Slot.exam_id == booking.exam_id, Slot.status == "Available",
                                Slot.id != booking.slot_id).all()
    return render_template("admin/reschedule.html", booking=booking, options=options)


# search
@admin.route("/search")
@login_required("admin")
def search():
    q = request.args.get("q", "").strip()
    found = {}
    if q:
        like = "%" + q + "%"
        num = int(q) if q.isdigit() else -1               # lets you search by ID too
        people = User.query.filter(or_(User.name.ilike(like), User.id == num))
        found["students"] = people.filter_by(role="student").all()
        found["examiners"] = people.filter_by(role="examiner").all()
        found["exams"] = Exam.query.filter(or_(Exam.name.ilike(like), Exam.id == num)).all()
        found["bookings"] = (Booking.query.join(User, Booking.student_id == User.id)
                             .filter(or_(User.name.ilike(like), Booking.id == num)).all())
    return render_template("admin/search.html", q=q, found=found)
