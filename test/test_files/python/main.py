"""Main entry point demonstrating the system."""

from core.processor import DataProcessor
from utils.helper import Logger


def main():
    """Main function to run the processor."""
    logger = Logger("Main")
    logger.log("Starting application")
    
    processor = DataProcessor("MainProcessor")
    
    # Control statement 1: if/elif/else block
    test_data = "test data"
    if len(test_data) > 20:
        logger.log("Large data detected")
        test_data = test_data[:20]
    elif len(test_data) < 5:
        logger.log("Small data detected")
        test_data = "default"
    else:
        logger.log("Normal data size")
    
    # Control statement 2: try/except/finally block
    try:
        result = processor.process(test_data)
        logger.log(f"Result: {result}")
    except ValueError as e:
        logger.log(f"Validation error: {e}")
        result = None
    except Exception as e:
        logger.log(f"Processing error: {e}")
        result = None
    finally:
        logger.log("Processing attempt completed")
    
    # Control statement 3: for loop
    test_items = ["item1", "item2", "item3"]
    for item in test_items:
        if item:
            processor.process(item)
    
    # Control statement 4: while loop
    retry_count = 0
    max_retries = 3
    while retry_count < max_retries:
        if processor.get_stats()["processed"] > 0:
            break
        retry_count += 1
    
    # Control statement 5: match statement (Python 3.10+)
    status_code = 200
    match status_code:
        case 200:
            logger.log("Success")
        case 404:
            logger.log("Not found")
        case _:
            logger.log("Other status")
    
    logger.log(f"Stats: {processor.get_stats()}")


if __name__ == "__main__":
    main()
