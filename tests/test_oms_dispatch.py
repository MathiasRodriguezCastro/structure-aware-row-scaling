import math
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/research'))
from oms_dispatch_validation import ruiz_row_factor, physical_spec, project_proposal, ruiz_export
from audit_identifiability_grid import parse

class DispatchValidation(unittest.TestCase):
    def test_ruiz_half_steps_and_safeguards(self):
        proposed,applied,_=ruiz_row_factor([1e8,1.])
        self.assertAlmostEqual(math.log10(proposed),-8*15/16)
        self.assertEqual(proposed,applied)
        self.assertEqual(ruiz_row_factor([1.])[1],1.)
        self.assertEqual(ruiz_row_factor([1e8,1e-8])[2],'coefficient_veto')
    def test_physical_conversion(self):
        self.assertEqual(physical_spec('a1_g2h_def(1)',{'g12(1)':1e7,'a1_z2h(1)':-1e7}),('Plant generation definitions','MW',1e7))
        self.assertEqual(physical_spec('a1_balance(2)',{'a1_v4h(2)':1,'a1_v4h(1)':-1,'a1_x4h(2)':3600}),('Water balances','m3',1.))
    def test_projection_and_incompatibility(self):
        lo,hi,factor,reason=project_proposal([1e6,1.],1e-3,.01)
        self.assertEqual(reason,'unchanged')
        self.assertEqual(factor,1e-3)
        self.assertEqual(project_proposal([1e12,1e-12],1.,.1)[3],'incompatible')
    def test_whole_row_rhs_and_domain(self):
        with tempfile.TemporaryDirectory() as temp:
            a,b=Path(temp)/'a.lp',Path(temp)/'b.lp'
            a.write_text('minimize\n  1 x\ns.t.\nr:\n  10000 x\n  -100 y\n  <= 50000\nbounds\n  0 <= x <= 1\nbinary\nx\nend\n')
            decisions=ruiz_export(a,b);old,other=parse(a);new,rest=parse(b)
            factor=decisions[0]['applied']
            self.assertEqual(other,rest)
            self.assertAlmostEqual(float(new['r']['rhs']),float(old['r']['rhs'])*factor)
            for name,c in old['r']['terms'].items():self.assertAlmostEqual(float(new['r']['terms'][name]),float(c)*factor)

if __name__=='__main__':unittest.main()
