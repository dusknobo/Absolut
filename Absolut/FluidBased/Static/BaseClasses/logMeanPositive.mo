within Absolut.FluidBased.Static.BaseClasses;
function logMeanPositive "Stable logarithmic mean of two positive temperature differences"
  input Modelica.Units.SI.TemperatureDifference a;
  input Modelica.Units.SI.TemperatureDifference b;
  output Modelica.Units.SI.TemperatureDifference mean;
protected
  Real z;
algorithm
  assert(a > 0 and b > 0, "logMeanPositive requires positive arguments");
  z := (a-b)/(a+b);
  if abs(z) < 1e-4 then
    // z/atanh(z) = 1-z^2/3-4*z^4/45+O(z^6).
    // This includes the exact limit mean=a when a=b, without 0/0.
    mean := (a+b)/2*(1-z*z/3-4*z^4/45);
  else
    mean := (a-b)/log(a/b);
  end if;
  annotation(Inline=true, smoothOrder=2);
end logMeanPositive;
