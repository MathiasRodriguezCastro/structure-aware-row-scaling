# Certificate-wrapper recovery

The first geometric-scaling certificate fallback completed its native SoPlex
call, then the wrapper stopped because its hash helper received a Path instead
of bytes. The complete native log and primal/dual files were retained and parsed
after correcting the helper call. No native solve was repeated. The missing
wrapper return code and wall time remain null; this attempt is not counted as
another independent experiment. The resulting rational certificate is checked
against the original MPS independently of the wrapper or native solver status.
