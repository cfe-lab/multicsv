

class SubTextIOErrror(Exception):
    """Base class for all SubTextIO custom exceptions."""
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


class EndsBeyondBaseContent(SubTextIOErrror, ValueError):
    pass


class BaseIOClosed(SubTextIOErrror, ValueError):
    pass


class MultiCSVFileError(Exception):
    """Base class for all MultiCSVFile custom exceptions."""
    pass


class OpOnClosedCSVFileError(MultiCSVFileError, ValueError):
    pass


class CSVFileBaseIOClosed(MultiCSVFileError, ValueError):
    pass


class SectionNotFound(MultiCSVFileError, KeyError):
    pass
