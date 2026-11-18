from datetime import date
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()
EXAM_TYPES = ["Viva", "Practical", "Project Demo", "Assessment"]
EXAM_STATUSES = ["Draft", "Slot Creation", "Booking Open", "Closed", "Completed"]


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)      
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    department = db.Column(db.String(100))
    role = db.Column(db.String(20), nullable=False)          
    status = db.Column(db.String(20), default="Active") # for examiners it will tel Pending/Approved/Deactivated


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300))
    status = db.Column(db.String(20), default="Active")       # Active/Inactive


class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    examiner_id = db.Column(db.Integer, db.ForeignKey("user.id")) 
    name = db.Column(db.String(100), nullable=False)
    exam_type = db.Column(db.String(30), nullable=False)
    duration = db.Column(db.Integer, nullable=False)       
    max_marks = db.Column(db.Integer, nullable=False)
    slot_start = db.Column(db.Date, nullable=False)           
    slot_end = db.Column(db.Date, nullable=False)
    book_start = db.Column(db.Date, nullable=False)           
    book_end = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default="Draft")
    course = db.relationship("Course", backref="exams")
    examiner = db.relationship("User")
    def can_create_slots(self):
        return self.status == "Slot Creation" and self.slot_start <= date.today() <= self.slot_end
    def can_book(self):
        return self.status == "Booking Open" and self.book_start <= date.today() <= self.book_end
class Rubric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exam.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)         
    max_marks = db.Column(db.Integer, nullable=False)
    weightage = db.Column(db.Integer, default=0)              # in percent 
    description = db.Column(db.String(300))

    exam = db.relationship("Exam", backref="rubrics")


class Slot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exam.id"), nullable=False)
    examiner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    slot_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(5), nullable=False)      # hour:min
    end_time = db.Column(db.String(5), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="Available")   

    exam = db.relationship("Exam", backref="slots")
    examiner = db.relationship("User")

    def booked(self):
        return Booking.query.filter(Booking.slot_id == self.id,
                                    Booking.status.in_(["Booked", "Completed"])).count()

    def seats_left(self):
        return self.capacity - self.booked()


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey("slot.id"), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey("exam.id"), nullable=False)
    booking_date = db.Column(db.Date, default=date.today)
    status = db.Column(db.String(20), default="Booked")       # Booked / Cancelled / Completed
    total = db.Column(db.Float)                               
    remarks = db.Column(db.String(500))

    student = db.relationship("User")
    slot = db.relationship("Slot", backref="bookings")
    exam = db.relationship("Exam")


class Score(db.Model):
    #marks given for ONE rubric criterion of ONE booking.
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("booking.id"), nullable=False)
    rubric_id = db.Column(db.Integer, db.ForeignKey("rubric.id"), nullable=False)
    marks = db.Column(db.Float, nullable=False)

    booking = db.relationship("Booking", backref="scores")
    rubric = db.relationship("Rubric")
