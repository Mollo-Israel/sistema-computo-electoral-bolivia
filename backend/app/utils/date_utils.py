"""
Date and timestamp utilities.
TODO: implement Bolivia timezone (America/La_Paz) aware timestamps.
"""
from datetime import datetime, timezone, timedelta

BOLIVIA_TZ = timezone(timedelta(hours=-4))


def now_bolivia() -> datetime:
    return datetime.now(tz=BOLIVIA_TZ)
