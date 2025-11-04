package com.example.utils;

/**
 * Helper utility class with validation and formatting functions.
 */
public class Helper {
    
    public static boolean validateInput(Object data) {
        if (data == null) {
            throw new IllegalArgumentException("Data cannot be null");
        }
        return true;
    }
    
    public static String formatOutput(Object value) {
        return value.toString().toUpperCase();
    }
}
