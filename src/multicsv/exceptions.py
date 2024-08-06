

class SubTextIOErrror(Exception):
    """Base class for all cigar-related custom exceptions."""
    pass


class OpOnClosedError(SubTextIOErrror, ValueError):
    pass


class InvalidWhenceError(SubTextIOErrror, ValueError):
    pass
