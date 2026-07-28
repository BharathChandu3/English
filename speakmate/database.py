from contextlib import contextmanager
from speakmate.models import db

def init_db(app=None):
    """Initializes Flask-SQLAlchemy database and creates tables."""
    if app is not None:
        db.init_app(app)
        with app.app_context():
            db.create_all()

@contextmanager
def get_db_context():
    """
    Context manager yielding SQLAlchemy db.session with automatic commit/rollback.
    """
    try:
        yield db.session
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
