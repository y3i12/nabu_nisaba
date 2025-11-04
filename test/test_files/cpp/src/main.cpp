#include "../include/core/data_processor.h"
#include "../include/utils/logger.h"

int main() {
    utils::Logger logger("Main");
    logger.log("Starting application");
    
    core::DataProcessor processor("MainProcessor");
    
    // Control statement 1: if/else if/else block
    std::string testData = "test data";
    if (testData.length() > 20) {
        logger.log("Large data detected");
        testData = testData.substr(0, 20);
    } else if (testData.length() < 5) {
        logger.log("Small data detected");
        testData = "default";
    } else {
        logger.log("Normal data size");
    }
    
    // Control statement 2: try/catch block
    std::string result;
    try {
        result = processor.process(testData);
        logger.log("Result: " + result);
    } catch (const std::invalid_argument& e) {
        logger.log(std::string("Validation error: ") + e.what());
        result = "";
    } catch (const std::exception& e) {
        logger.log(std::string("Processing error: ") + e.what());
        result = "";
    }
    
    // Control statement 3: for loop
    std::vector<std::string> testItems = {"item1", "item2", "item3"};
    for (const auto& item : testItems) {
        if (!item.empty()) {
            processor.process(item);
        }
    }
    
    // Control statement 4: while loop
    int retryCount = 0;
    int maxRetries = 3;
    while (retryCount < maxRetries) {
        auto stats = processor.getStats();
        if (stats["processed"] > 0) {
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
    
    auto stats = processor.getStats();
    logger.log("Processed count: " + std::to_string(stats["processed"]));
    
    return 0;
}
