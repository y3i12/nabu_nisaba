#include "../../include/utils/logger.h"
#include <iostream>

namespace utils {

Logger::Logger(const std::string& name) : name(name), enabled(true) {}

void Logger::log(const std::string& message) {
    if (enabled) {
        std::cout << "[" << name << "] " << message << std::endl;
    }
}

void Logger::disable() {
    enabled = false;
}

} // namespace utils
