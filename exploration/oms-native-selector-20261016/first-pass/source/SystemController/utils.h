// Utils.h
#ifndef UTILS_H
#define UTILS_H

using namespace std;

#include <sstream>
#include <iomanip>

inline string to_string_mod(double x, int precision = 17) {
    ostringstream oss;
    if (x > 0) oss << "+";
    oss << fixed << setprecision(precision) << x;
    return oss.str();
}

inline string to_string_mod(int x) {
    ostringstream oss;
    if (x > 0) oss << "+";
    oss << x;
    return oss.str();
}

#endif // UTILS_H