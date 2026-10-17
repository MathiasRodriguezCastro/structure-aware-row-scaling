"""Tests for refutation logic, including missing candidates and negative costs."""
from fractions import Fraction
import unittest
from study import bound_flags


class Endpoints(unittest.TestCase):
    def test_bound_can_be_refuted_without_candidate(self):
        self.assertEqual(bound_flags(-50.,None,False,Fraction(-100)),(True,False))

    def test_native_completion_does_not_certify_negative_cost_gap(self):
        self.assertEqual(bound_flags(-50.,-50.,True,Fraction(-100)),(True,True))
        self.assertEqual(bound_flags(-50.,-50.,False,Fraction(-100)),(True,False))

    def test_known_witness_does_not_certify_a_bound(self):
        self.assertEqual(bound_flags(-110.,-99.,True,Fraction(-100)),(False,True))
        self.assertEqual(bound_flags(-110.,-100.,True,Fraction(-100)),(False,False))

    def test_presentation_margin(self):
        self.assertFalse(bound_flags(0.0000009,0.,False,Fraction(0))[0])
        self.assertTrue(bound_flags(0.0000011,0.,False,Fraction(0))[0])


if __name__=='__main__':unittest.main()
