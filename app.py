from flask import Flask, session
from werkzeug.security import generate_password_hash
from models import db, User
from routes.auth import auth
from routes.admin import admin
from routes.examiner import examiner
from routes.student import student
from routes.api import api

app = Flask(__name__)
app.config["SECRET_KEY"] = "emp-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///emp.db"   # SQLite file
db.init_app(app)
for blueprint in (auth, admin, examiner, student, api):
    app.register_blueprint(blueprint)
@app.context_processor
def inject_user():
    return {"role": session.get("role"), "user_name": session.get("name")}
with app.app_context():
    db.create_all()
    if not User.query.filter_by(role="admin").first():
        db.session.add(User(email="admin@emp.com", name="Admin", role="admin",
                            password=generate_password_hash("admin123")))
        db.session.commit()

if __name__ == "__main__":
    app.run(debug=True)
