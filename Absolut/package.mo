within ;
package Absolut
annotation (uses(
    Modelica(version="4.0.0"),
    ModelicaServices(version="4.0.0"),
      Buildings(version="12.0.0")),
  version="1.0.0+openmodelica.1",
  conversion(noneFromVersion={"1","1.0.0"}),
  Documentation(info="<html>
<p>OpenModelica migration of Absolut v1.0.0. Requires Modelica 4.0.0 and Buildings 12.0.0.</p>
<p>Dynamic vessels use mass and internal energy as states, with pT water media for the refrigerant.</p>
<p>See the accompanying README_zh.md and reports for loading instructions and simulation coverage.
Laboratory validation requires the original experimental data file, supplied through dataFile.</p>
</html>"));
end Absolut;
