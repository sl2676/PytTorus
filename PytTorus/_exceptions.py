"""Exception classes raised by the compiled extension, PytTorus._torus."""


class TorusExcept(RuntimeError):
    """A fatal Torus error: raised where Torus calls ``TorusError(msgs, index)`` with ``index < 0``.

    This is the Python form of the C++ ``TorusExcept`` struct. (Without it, Torus
    would print the message and end the process.) It is available as
    ``PytTorus._torus.TorusExcept``.

    Attributes:
        msgs: the Torus error message.
        index: the Torus error code; negative for fatal errors.
    """

    def __init__(self, msgs, index):
        super().__init__(msgs, index)
        self.msgs = msgs
        self.index = index

    def __str__(self):
        return f"{self.msgs} (index {self.index})"
