from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort

from models import db, Exam, Slot, Booking, Score
from helpers import login_required

examiner = Blueprint("examiner", __name__, url_prefix="/examiner")

BEFORE_BOOKING = ("Draft", "Slot Creation")     # slots can be changed only in these stages


def me():
    return session["user_id"]


@examiner.route("/")
@login_required("examiner")
def dashboard():
    exams = Exam.query.filter_by(examiner_id=me()).all()
    slots = Slot.query.filter_by(examiner_id=me()).all()
    students_booked = sum(s.booked() for s in slots)
    pending = Booking.query.join(Slot).filter(Slot.examiner_id == me(), Booking.status == "Booked").count()
    return render_template("examiner/dashboard.html", exams=exams, slots=slots,
                           students_booked=students_booked, pending=pending, editable=BEFORE_BOOKING)


@examiner.route("/slot/new", methods=["GET", "POST"])
@examiner.route("/slot/<int:id>/edit", methods=["GET", "POST"])
@login_required("examiner")
def slot_form(id=None):
    slot = db.get_or_404(Slot, id) if id else None
    if slot and slot.examiner_id != me():
        abort(403)                                          # not your slot
    if slot and slot.exam.status not in BEFORE_BOOKING:
        flash("Booking has started, so this slot can no longer be changed.")
        return redirect(url_for("examiner.dashboard"))

    if request.method == "POST":
        f = request.form
        exam = slot.exam if slot else db.get_or_404(Exam, int(f["exam_id"]))
        slot_date, start, end, cap = date.fromisoformat(f["slot_date"]), f["start_time"], f["end_time"], int(f["capacity"])
        if exam.examiner_id != me():
            abort(403)                                      # not your exam
        if not slot and not exam.can_create_slots():
            flash("Slot creation is not open for this examination.")
        elif end <= start:
            flash("End time must be after start time.")
        elif cap < 1:
            flash("Capacity must be at least 1.")
        elif slot_date < date.today():
            flash("The date cannot be in the past.")
        else:
            if not slot:
                slot = Slot(exam_id=exam.id, examiner_id=me())
                db.session.add(slot)
            slot.slot_date, slot.start_time, slot.end_time, slot.capacity = slot_date, start, end, cap
            db.session.commit()
            flash("Slot saved.")
            return redirect(url_for("examiner.dashboard"))

    exams = [e for e in Exam.query.filter_by(examiner_id=me()).all() if e.can_create_slots()]
    return render_template("examiner/slot_form.html", slot=slot, exams=exams)


@examiner.route("/slot/<int:id>/delete", methods=["POST"])
@login_required("examiner")
def slot_delete(id):
    slot = db.get_or_404(Slot, id)
    if slot.examiner_id != me():
        abort(403)
    if slot.exam.status not in BEFORE_BOOKING:
        flash("Booking has started, so this slot can no longer be removed.")
    else:
        db.session.delete(slot)
        db.session.commit()
        flash("Slot removed.")
    return redirect(url_for("examiner.dashboard"))


@examiner.route("/slot/<int:id>")
@login_required("examiner")
def slot_students(id):
    slot = db.get_or_404(Slot, id)
    if slot.examiner_id != me():
        abort(403)
    return render_template("examiner/slot_students.html", slot=slot)


@examiner.route("/evaluate/<int:id>", methods=["GET", "POST"])
@login_required("examiner")
def evaluate(id):
    booking = db.get_or_404(Booking, id)
    if booking.slot.examiner_id != me():
        abort(403)                                          # only students in YOUR slots
    if booking.status == "Cancelled":
        flash("This booking was cancelled.")
        return redirect(url_for("examiner.slot_students", id=booking.slot_id))

    rubrics = booking.exam.rubrics
    if request.method == "POST":
        marks = {r.id: float(request.form["marks_" + str(r.id)]) for r in rubrics}
        if any(not 0 <= marks[r.id] <= r.max_marks for r in rubrics):
            flash("Marks must be between 0 and the criterion maximum.")
            return redirect(request.url)
        Score.query.filter_by(booking_id=booking.id).delete()      # replace old marks
        for r in rubrics:
            db.session.add(Score(booking_id=booking.id, rubric_id=r.id, marks=marks[r.id]))
        booking.total = sum(marks.values())
        booking.remarks = request.form["remarks"]
        booking.status = "Completed"
        if not any(b.status == "Booked" for b in booking.slot.bookings):
            booking.slot.status = "Completed"                       # everyone evaluated
        db.session.commit()
        flash("Marks saved.")
        return redirect(url_for("examiner.slot_students", id=booking.slot_id))

    old = {s.rubric_id: s.marks for s in booking.scores}
    return render_template("examiner/evaluate.html", booking=booking, rubrics=rubrics, old=old)
