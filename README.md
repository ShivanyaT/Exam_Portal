# Examination Management Portal (EMP)

Flask + Jinja2 + Bootstrap + SQLite. No JavaScript is used.

## Run it
```
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000. The database (`instance/emp.db`) is created by the code on the first run.

**Admin login:** `admin@emp.com` / `admin123` (created automatically; there is no admin registration).

## Project structure (what each file does)
| File | Purpose |
|---|---|
| `app.py` | Starts Flask, connects the database, registers the pages, creates tables + the Admin |
| `models.py` | The database tables: User, Course, Exam, Rubric, Slot, Booking, Score |
| `helpers.py` | `login_required("role")` - blocks a page for the wrong role |
| `routes/auth.py` | Login, register, logout |
| `routes/admin.py` | All Admin pages |
| `routes/examiner.py` | All Examiner pages |
| `routes/student.py` | All Student pages |
| `routes/api.py` | Optional feature 1: JSON API |
| `templates/` | HTML pages (Jinja2). `base.html` is the common layout; the rest "extend" it |
| `static/style.css` | The retro (Windows 95) look |

## How the exam timeline works
Admin changes the **status** of an examination:
`Draft` -> `Slot Creation` (examiners can add slots) -> `Booking Open` (students can book)
-> `Closed` -> `Completed` (students can now see their results).
The start/end dates are also checked (slots only inside the slot-creation dates, booking and cancelling only until the booking end date).

## Rules enforced in the code
- Examiner needs Admin approval before they can log in (`status = Pending`).
- Slots can be created only while status is *Slot Creation*, and edited/removed only before booking starts.
- A slot can never hold more students than its capacity; it becomes `Full` automatically and `Available` again after a cancellation.
- A student cannot book the same examination twice.
- An examiner can only open/evaluate bookings of their **own** slots (otherwise 403).
- Admin can reschedule a booking to another slot of the same exam and change a slot's examiner.
- Total marks = sum of marks given per rubric criterion (weightage is stored for information).

## The 2 optional features chosen
1. **JSON API** - log in as Admin, then open `/api/exams`, `/api/examiners`, `/api/students`, `/api/bookings`.
2. **Downloadable scorecard** - Student > Results > "Download scorecard" (a `.txt` file).

## Quick demo order
1. Register an examiner and a student. 2. Admin: approve examiner, add a course, add an exam (assign that examiner), add rubric criteria.
3. Admin: set exam to *Slot Creation*. 4. Examiner: create a slot. 5. Admin: set exam to *Booking Open*.
6. Student: book the slot. 7. Examiner: Slots > Students > Evaluate. 8. Admin: set exam to *Completed*. 9. Student: view results + download scorecard.
