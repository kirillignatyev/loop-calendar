class CalendarError(Exception):
    """Base class for expected user-facing calendar errors."""


class InvalidCommand(CalendarError):
    pass


class EventConflict(CalendarError):
    pass


class EventNotFound(CalendarError):
    pass


class PermissonDenied(CalendarError):
    pass
