#ifndef OMS_NATIVE_CONTRACTS_H
#define OMS_NATIVE_CONTRACTS_H
#include "SystemController/Problema/Problema.h"
#include <boost/multiprecision/cpp_int.hpp>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <limits>
#include <map>
#include <regex>
#include <set>
#include <stdexcept>

namespace oms_native {
using Q=boost::multiprecision::cpp_rational;
using I=boost::multiprecision::cpp_int;
inline Q exact(double x) {
    if (!std::isfinite(x)) throw std::invalid_argument("finite binary64 required");
    if (x==0) return Q(0);
    int e; double m=std::frexp(std::abs(x),&e);
    auto n=static_cast<unsigned long long>(std::ldexp(m,53));
    Q q(n); int k=e-53;
    if (k>=0) q*=I(1)<<k; else q/=I(1)<<(-k);
    return x<0 ? -q : q;
}
inline double inward(const Q& q,bool lower) {
    double x=q.convert_to<double>();
    if (!std::isfinite(x)) throw std::overflow_error("factor endpoint overflow");
    if (lower && exact(x)<q) x=std::nextafter(x,std::numeric_limits<double>::infinity());
    if (!lower && exact(x)>q) x=std::nextafter(x,0.);
    return x;
}
struct Units {double conversion=1.;bool physical=false;bool power=false;bool activation=false;};
inline Units units(const Restriccion& r) {
    const std::string name=r.getNombre(), f=name.substr(0,name.find('('));
    static const std::regex rio("a[0-9]+_gen_rio_negro"), gen("a[0-9]+_g[1-4]h_def"),
        env("a[0-9]+_(bonete|baygorria|palmar|salto_grande)_tangente_[0-9]+"),
        water("a[0-9]+_(v[1-3]h_din|balance)"), act("a[0-9]+_activacion_[1-4]"),
        gcol("g[0-9]+\\([0-9]+\\)"), zcol("a[0-9]+_z[1-4]h\\([0-9]+\\)");
    Units u;
    if (std::regex_match(f,act)) {u.physical=true;u.activation=true;return u;}
    std::string target;
    if (f=="gh_total" || f=="gen_menor_demanda" || std::regex_match(f,rio)) {
        target=(f=="gh_total" || f=="gen_menor_demanda") ? "g" : "g"+f.substr(1,f.find('_')-1);
        for (const auto& term:r.getTerminos()) if (term.second.substr(0,term.second.find('('))==target) return {std::abs(term.first),true,true,false};
        throw std::runtime_error("missing aggregate generation "+name);
    }
    bool isgen=std::regex_match(f,gen), isenv=std::regex_match(f,env);
    if (isgen || isenv) {
        int count=0;
        for (const auto& term:r.getTerminos()) if (std::regex_match(term.second,isgen ? gcol : zcol)) {u.conversion=std::abs(term.first);++count;}
        if (count!=1) throw std::runtime_error("ambiguous generation/envelope "+name);
        u.physical=true;u.power=true;return u;
    }
    if (std::regex_match(f,water)) {
        auto split=f.find('_');std::string agent=f.substr(0,split);
        char plant=f.substr(split+1)=="balance" ? '4' : f[split+2];
        target=agent+"_v"+plant+"h";int count=0;
        for (const auto& term:r.getTerminos()) if (term.second.substr(0,term.second.find('('))==target) {
            double c=std::abs(term.first);if(count && c!=u.conversion) throw std::runtime_error("ambiguous storage "+name);u.conversion=c;++count;
        }
        if (!count && plant=='2') {
            target=agent+"_x2h";
            for (const auto& term:r.getTerminos()) if (term.second.substr(0,term.second.find('('))==target) {u.conversion=std::abs(term.first)/3600.;++count;}
        }
        if (!count) throw std::runtime_error("missing water conversion "+name);
        u.physical=true;return u;
    }
    return u;
}
inline void apply(Problema& problem) {
    const char* mode=std::getenv("OMS_NATIVE_POLICY");if (!mode) return;
    bool budgeted=std::string(mode)=="Budget-L2";
    if (!budgeted && std::string(mode)!="L2") throw std::invalid_argument("unknown native policy");
    double gamma=1e-9, volume=100.;
    if (const char* v=std::getenv("OMS_NATIVE_VOLUME")) volume=std::stod(v);
    auto start=std::chrono::steady_clock::now();
    std::set<std::string> integer;std::map<std::string,double> boxes;
    for (const auto* b:problem.getBinarios()) {integer.insert(b->getNombre());boxes[b->getNombre()]=1.;}
    for (const auto* v:problem.getVariables()) boxes[v->getNombre()]=std::max(std::abs(v->getCotaInf()),std::abs(v->getCotaSup()));
    std::vector<double> factors;factors.reserve(problem.getRestricciones().size());
    for (const auto* row:problem.getRestricciones()) {
        double lo=std::numeric_limits<double>::infinity(),hi=0.;
        for (const auto& t:row->getTerminos()) if (t.first) {lo=std::min(lo,std::abs(t.first));hi=std::max(hi,std::abs(t.first));}
        if (!std::isfinite(lo) || !hi) throw std::runtime_error("constant/nonfinite row requires separate check");
        double delta=1e100,reserve=0.;Units u;
        if (budgeted) {
            u=units(*row);
            if (u.physical) {
                delta=(u.power ? .01 : volume)*u.conversion;Q E=0,box=exact(std::abs(row->getTerminoIndependiente()));
                for (const auto& t:row->getTerminos()) {
                    if (integer.count(t.second)) E+=exact(gamma)*exact(std::abs(t.first));
                    if (u.activation) {
                        auto it=boxes.find(t.second);if(it==boxes.end() || !std::isfinite(it->second)) throw std::runtime_error("missing finite box");
                        box+=exact(std::abs(t.first))*exact(it->second);
                    }
                }
                if (u.activation) E+=exact(std::ldexp(1.,-52))*box;
                reserve=inward(E,true);
            }
        }
        if (reserve>=delta) throw std::runtime_error("rounding budget exhausted "+row->getNombre());
        Q lower=exact(1e-9)/exact(lo), accuracy=exact(1e-6)/(exact(delta)-exact(reserve));
        if (accuracy>lower) lower=accuracy;
        Q upper=exact(1e9)/exact(hi);
        if (lower>upper) throw std::runtime_error("empty contract "+row->getNombre());
        double L=inward(lower,true),H=inward(upper,false),sum=0.;
        for (const auto& t:row->getTerminos()) {double a=t.first/hi;sum+=a*a;}
        double candidate=std::exp(-std::log(hi)-std::log(std::sqrt(sum)));
        factors.push_back(std::min(std::max(candidate,L),H));
    }
    double selection=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
    // Commit only after every row has a valid decision.
    for (std::size_t i=0;i<factors.size();++i) {
        auto* row=problem.getRestricciones()[i];auto terms=row->getTerminos();
        for (auto& t:terms)t.first*=factors[i];row->setTerminos(terms);
        row->setTerminoIndependiente(row->getTerminoIndependiente()*factors[i]);
    }
    double total=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
    if (const char* file=std::getenv("OMS_NATIVE_FACTORS")) {
        std::ofstream out(file);out<<std::setprecision(17)<<"row,factor\n";
        for (std::size_t i=0;i<factors.size();++i)out<<problem.getRestricciones()[i]->getNombre()<<','<<factors[i]<<'\n';
    }
    std::cout<<std::setprecision(17)<<"[NATIVE_CONTRACT] selection_seconds="<<selection<<" selection_apply_seconds="<<total<<" rows="<<factors.size()<<std::endl;
}
}
#endif
