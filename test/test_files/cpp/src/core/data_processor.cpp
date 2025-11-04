#include "../../include/core/data_processor.h"
#include "../../include/utils/helper.h"

namespace core {

DataProcessor::DataProcessor(const std::string& name) 
    : BaseProcessor(name), processedCount(0) {}

std::string DataProcessor::process(const std::string& data) {
    logger->log("Processing data: " + data);
    
    // Control statement: if/else for validation
    if (data.empty()) {
        throw std::invalid_argument("Data cannot be empty");
    }
    
    // Control statement: try/catch for validation
    try {
        utils::Helper::validateInput(&data);
    } catch (const std::exception& e) {
        logger->log(std::string("Validation failed: ") + e.what());
        throw;
    }
    
    std::string result = utils::Helper::formatOutput(data);
    processedCount++;
    return result;
}

std::map<std::string, int> DataProcessor::getStats() {
    std::map<std::string, int> stats;
    stats["processed"] = processedCount;
    
    // Control statement: if/else if/else for status code
    int statusCode;
    if (processedCount == 0) {
        statusCode = 0;  // idle
    } else if (processedCount < 10) {
        statusCode = 1;  // active
    } else {
        statusCode = 2;  // busy
    }
    stats["status_code"] = statusCode;
    
    return stats;
}

} // namespace core
