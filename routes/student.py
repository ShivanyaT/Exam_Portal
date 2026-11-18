from datetime import date
from flask import (Blueprint, render_template, request, redirect, url_for, session, flash,
                   abort, Response)
from sqlalchemy import or_

from models import db, User, Course, Exam, Slot, Booking, EXAM_TYPES
from helpers import login_required

student = Blueprint("student", __name__, url_prefix="/student")


def me():
    return session["user_id"]


@student.route("/")
@login_required("student")
def dashboard():
    exams = Exam.query.filter_by(status="Booking Open").all()
    slots = Slot.query.join(Exam).filter(Exam.status == "Booking Open", Slot.status == "Available").all()
    mine = Booking.query.filter_by(student_id=me()).all()
    upcoming = [b for b in mine if b.status == "Booked" and b.slot.slot_date >= date.today()]
    results = [b for b in mine if b.status == "Completed" and b.exam.status == "Completed"]
    return render_template("student/dashboard.html", exams=exams, slots=slots,
                           upcoming=upcoming, results=results)


@student.route("/exams")
@login_required("student")
def exams():
    q = request.args.get("q", "").strip()
    kind = request.args.get("type", "")
    query = Exam.query.join(Course).filter(Exam.status != "Draft")
    if q:
        like = "%" + q + "%"
        query = query.filter(or_(Exam.name.ilike(like), Course.name.ilike(like), Course.code.ilike(like)))
    if kind:
        query = query.filter(Exam.exam_type == kind)
    return render_template("student/exams.html", exams=query.all(), q=q, kind=kind, types=EXAM_TYPES)


@student.route("/exam/<int:id>")
@login_required("student")
def exam_detail(id):
    exam = db.get_or_404(Exam, id)
    slots = Slot.query.filter_by(exam_id=id).order_by(Slot.slot_date, Slot.start_time).all()
    already = Booking.query.filter(Booking.student_id == me(), Booking.exam_id == id,
                                   Booking.status.in_(["Booked", "Completed"])).first()
    return render_template("student/exam_detail.html", exam=exam, slots=slots, already=already)


@student.route("/book/<int:slot_id>", methods=["POST"])
@login_required("student")
def book(slot_id):
    slot = db.get_or_404(Slot, slot_id)
    exam = slot.exam
    already = Booking.query.filter(Booking.student_id == me(), Booking.exam_id == exam.id,
                                   Booking.status.in_(["Booked", "Completed"])).first()
    if not exam.can_book():
        flash("Booking is not open for this examination.")
    elif already:
        flash("You already have a booking for this examination.")        # no duplicates
    elif slot.status != "Available" or slot.seats_left() < 1:
        flash("Sorry, this slot is full.")                               # no overbooking
    else:
        db.session.add(Booking(student_id=me(), slot_id=slot.id, exam_id=exam.id))
        if slot.seats_left() == 0:                                       # last seat taken
            slot.status = "Full"
        db.session.commit()
        flash("Slot booked!")
    return redirect(url_for("student.exam_detail", id=exam.id))


@student.route("/cancel/<int:id>", methods=["POST"])
@login_required("student")
def cancel(id):
    booking = db.get_or_404(Booking, id)
    if booking.student_id != me():
        abort(403)
    if booking.status != "Booked":
        flash("Only active bookings can be cancelled.")
    elif date.today() > booking.exam.book_end:
        flash("The booking deadline has passed, so you cannot cancel.")
    else:
        booking.status = "Cancelled"
        if booking.slot.status == "Full":
            booking.slot.status = "Available"                            # seat is free again
        db.session.commit()
        flash("Booking cancelled.")
    return redirect(url_for("student.bookings"))


@student.route("/bookings")
@login_required("student")
def bookings():
    mine = Booking.query.filter_by(student_id=me()).order_by(Booking.id.desc()).all()
    return render_template("student/bookings.html", bookings=mine)


@student.route("/results")
@login_required("student")
def results():
    done = [b for b in Booking.query.filter_by(student_id=me(), status="Completed").all()
            if b.exam.status == "Completed"]                             # published results only
    return render_template("student/results.html", results=done)


@student.route("/scorecard/<int:id>")
@login_required("student")
def scorecard(id):
    """OPTIONAL FEATURE 2: download the result as a text file."""
    b = db.get_or_404(Booking, id)
    if b.student_id != me() or b.status != "Completed" or b.exam.status != "Completed":
        abort(403)
    lines = ["EXAMINATION SCORECARD", "",
             "Student : " + b.student.name,
             "Course  : " + b.exam.course.code + " - " + b.exam.course.name,
             "Exam    : " + b.exam.name + " (" + b.exam.exam_type + ")", ""]
    for s in b.scores:
        lines.append("{:<25} {} / {}".format(s.rubric.name, s.marks, s.rubric.max_marks))
    lines += ["", "TOTAL: {} / {}".format(b.total, b.exam.max_marks), "Remarks: " + (b.remarks or "-")]
    return Response("\n".join(lines), mimetype="text/plain",
                    headers={"Content-Disposition": "attachment; filename=scorecard_" + str(b.id) + ".txt"})


@student.route("/profile", methods=["GET", "POST"])
@login_required("student")
def profile():
    user = db.session.get(User, me())
    if request.method == "POST":
        user.name = request.form["name"].strip()
        user.phone = request.form["phone"]
        user.department = request.form["department"]
        db.session.commit()
        session["name"] = user.name
        flash("Profile updated.")
    return render_template("student/profile.html", user=user)
