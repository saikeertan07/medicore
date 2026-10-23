from datetime import datetime, timezone

def utc_now() -> datetime:
    """Return timezone-naive UTC datetime compatible with SQLAlchemy naive DateTime columns without Python 3.14 deprecation warnings."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
