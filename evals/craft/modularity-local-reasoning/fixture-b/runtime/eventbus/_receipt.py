"""What one publish did, as a value callers can read without knowing how delivery works."""


class Receipt:
    """The outcome of one publish: who received the event and who did not."""

    __slots__ = ("topic", "delivered", "failures", "queued")

    def __init__(self, topic, delivered=(), failures=(), queued=False):
        self.topic = topic
        self.delivered = tuple(delivered)
        self.failures = tuple(failures)
        self.queued = bool(queued)

    @property
    def ok(self):
        """True when every consumer registered for the topic accepted the event."""
        return not self.failures

    @property
    def failed(self):
        """The names of the consumers that did not accept the event."""
        return tuple(name for name, _ in self.failures)

    def __repr__(self):
        return (f"Receipt(topic={self.topic!r}, delivered={self.delivered!r}, "
                f"failures={self.failures!r}, queued={self.queued!r})")
