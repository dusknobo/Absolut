within Absolut.FluidBased.Static.Components;
model Compressor
  extends Modelica.Icons.UnderConstruction;

  replaceable package Medium_v = Modelica.Media.Water.WaterIF97_R2ph annotation (
     __Dymola_choicesAllMatching=true);

Modelica.Units.SI.Temperature Tsuc "Suction temperature";
Real R = Modelica.Constants.R "Gas constant in J/(mol.K)";
Real M = 18.015 "Molecular weight";
Real gamma = 1.4 "Isentropic expansion factor. Cp/Cv 8/6";
Modelica.Units.SI.Pressure Psuc = port_v_a.p "Suction pressure";
Modelica.Units.SI.Pressure Pdis = port_v_b.p "Discharge pressure";
Real Pr = Pdis/Psuc "Pressure ratio";
parameter Real Pr_set = 2 "Setpoint - Pressure ratio";
parameter Real eff_is = 0.7 "Isentropic efficiency";

Modelica.Fluid.Interfaces.FluidPort_a port_v_a(redeclare package Medium =
        Medium_v) "Fluid port. Water vapor" annotation (Placement(
        transformation(extent={{-100,-10},{-80,10}}), iconTransformation(extent={{-100,
            -10},{-80,10}})));
Modelica.Fluid.Interfaces.FluidPort_b port_v_b(redeclare package Medium =
        Medium_v) "Fluid port. Water vapor" annotation (Placement(
        transformation(extent={{80,-10},{100,10}}), iconTransformation(extent={{80,-10},
            {100,10}})));

Modelica.Units.SI.SpecificEnthalpy h1, h2s;
Modelica.Units.SI.SpecificEntropy s1, s2;
Modelica.Units.SI.SpecificEntropy s2s;

Modelica.Units.SI.Temperature T2, T2s;

Real W_spec(unit="kJ/kg") "Work for a specific amount of vapor compressed in kJ/kg";
Modelica.Units.SI.EnergyFlowRate W "Work in W";

equation
port_v_a.m_flow + port_v_b.m_flow = 0;

Tsuc = Medium_v.temperature(Medium_v.setState_phX(port_v_a.p, h1, {1}));
assert(Pr_set >= 1, "Compressor pressure ratio must be at least one");
assert(eff_is > 0 and eff_is <= 1, "Compressor isentropic efficiency must be in (0, 1]");

port_v_a.h_outflow = Medium_v.specificEnthalpy(Medium_v.setState_pTX(
    port_v_a.p,
    Tsuc,
    {1}));

s1 = Medium_v.specificEntropy(Medium_v.setState_phX(
    port_v_a.p,
    inStream(port_v_a.h_outflow),
    {1}));
s1 = s2s;
s2 = Medium_v.specificEntropy(Medium_v.setState_phX(
    port_v_b.p,
    port_v_b.h_outflow,
    {1}));

h1 = inStream(port_v_a.h_outflow);
h2s = if Pr_set == 1 then h1 else Medium_v.specificEnthalpy(Medium_v.setState_psX(
    port_v_b.p,
    s2s,
    {1}));

// One adiabatic energy balance for both reported power and outlet enthalpy.
W_spec = (port_v_b.h_outflow - h1)/1000;
W = port_v_a.m_flow*(port_v_b.h_outflow - h1);

Pr = Pr_set;

port_v_b.h_outflow = h1 + (h2s - h1)/eff_is;

T2s = if Pr_set == 1 then Tsuc else Medium_v.temperature(Medium_v.setState_psX(
    port_v_b.p,
    s2s,
    {1}));
T2 = Medium_v.temperature(Medium_v.setState_phX(
    port_v_b.p,
    port_v_b.h_outflow,
    {1}));

  annotation (Icon(coordinateSystem(preserveAspectRatio=false), graphics={
          Polygon(
          points={{-90,100},{-90,-100},{90,-40},{90,40},{-90,100}},
          lineColor={28,108,200},
          fillColor={255,255,255},
          fillPattern=FillPattern.Solid)}),                      Diagram(
        coordinateSystem(preserveAspectRatio=false)),
    Documentation(info="<html>
<p>Forward-flow adiabatic compressor. Outlet enthalpy follows the isentropic efficiency and reported power equals the enthalpy-flow rise. At unit pressure ratio, enthalpy and power changes are exactly zero.</p>
</html>"));
end Compressor;
