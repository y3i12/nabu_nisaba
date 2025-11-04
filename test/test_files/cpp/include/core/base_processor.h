#ifndef CORE_BASE_PROCESSOR_H
#define CORE_BASE_PROCESSOR_H

#include <string>
#include "../utils/logger.h"

namespace core {

/**
 * Base processor with common functionality.
 */
class BaseProcessor {
protected:
    std::string name;
    utils::Logger* logger;

public:
    BaseProcessor(const std::string& name);
    virtual ~BaseProcessor();
    virtual std::string process(const std::string& data) = 0;
};

} // namespace core

#endif // CORE_BASE_PROCESSOR_H
