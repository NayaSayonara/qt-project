from enum import *


class BillStatus(Enum):
    OUTSIDE = auto()
    IN_ESCROW = auto()
    ROUTING_OUT = auto()
    ROUTING_IN = auto()
    INSIDE = auto()
