#ifndef CORE_DATA_PROCESSOR_H
#define CORE_DATA_PROCESSOR_H

#include "base_processor.h"
#include <map>
#include <string>

namespace core {

/**
 * Concrete processor for data handling.
 */
class DataProcessor : public BaseProcessor {
private:
    int processedCount;

public:
    DataProcessor(const std::string& name);
    std::string process(const std::string& data) override;
    std::map<std::string, int> getStats();
};

} // namespace core

#endif // CORE_DATA_PROCESSOR_H
