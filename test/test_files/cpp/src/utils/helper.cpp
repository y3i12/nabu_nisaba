#include "../../include/utils/helper.h"
#include <algorithm>
#include <stdexcept>

namespace utils {

bool Helper::validateInput(const void* data) {
    if (data == nullptr) {
        throw std::invalid_argument("Data cannot be null");
    }
    return true;
}

std::string Helper::formatOutput(const std::string& value) {
    std::string result = value;
    std::transform(result.begin(), result.end(), result.begin(), ::toupper);
    return result;
}

} // namespace utils
