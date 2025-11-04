"""Helper utility module with base functionality."""


class Logger:
    """Simple logger class for demonstration."""
    
    def __init__(self, name):
        self.name = name
        self.enabled = True
    
    def log(self, message):
        """Log a message if enabled."""
        if self.enabled:
            print(f"[{self.name}] {message}")
    
    def disable(self):
        """Disable logging."""
        self.enabled = False


def validate_input(data):
    """Validate input data."""
    if data is None:
        raise ValueError("Data cannot be None")
    return True


def format_output(value):
    """Format output value as string."""
    return str(value).upper()
