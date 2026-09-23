# Absolut for OpenModelica

This fork contains the OpenModelica migration of Absolut v1.0.0, numerical and
initialization fixes, and reproducible component tests. The Modelica package
remains `Absolut`; load [Absolut/package.mo](Absolut/package.mo).

- [中文运行说明](README_zh.md)
- [Verification of the published source](reports/PUBLISH_VALIDATION.md)
- [Two evaporators in refrigerant-vapor series](reports/EVAPORATORS_SERIES.md)
- [Upstream integration notes](reports/UPSTREAM_MERGE.md)

## Requirements and use

Use OpenModelica with Modelica 4.0.0 and Buildings 12.0.0 for the complete
component suite. The heatport initialization and refrigerant-series cases are
also tested with Modelica 4.1.0. Buildings is an external dependency and is not
vendored in this repository.

In OMEdit, load the selected Modelica version, Buildings 12.0.0, and
`Absolut/package.mo`. The examples include the translation workaround
`--preOptModules-=evalFunc`. `AHPse_Dyn_heatport` runs with DASSL, tolerance
`1e-7`, and a full stop time of 86400 s.

The new example is
`Absolut.FluidBased.Dynamic.Components.Validation.EvaporatorsSeries_heatport`.
It connects the first evaporator's vapor outlet to the second evaporator's
vapor inlet through an adiabatic pressure-drop element. The second stage
consumes its initial liquid inventory; this 1200 s experiment does not model
an indefinitely sustained liquid supply to that stage.

## Reproduce the tests

Run from the repository root. Python's standard library is sufficient for the
test runners. Provide the installed `omc` and Buildings paths when necessary:

```powershell
python verify.py check --omc E:/OpenModelica/bin/omc.exe --buildings "../Buildings 12.0.0/package.mo"
python component_tests.py --omc E:/OpenModelica/bin/omc.exe --buildings "../Buildings 12.0.0/package.mo" --jobs 2
python component_tests.py --omc E:/OpenModelica/bin/omc.exe --buildings "../Buildings 12.0.0/package.mo" --modelica 4.1.0 --case EvaporatorsSeriesNominal --case EvaporatorsSeriesHeatStep --case EvaporatorsSeriesFeedStep --jobs 2 --report evaporators_series_msl_4_1_0
python verify.py regression --omc E:/OpenModelica/bin/omc.exe --buildings "../Buildings 12.0.0/package.mo"
```

With `OPENMODELICAHOME` set and Buildings 12.0.0 in the adjacent directory,
`python tests/initialization.py` runs the three heatport variants with both MSL
versions. `python tests/closed_loop_guards.py` tests intentional rejection of
invalid conservation configurations. Outputs are generated under `build/`.
Reports and selected series CSV evidence are committed under `reports/`;
compiler binaries and third-party dependencies are excluded.

The component suite checks mass/energy inventories, physical ranges, and load
changes. Successful simulation is not experimental validation or proof of
point-by-point equivalence with Dymola. Two laboratory examples require data
not distributed by upstream. Some complex AHP cases retain recovered nonlinear
iteration warnings; consult the reports and final simulation status.

---

The original project description and acknowledgements are retained below.

## Introduction
The Absolut library has been developed at [AEE INTEC](https://www.aee-intec.at/en/) to investigate absorption thermodynamic cycles, with special attention to the absorption heat exchanger (AHE) as part of the austrian research project “[Absolut](https://www.aee-intec.at/project/absolut-absorptionstechnologien-als-loesungen-fuer-nachhaltige-fernwaerme-und-fernkaelte/)” (FFG-Nr.: 879433).
The library includes models for different absorption cycles at various levels of detail, most of which have been validated against literature values.

## Dependencies
[Buildings library v12.0](https://github.com/lbl-srg/modelica-buildings/releases/tag/v12.0.0) is used for some heat exchanger models.

## Tool compatibility
The library has been developed using Dymola with partial testing performed in OpenModelica

## Acknowledgements
The project AbSolut (FFG-Nr.: 879433) is supported with the funds from the Climate and Energy Fund and implemented in the framework of the RTI-initiative “Flagship region Energy”.
The TREASURE project has received funding from the European Union under Grant Agreement No. 101136095.
Views and opinions expressed are however those of the author(s) only and do not necessarily reflect those of the European Union or CINEA.
Neither the European Union nor CINEA can be held responsible for them. 
