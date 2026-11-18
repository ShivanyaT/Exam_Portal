from functools import wraps
from flask import session, redirect, url_for, flash
def login_required(role):
    def decorator(page):
        @wraps(page)
        def wrapper(*args, **kwargs):
            if session.get("role") != role:
                flash("Please log in with the correct account.")
                return redirect(url_for("auth.login"))
            return page(*args, **kwargs)
        return wrapper
    return decorator
