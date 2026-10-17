"""Independent randomized rational checks for the C++ binary64 conversion."""
from fractions import Fraction
import math
from pathlib import Path
import random
import struct
import subprocess

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def test_cpp_exact_conversion():
    executable=HERE/'test-exact'
    local=ROOT/'exploration/oms-followup-20261014/tools/local-deps/usr/include'
    subprocess.run(['g++','-std=c++17','-O2','-I'+str(ROOT/'code'),'-I'+str(local),str(HERE/'test_exact.cpp'),'-o',str(executable)],check=True)
    rng=random.Random(20261016)
    numbers=[0.,-0.,1.,-1.,2.**-1022,math.nextafter(2.**-1022,0.),float.fromhex('0x1.fffffffffffffp1023')]
    while len(numbers)<1007:
        value=struct.unpack('d',rng.getrandbits(64).to_bytes(8,'little'))[0]
        # stod legitimately raises ERANGE on subnormal decimal strings on this
        # C library; conversion of subnormals is tested via the hexadecimal path.
        if math.isfinite(value) and (not value or abs(value)>=2.**-1022):numbers.append(value)
    # Hex input avoids decimal parser underflow for the subnormal boundary.
    text='\n'.join(value.hex() for value in numbers)+'\n'
    p=subprocess.run([str(executable)],input=text,text=True,capture_output=True,check=True)
    actual=[Fraction(line) for line in p.stdout.splitlines()]
    assert actual==[Fraction.from_float(x) for x in numbers]
