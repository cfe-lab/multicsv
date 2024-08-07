

class SubTextIOErrror(Exception):
    """Base class for all cigar-related custom exceptions."""
    pass


class OpOnClosedError(SubTextIOErrror, ValueError):
    pass


class InvalidWhenceError(SubTextIOErrror, ValueError):
    pass


class InvalidSubtextCoordinates(SubTextIOErrror, ValueError):
    pass


class BaseMustBeSeakable(SubTextIOErrror, ValueError):
    pass


class BaseMustBeReadable(SubTextIOErrror, ValueError):
    pass


class StartsBeyondBaseContent(SubTextIOErrror, ValueError):
    pass


class BaseIOClosed(SubTextIOErrror, ValueError):
    pass
