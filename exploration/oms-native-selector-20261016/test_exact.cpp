#include "NativeContracts.h"
#include <iostream>
#include <iomanip>
#include <string>
int main() {
    std::string text;
    while (std::cin>>text) {
        double x=std::stod(text);
        auto q=oms_native::exact(x);
        std::cout<<boost::multiprecision::numerator(q)<<'/'
                 <<boost::multiprecision::denominator(q)<<'\n';
    }
}
