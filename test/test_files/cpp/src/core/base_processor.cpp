#include "../../include/core/base_processor.h"

namespace core {

BaseProcessor::BaseProcessor(const std::string& name) : name(name) {
    logger = new utils::Logger(name);
}

BaseProcessor::~BaseProcessor() {
    delete logger;
}

} // namespace core
