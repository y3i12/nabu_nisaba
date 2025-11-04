package com.example.utils;

/**
 * Simple logger class for demonstration.
 */
public class Logger {
    private String name;
    private boolean enabled;
    
    public Logger(String name) {
        this.name = name;
        this.enabled = true;
    }
    
    public void log(String message) {
        if (enabled) {
            System.out.println("[" + name + "] " + message);
        }
    }
    
    public void disable() {
        this.enabled = false;
    }
}
