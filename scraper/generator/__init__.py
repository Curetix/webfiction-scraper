from .generator import ConfigGenerator
from .royalroad import RoyalRoadConfigGenerator


class ElementNotFoundException(Exception):
    pass


class InvalidPageException(Exception):
    pass
