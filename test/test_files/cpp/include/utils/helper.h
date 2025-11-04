#ifndef UTILS_HELPER_H
#define UTILS_HELPER_H

#include <string>

namespace utils {

/**
 * Helper utility functions for validation and formatting.
 */
class Helper {
public:
    static bool validateInput(const void* data);
    static std::string formatOutput(const std::string& value);
};

} // namespace utils

#endif // UTILS_HELPER_H
