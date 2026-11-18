from flask import Blueprint, jsonify

from models import User, Exam, Booking
from helpers import login_required

# OPTIONAL FEATURE 1: read-only JSON API (log in as Admin, then open e.g. /api/exams).
api = Blueprint("api", __name__, url_prefix="/api")


def user_to_dict(u):
    return {"id": u.id, "name": u.name, "email": u.email, "department": u.department, "status": u.status}


@api.route("/exams")
@login_required("admin")
def exams():
    return jsonify([{"id": e.id, "name": e.name, "course": e.course.code, "type": e.exam_type,
                     "max_marks": e.max_marks, "status": e.status} for e in Exam.query.all()])


@api.route("/examiners")
@login_required("admin")
def examiners():
    return jsonify([user_to_dict(u) for u in User.query.filter_by(role="examiner").all()])


@api.route("/students")
@login_required("admin")
def students():
    return jsonify([user_to_dict(u) for u in User.query.filter_by(role="student").all()])


@api.route("/bookings")
@login_required("admin")
def bookings():
    return jsonify([{"id": b.id, "student": b.student.name, "exam": b.exam.name,
                     "date": str(b.slot.slot_date), "status": b.status} for b in Booking.query.all()])
