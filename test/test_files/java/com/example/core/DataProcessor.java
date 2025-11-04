package com.example.core;

import com.example.utils.Logger;
import com.example.utils.Helper;
import java.util.HashMap;
import java.util.Map;

/**
 * Concrete processor for data handling.
 */
public class DataProcessor extends BaseProcessor {
    private int processedCount;
    
    public DataProcessor(String name) {
        super(name);
        this.processedCount = 0;
    }
    
    @Override
    public String process(Object data) {
        logger.log("Processing data: " + data);
        
        // Control statement: if/else for validation
        if (data == null || data.toString().isEmpty()) {
            throw new IllegalArgumentException("Data cannot be empty");
        }
        
        // Control statement: try/catch for validation
        try {
            Helper.validateInput(data);
        } catch (Exception e) {
            logger.log("Validation failed: " + e.getMessage());
            throw e;
        }
        
        String result = Helper.formatOutput(data);
        processedCount++;
        return result;
    }
    
    public Map<String, Object> getStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("name", name);
        stats.put("processed", processedCount);
        
        // Control statement: if/elif/else for status
        if (processedCount == 0) {
            stats.put("status", "idle");
        } else if (processedCount < 10) {
            stats.put("status", "active");
        } else {
            stats.put("status", "busy");
        }
        
        return stats;
    }
}
