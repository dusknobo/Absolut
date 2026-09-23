within Absolut.FluidBased.Dynamic.Components.Validation;
model EvaporatorsSeries_heatport
  "Two dynamic evaporators in refrigerant-vapor series, with inventory checks"
  extends Modelica.Icons.Example;

  replaceable package Medium_l = Modelica.Media.Water.WaterIF97_R1pT;
  replaceable package Medium_v = Modelica.Media.Water.WaterIF97_R2pT;
  inner Modelica.Fluid.System system(allowFlowReversal=false);

  parameter Boolean useHeatStep=true "Apply heat steps at 300 s and 600 s";
  parameter Boolean useFeedStep=false "Halve the first-stage liquid feed at 600 s";
  parameter Modelica.Units.SI.HeatFlowRate Q1_nominal=1000;
  parameter Modelica.Units.SI.HeatFlowRate Q2_nominal=800;
  parameter Modelica.Units.SI.MassFlowRate m_feed_nominal=0.0004;
  parameter Modelica.Units.SI.Temperature T_feed=280.15;
  parameter Modelica.Units.SI.AbsolutePressure p_sink=1200;

  Absolut.FluidBased.Dynamic.Components.EvaporatorDyn_heatport eva1(
    redeclare package Medium_l=Medium_l,
    redeclare package Medium_v=Medium_v,
    p_start=1400, UA=1000, m(fixed=true), U(fixed=true))
    annotation(Placement(transformation(extent={{-72,-20},{-32,20}})));
  Absolut.FluidBased.Dynamic.Components.EvaporatorDyn_heatport eva2(
    redeclare package Medium_l=Medium_l,
    redeclare package Medium_v=Medium_v,
    p_start=1300, UA=1000, m(fixed=true), U(fixed=true))
    annotation(Placement(transformation(extent={{28,-20},{68,20}})));
  Modelica.Fluid.Sources.MassFlowSource_T liquidFeed(
    redeclare package Medium=Medium_l, nPorts=1,
    use_m_flow_in=true, T=T_feed)
    annotation(Placement(transformation(extent={{-126,-68},{-106,-48}})));
  Modelica.Fluid.Valves.ValveLinear seriesResistance(
    redeclare package Medium=Medium_v, allowFlowReversal=false,
    dp_nominal=100, m_flow_nominal=0.0004)
    "Adiabatic pressure drop between the two vapor spaces"
    annotation(Placement(transformation(extent={{-20,28},{0,48}})));
  Modelica.Fluid.Valves.ValveLinear outletResistance(
    redeclare package Medium=Medium_v, allowFlowReversal=false,
    dp_nominal=100, m_flow_nominal=0.0008)
    annotation(Placement(transformation(extent={{80,-10},{100,10}})));
  Modelica.Fluid.Sources.FixedBoundary vaporSink(
    redeclare package Medium=Medium_v, nPorts=1,
    p=p_sink, use_T=true, T=Medium_l.saturationTemperature(p_sink))
    annotation(Placement(transformation(extent={{130,-10},{110,10}})));
  Modelica.Thermal.HeatTransfer.Sources.PrescribedHeatFlow heat1
    annotation(Placement(transformation(extent={{-82,-88},{-62,-68}})));
  Modelica.Thermal.HeatTransfer.Sources.PrescribedHeatFlow heat2
    annotation(Placement(transformation(extent={{18,-88},{38,-68}})));

  Modelica.Units.SI.MassFlowRate m_feed=eva1.port_l_a.m_flow;
  Modelica.Units.SI.MassFlowRate m_series=-eva1.port_v.m_flow
    "Positive from evaporator 1 to evaporator 2";
  Modelica.Units.SI.MassFlowRate m_out=-eva2.port_v.m_flow;
  Modelica.Units.SI.PressureDifference dp_series=eva1.p-eva2.p;
  Modelica.Units.SI.HeatFlowRate Q_total=eva1.Qb_flow+eva2.Qb_flow;
  Real liquidFraction1=eva1.V_l/eva1.V;
  Real liquidFraction2=eva2.V_l/eva2.V;

  parameter Modelica.Units.SI.Mass initialMass1(fixed=false);
  parameter Modelica.Units.SI.Mass initialMass2(fixed=false);
  parameter Modelica.Units.SI.InternalEnergy initialEnergy1(fixed=false);
  parameter Modelica.Units.SI.InternalEnergy initialEnergy2(fixed=false);
  Modelica.Units.SI.Mass integratedMass1(start=0, fixed=true);
  Modelica.Units.SI.Mass integratedMass2(start=0, fixed=true);
  Modelica.Units.SI.Mass integratedMassTotal(start=0, fixed=true);
  Modelica.Units.SI.Energy integratedEnergy1(start=0, fixed=true);
  Modelica.Units.SI.Energy integratedEnergy2(start=0, fixed=true);
  Modelica.Units.SI.Energy integratedEnergyTotal(start=0, fixed=true);

  Modelica.Units.SI.Mass massChange1=eva1.m-initialMass1;
  Modelica.Units.SI.Mass massChange2=eva2.m-initialMass2;
  Modelica.Units.SI.Mass r_mass1=massChange1-integratedMass1;
  Modelica.Units.SI.Mass r_mass2=massChange2-integratedMass2;
  Modelica.Units.SI.Mass r_massTotal=massChange1+massChange2-integratedMassTotal;
  Modelica.Units.SI.Energy r_energy1=eva1.U-initialEnergy1-integratedEnergy1;
  Modelica.Units.SI.Energy r_energy2=eva2.U-initialEnergy2-integratedEnergy2;
  Modelica.Units.SI.Energy r_energyTotal=
    eva1.U+eva2.U-initialEnergy1-initialEnergy2-integratedEnergyTotal;
  Modelica.Units.SI.MassFlowRate r_seriesMass=
    eva1.port_v.m_flow+eva2.port_v_a.m_flow;
  Modelica.Units.SI.Power r_seriesEnergy=
    eva1.port_v.m_flow*actualStream(eva1.port_v.h_outflow)
    +eva2.port_v_a.m_flow*actualStream(eva2.port_v_a.h_outflow);

initial equation
  initialMass1=eva1.m;
  initialMass2=eva2.m;
  initialEnergy1=eva1.U;
  initialEnergy2=eva2.U;

equation
  liquidFeed.m_flow_in=m_feed_nominal*(if useFeedStep and time>=600 then 0.5 else 1);
  heat1.Q_flow=Q1_nominal+(if useHeatStep and time>=300 then 400 else 0);
  heat2.Q_flow=Q2_nominal+(if useHeatStep and time>=600 then 300 else 0);
  seriesResistance.opening=1;
  outletResistance.opening=1;

  connect(liquidFeed.ports[1], eva1.port_l_a)
    annotation(Line(points={{-106,-58},{-70,-58},{-70,-18}},color={0,127,255}));
  connect(eva1.port_v, seriesResistance.port_a)
    annotation(Line(points={{-33.6,0},{-26,0},{-26,38},{-20,38}},color={0,127,255}));
  connect(seriesResistance.port_b, eva2.port_v_a)
    annotation(Line(points={{0,38},{48,38},{48,19.6}},color={0,127,255}));
  connect(eva2.port_v, outletResistance.port_a)
    annotation(Line(points={{66.4,0},{80,0}},color={0,127,255}));
  connect(outletResistance.port_b, vaporSink.ports[1])
    annotation(Line(points={{100,0},{110,0}},color={0,127,255}));
  connect(heat1.port, eva1.heatPort)
    annotation(Line(points={{-62,-78},{-52,-78},{-52,0}},color={191,0,0}));
  connect(heat2.port, eva2.heatPort)
    annotation(Line(points={{38,-78},{48,-78},{48,0}},color={191,0,0}));

  // Unconnected eva1.port_v_a and eva2.port_l_a have zero mass flow.
  // Stage 2 evaporates its initial liquid inventory; it has no liquid makeup.
  // Integrate measured boundary fluxes independently of the vessel balances.
  der(integratedMass1)=eva1.port_l_a.m_flow+eva1.port_v_a.m_flow+eva1.port_v.m_flow;
  der(integratedMass2)=eva2.port_l_a.m_flow+eva2.port_v_a.m_flow+eva2.port_v.m_flow;
  der(integratedMassTotal)=m_feed-m_out;
  der(integratedEnergy1)=
    eva1.port_l_a.m_flow*actualStream(eva1.port_l_a.h_outflow)
    +eva1.port_v_a.m_flow*actualStream(eva1.port_v_a.h_outflow)
    +eva1.port_v.m_flow*actualStream(eva1.port_v.h_outflow)-heat1.port.Q_flow;
  der(integratedEnergy2)=
    eva2.port_l_a.m_flow*actualStream(eva2.port_l_a.h_outflow)
    +eva2.port_v_a.m_flow*actualStream(eva2.port_v_a.h_outflow)
    +eva2.port_v.m_flow*actualStream(eva2.port_v.h_outflow)-heat2.port.Q_flow;
  der(integratedEnergyTotal)=
    eva1.port_l_a.m_flow*actualStream(eva1.port_l_a.h_outflow)
    +eva2.port_v.m_flow*actualStream(eva2.port_v.h_outflow)
    -heat1.port.Q_flow-heat2.port.Q_flow;

  assert(noEvent(liquidFraction1>0 and liquidFraction1<1),
    "Evaporator 1 liquid inventory left the two-phase vessel range");
  assert(noEvent(liquidFraction2>0 and liquidFraction2<1),
    "Evaporator 2 liquid inventory left the two-phase vessel range");

  annotation(
    experiment(StartTime=0, StopTime=1200, Interval=1, Tolerance=1e-8),
    __OpenModelica_commandLineOptions="--preOptModules-=evalFunc -d=initialization",
    Diagram(coordinateSystem(extent={{-140,-110},{140,90}}),graphics={
      Text(extent={{-130,82},{130,58}},textString="Refrigerant series: evaporator 1 -> evaporator 2",textColor={28,108,200}),
      Text(extent={{-76,-24},{-30,-40}},textString="Evaporator 1"),
      Text(extent={{24,-24},{72,-40}},textString="Evaporator 2"),
      Text(extent={{-122,-92},{118,-106}},textString="Stage 2 uses its initial liquid inventory; 1200 s test")}),
    Documentation(info="<html>
<p>Two <code>EvaporatorDyn_heatport</code> components in refrigerant-vapor series.
Liquid enters stage 1 only. Its vapor outlet passes through an adiabatic linear
pressure-drop element into the vapor inlet of stage 2. The second vapor outlet
discharges through another resistance to a 1200 Pa boundary.</p>
<p>The steam connectors use WaterIF97_R2pT and the liquid connector uses
WaterIF97_R1pT. This is a series connection of vapor spaces, not a generic
two-phase flow-through evaporator. Stage 2 has no liquid makeup and evaporates
its initial liquid inventory. The experiment is limited to 1200 s, with liquid
volume checks; it is not an indefinitely sustained steady operating point.</p>
<p>Heat sources impose 1000 W and 800 W. By default they step to 1400 W at
300 s and 1100 W at 600 s. An optional feed test halves the liquid inlet flow
from 0.0004 kg/s at 600 s. The UA parameters do not determine prescribed heat
inputs in this heatport fixture.</p>
<p>Residuals compare vessel inventory changes with independent integrals of
connector mass and enthalpy fluxes and heat-source power, for each stage and
the complete series. Connection mass and energy residuals are also exposed.
No additional balance law is imposed on either evaporator.</p>
<p>Plot eva1.T, eva2.T, eva1.p, eva2.p, m_series, m_out, eva1.level,
eva2.level, eva1.Qb_flow, eva2.Qb_flow, and the r_* residuals.</p>
</html>"));
end EvaporatorsSeries_heatport;
