package com.example.core;

import com.example.utils.Logger;

/**
 * Base processor with common functionality.
 */
public abstract class BaseProcessor {
    protected String name;
    protected Logger logger;
    
    public BaseProcessor(String name) {
        this.name = name;
        this.logger = new Logger(name);
    }
    
    public abstract String process(Object data);
}
