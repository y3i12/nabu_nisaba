"""Core processor module that uses utility functions."""

from utils.helper import Logger, validate_input, format_output


class BaseProcessor:
    """Base processor with common functionality."""
    
    def __init__(self, name):
        self.name = name
        self.logger = Logger(name)
    
    def process(self, data):
        """Process data - to be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement process()")


class DataProcessor(BaseProcessor):
    """Concrete processor for data handling."""
    
    def __init__(self, name):
        super().__init__(name)
        self.processed_count = 0
    
    def process(self, data):
        """Process the input data."""
        self.logger.log(f"Processing data: {data}")
        
        # Control statement: if/else for validation
        if not data:
            raise ValueError("Data cannot be empty")
        
        # Control statement: try/except for validation
        try:
            validate_input(data)
        except Exception as e:
            self.logger.log(f"Validation failed: {e}")
            raise
        
        result = format_output(data)
        self.processed_count += 1
        return result
    
    def get_stats(self):
        """Get processing statistics."""
        # Control statement: for loop with condition
        stats = {
            "name": self.name,
            "processed": self.processed_count
        }
        
        # Add status based on count
        if self.processed_count == 0:
            stats["status"] = "idle"
        elif self.processed_count < 10:
            stats["status"] = "active"
        else:
            stats["status"] = "busy"
        
        return stats
