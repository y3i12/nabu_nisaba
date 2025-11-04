package com.example;

import com.example.core.DataProcessor;
import com.example.utils.Logger;

/**
 * Main entry point demonstrating the system.
 */
public class Main {
    
    public static void main(String[] args) {
        Logger logger = new Logger("Main");
        logger.log("Starting application");
        
        DataProcessor processor = new DataProcessor("MainProcessor");
        
        // Control statement 1: if/else if/else block
        String testData = "test data";
        if (testData.length() > 20) {
            logger.log("Large data detected");
            testData = testData.substring(0, 20);
        } else if (testData.length() < 5) {
            logger.log("Small data detected");
            testData = "default";
        } else {
            logger.log("Normal data size");
        }
        
        // Control statement 2: try/catch/finally block
        String result = null;
        try {
            result = processor.process(testData);
            logger.log("Result: " + result);
        } catch (IllegalArgumentException e) {
            logger.log("Validation error: " + e.getMessage());
            result = null;
        } catch (Exception e) {
            logger.log("Processing error: " + e.getMessage());
            result = null;
        } finally {
            logger.log("Processing attempt completed");
        }
        
        // Control statement 3: for loop
        String[] testItems = {"item1", "item2", "item3"};
        for (String item : testItems) {
            if (item != null && !item.isEmpty()) {
                processor.process(item);
            }
        }
        
        // Control statement 4: while loop
        int retryCount = 0;
        int maxRetries = 3;
        while (retryCount < maxRetries) {
            Map<String, Object> stats = processor.getStats();
            if ((Integer) stats.get("processed") > 0) {
                break;
            }
            retryCount++;
        }
        
        // Control statement 5: switch statement
        int statusCode = 200;
        switch (statusCode) {
            case 200:
                logger.log("Success");
                break;
            case 404:
                logger.log("Not found");
                break;
            default:
                logger.log("Other status");
                break;
        }
        
        logger.log("Stats: " + processor.getStats());
    }
}
