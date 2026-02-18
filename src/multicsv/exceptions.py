

class MultiCSVFileError(Exception):
    """Base class for all MultiCSVFile custom exceptions."""
    pass


class OpOnClosedCSVFileError(MultiCSVFileError, ValueError):
    pass


class CSVFileBaseIOClosed(MultiCSVFileError, ValueError):
    pass


class SectionNotFound(MultiCSVFileError, KeyError):
    pass
