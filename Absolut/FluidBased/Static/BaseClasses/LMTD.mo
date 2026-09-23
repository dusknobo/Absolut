within Absolut.FluidBased.Static.BaseClasses;
partial model LMTD "Mean temperature difference"

  Modelica.Units.SI.TemperatureDifference dT1(start=2, nominal = 5) "Temperature differences 1 for HX";
  Modelica.Units.SI.TemperatureDifference dT2(start=1, nominal = 5) "Temperature differences 2 for HX";
  Modelica.Units.SI.TemperatureDifference dT_used(nominal = 5) "Used mean temperature difference";
  Modelica.Units.SI.TemperatureDifference dT_log(nominal = 5) "Logarithmic mean temperature difference (LMTD)";
  Boolean dTzero;
  parameter Real tol = 0.1 "Tolerance for dT1=dT2";


equation

  dTzero = noEvent(abs(dT1*dT1 - dT2*dT2) <= tol);
  // Evaluate the domain guard immediately, including during event iteration.
  // The nonnegative zero-terminal limit is zero; negative differences retain
  // the historical arithmetic fallback outside the positive LMTD domain.
  dT_log = if noEvent(dT1 > 0 and dT2 > 0) then
    Absolut.FluidBased.Static.BaseClasses.logMeanPositive(dT1, dT2)
    elseif noEvent(dT1 >= 0 and dT2 >= 0) then 0 else (dT1+dT2)/2;
  dT_used = dT_log;

  annotation (Icon(coordinateSystem(preserveAspectRatio=false)), Diagram(
        coordinateSystem(preserveAspectRatio=false)));
end LMTD;
