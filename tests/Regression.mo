within ;
package Regression "Independent numerical checks for the OpenModelica migration"
  model FlashingLiBrConservation
    "Continuous cooling and reheating through the onset of flashing"
    inner Modelica.Fluid.System system;
    package Solution = Absolut.Media.LiBrH2O;
    package Vapor = Modelica.Media.Water.WaterIF97_R2pT;
    Modelica.Fluid.Sources.MassFlowSource_T source(
      redeclare package Medium = Solution, nPorts=1, m_flow=0.05,
      use_T_in=true, X={0.4,0.6});
    Modelica.Fluid.Sources.FixedBoundary liquidSink(
      redeclare package Medium = Solution, nPorts=1, p=1000, use_T=true, T=300);
    Modelica.Fluid.Sources.FixedBoundary vaporSink(
      redeclare package Medium = Vapor, nPorts=1, p=1000, use_T=true, T=320);
    Absolut.FluidBased.Static.Components.FlashingLiBr valve(
      redeclare package Medium_l = Solution,
      redeclare package Medium_v = Vapor,
      m_flow_nominal=0.05, dp_nominal=9000,
      X_LiBr_start=0.6, p_out_start=1000, T_out_start=320,
      T_out_intern_auxiliar(start=320));
    Modelica.Units.SI.MassFlowRate saltResidual =
      valve.port_a.m_flow*0.6 + valve.port_l_b.m_flow*valve.X_LiBr_out;
    Real saltLoss(unit="kg", start=0, fixed=true) "Signed integral of LiBr imbalance";
  equation
    source.T_in = 273.15 + 50 + 10*cos(2*Modelica.Constants.pi*time/120);
    valve.opening = 1;
    connect(source.ports[1], valve.port_a);
    connect(valve.port_l_b, liquidSink.ports[1]);
    connect(valve.port_v_b, vaporSink.ports[1]);
    der(saltLoss) = saltResidual;
    assert(noEvent(abs(saltResidual)<1e-8),
      "Flashing valve loses LiBr while crossing the no-vapor boundary");
    assert(noEvent(abs(valve.balance)<0.05),
      "Flashing valve does not conserve energy");
    assert(noEvent(valve.T_out_intern_auxiliar > 273.15 and valve.T_out_intern_auxiliar < 500),
      "Diagnostic solution temperature left the physical branch in the cooling/reheating test");
    assert(noEvent(abs(Solution.specificEnthalpy_SSC_TXp(valve.T_out_intern_auxiliar,
      1-valve.X_LiBr_out, valve.port_l_b.p)-valve.h_out)<0.01),
      "Diagnostic solution temperature does not reproduce the mixture enthalpy");
    when terminal() then
      assert(abs(saltLoss)<1e-7, "Accumulated LiBr loss in a massless flashing valve");
    end when;
    annotation(experiment(StopTime=240, Interval=0.1, Tolerance=1e-8));
  end FlashingLiBrConservation;

  model StableLogMean
    Real a=5+time*1e-6;
    Real nearEqual=Absolut.FluidBased.Static.BaseClasses.logMeanPositive(a,5);
    Real equal=Absolut.FluidBased.Static.BaseClasses.logMeanPositive(5,5);
    Real forward=Absolut.FluidBased.Static.BaseClasses.logMeanPositive(2,8);
    Real backward=Absolut.FluidBased.Static.BaseClasses.logMeanPositive(8,2);
  equation
    assert(abs(equal-5)<1e-14, "Logarithmic mean does not have the correct equal-temperature limit");
    assert(abs(nearEqual-(a+5)/2)<1e-12, "Logarithmic mean lost precision near equal temperatures");
    assert(abs(forward-6/log(4))<1e-12 and abs(forward-backward)<1e-12,
      "Logarithmic mean disagrees with its definition or is not symmetric");
    annotation(experiment(StopTime=1, Interval=0.01, Tolerance=1e-8));
  end StableLogMean;

  model GibbsSecondDerivative
    parameter Real delta=0.001;
    Real T=350 + 2*time + 0.1*time^2;
    Real X=0.4 + 0.002*time + 0.0001*time^2;
    Real p=6000 + 100*time;
    Real gp=Absolut.Media.LiBrH2O.specificGibbsEnergy_TXp_derp(T,X,p);
    Real firstDerivative=der(gp);
    Real secondDerivative=der(firstDerivative);
    Real plus=Absolut.Media.LiBrH2O.specificGibbsEnergy_TXp_derp(
      350+2*(time+delta)+0.1*(time+delta)^2,
      0.4+0.002*(time+delta)+0.0001*(time+delta)^2,
      6000+100*(time+delta));
    Real minus=Absolut.Media.LiBrH2O.specificGibbsEnergy_TXp_derp(
      350+2*(time-delta)+0.1*(time-delta)^2,
      0.4+0.002*(time-delta)+0.0001*(time-delta)^2,
      6000+100*(time-delta));
    Real finiteDifference=(plus-2*gp+minus)/delta^2;
    Real error=secondDerivative-finiteDifference;
  equation
    assert(abs(error)<1e-7, "Gibbs second derivative disagrees with finite differences");
    annotation(experiment(StopTime=1, Interval=0.01, Tolerance=1e-8));
  end GibbsSecondDerivative;

  model MediumRoundTrip
    package Medium=Absolut.Media.LiBrH2O;
    parameter Real temperatures[3]={300,350,400};
    parameter Real waterFractions[3]={0.4,0.5,0.6};
    parameter Real pressures[3]={676,7406,50000};
    Medium.ThermodynamicState states[3];
    Real reconstructedTemperature[3];
    Real density[3];
    Real cp[3];
  equation
    for i in 1:3 loop
      states[i]=Medium.setState_pTX(pressures[i],temperatures[i],{waterFractions[i],1-waterFractions[i]});
      reconstructedTemperature[i]=Medium.temperature_hXp(
        Medium.specificEnthalpy(states[i]),waterFractions[i],pressures[i]);
      density[i]=Medium.density(states[i]);
      cp[i]=Medium.specificHeatCapacityCp(states[i]);
      assert(abs(reconstructedTemperature[i]-temperatures[i])<1e-7,
        "Temperature/enthalpy round trip failed");
      assert(density[i]>0 and cp[i]>0, "Non-positive density or heat capacity");
    end for;
    annotation(experiment(StopTime=1, Interval=0.1, Tolerance=1e-8));
  end MediumRoundTrip;
end Regression;
