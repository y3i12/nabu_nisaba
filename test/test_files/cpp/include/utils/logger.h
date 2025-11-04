#ifndef UTILS_LOGGER_H
#define UTILS_LOGGER_H

#include <string>

namespace utils {

/**
 * Simple logger class for demonstration.
 */
class Logger {
private:
    std::string name;
    bool enabled;

public:
    Logger(const std::string& name);
    void log(const std::string& message);
    void disable();
};

} // namespace utils

#endif // UTILS_LOGGER_H
