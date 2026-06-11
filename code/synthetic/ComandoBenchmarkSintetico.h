#ifndef COMANDO_BENCHMARK_SINTETICO_H
#define COMANDO_BENCHMARK_SINTETICO_H

// =============================================================================
//  ComandoBenchmarkSintetico — punto de entrada del comando 'benchmarkSintetico'.
//
//  Parsea la gramática del comando (flags opcionales en `args`, parámetros
//  posicionales en las líneas siguientes leídas de `in`) y dispara el barrido
//  vía RunnerBenchmarkSintetico.
//
//  Se invoca desde 1_SistemaElectrico.cpp con una única rama 'else if' aditiva,
//  ANTES de inicializar (es autónomo: no requiere inicializar/agentes/despacho).
//
//  Gramática (líneas siguientes al token del comando):
//      <solver>
//      <seed>
//      <numInstancias>
//      <numBloques>
//      <varsContinuasPorBloque> <varsBinariasPorBloque>
//      <restrLocalesPorBloque> <restrAcoplamiento>
//      <pattern>                # none|local|coupling|mixed
//      <S>                      # 0|3|6
//      <variantes>              # ej: Base,SA-Aug,SA-Mat,Ruiz,Ruiz+Cols
//      <rutaCsvSalida>
//
//  Flags opcionales (en la misma línea del comando, p.ej.
//  'benchmarkSintetico --out dir --coef-family banded'):
//      --out <dir>            manifest.json + row/column_metadata.csv por instancia
//      --volcar-lp <dir>      exporta cada (instancia, variante) a .lp
//      --coef-family <fam>    uniform|block_heterogeneous|banded (default uniform)
//      --timeout <s>          timeout del solver
//      --mipgap <v>           gap MIP del solver
// =============================================================================

#include <istream>
#include <string>
#include <vector>

void ejecutarBenchmarkSintetico(std::istream& in, const std::vector<std::string>& args);

#endif // COMANDO_BENCHMARK_SINTETICO_H
