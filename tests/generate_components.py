"""Generate readable, standalone component fixtures and their coverage manifest.

The fixtures measure residuals; they never add missing conservation laws to a DUT.
Use component_tests.py to compile, run, and independently judge saved residuals.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LIB = ROOT / "Absolut"
S = "Absolut.FluidBased.Static."
D = "Absolut.FluidBased.Dynamic.Components."
B = "Absolut.Basic.Blocks."
W = "Modelica.Media.Water.WaterIF97_R1pT"
V = "Modelica.Media.Water.WaterIF97_R2pT"
L = "Absolut.Media.LiBrH2O"
CW = "Modelica.Media.Water.ConstantPropertyLiquidWater"
cases = []
models = []


def add(name, target, declarations, equations, metrics, scenario, *, initial="", stop=10,
        ranges=None, excursions=None, notes="", tolerance=1e-8):
    case = dict(case=name, model="ComponentTests." + name, component=target,
                scenario=scenario, residual_limits=metrics, ranges=ranges or {}, excursions=excursions or {}, notes=notes,
                stop=stop, tolerance=tolerance)
    cases.append(case)
    models.append(f'''  model {name}
    "{scenario}"
{declarations}
{('  initial equation' + chr(10) + initial) if initial else ''}
  equation
{equations}
    annotation(experiment(StopTime={stop}, Interval={stop/500:g}, Tolerance={tolerance}),
      __OpenModelica_commandLineOptions="--preOptModules-=evalFunc");
  end {name};
''')


def port_flux(ports, field="energy"):
    if field == "mass":
        return " + ".join(f"dut.{p}.m_flow" for p in ports) or "0"
    if field == "salt":
        return " + ".join(f"dut.{p}.m_flow*(1-actualStream(dut.{p}.Xi_outflow[1]))" for p in ports) or "0"
    return " + ".join(f"dut.{p}.m_flow*actualStream(dut.{p}.h_outflow)" for p in ports) or "0"


def flow_source(name, port, medium, rate, temp, x=""):
    decl = f"    Modelica.Fluid.Sources.MassFlowSource_T {name}(redeclare package Medium={medium}, nPorts=1, use_m_flow_in=true, use_T_in=true{x});\n"
    eq = f"    {name}.m_flow_in={rate}; {name}.T_in={temp};\n    connect({name}.ports[1], dut.{port});\n"
    return decl, eq


def pressure_sink(name, port, medium, pressure, temp, x=""):
    return (f"    Modelica.Fluid.Sources.FixedBoundary {name}(redeclare package Medium={medium}, nPorts=1, p={pressure}, use_T=true, T={temp}{x});\n",
            f"    connect(dut.{port}, {name}.ports[1]);\n")


def basics():
    common = "    Integer point = if time<3 then 1 elseif time<6 then 2 else 3;\n"
    for name, factor in [("EER_HalfEffectAHP", .5), ("EER_SingleEffectAHP", 1),
                         ("EER_DoubleEffectAHP", 2), ("EER_TripleEffectAHP", 3)]:
        decl = common + f"    {B+name} dut;\n    parameter Real expected[3]={{0.8,0.75,0.6}};\n    Real r_eer=dut.EER-{factor}*expected[point];\n"
        eq = "    dut.Te=if point==1 then 280 elseif point==2 then 285 else 300;\n    dut.Th=if point==1 then 350 elseif point==2 then 380 else 500;\n"
        metrics = {"r_eer": 1e-10}
        if name == "EER_SingleEffectAHP":
            decl += "    Real r_cop=dut.COP-dut.EER-1;\n"
            metrics["r_cop"] = 1e-10
        add(name, B+name, decl, eq, metrics, "Three analytic operating points and temperature steps")
    for name in ["CarnotSingleEffectAHP", "EER_CarnotSingleEffectAHP"]:
        suffix = "i" if name == "CarnotSingleEffectAHP" else ""
        decl = common + f"    {B+name} dut;\n    Real r_entropy=dut.EER/dut.Te{suffix}+1/dut.Th{suffix}-dut.COP/dut.Tc{suffix};\n    Real r_cop=dut.COP-dut.EER-1;\n"
        eq = f"    dut.Te{suffix}=280+point; dut.Th{suffix}=360+10*point; dut.Tc{suffix}=310+5*point;\n"
        metrics = {"r_entropy": 1e-10, "r_cop": 1e-10}
        if suffix:
            eq += "    dut.Qh=1000*point;\n"
            decl += "    Real r_energy=dut.Qh+dut.Qe-dut.Qc;\n"
            metrics["r_energy"] = 1e-6
        add(name, B+name, decl, eq, metrics, "Reversible-cycle entropy balance and heating/cooling COP identity")
    add("DDT_AHT", B+"DDT_AHT", common + f'''    {B}DDT_AHT dut;
    parameter Real expected[3]={{10.5,12.0,25.0}};
    Real r_ddt=dut.DDT-expected[point];''',
        "    dut.Te=if point==1 then 350 elseif point==2 then 360 else 350;\n    dut.Tc=300; dut.Tg=350; dut.Ta=if point==1 then 397 elseif point==2 then 407 else 382.5;",
        {"r_ddt": 1e-10}, "Three independent Duehring temperature-difference values")
    add("Tfiring", B+"Tfiring", common + f'''    {B}Tfiring dut;
    parameter Real expected[3]={{360,390,325}};
    Real r_temperature=dut.Th-expected[point];''',
        "    dut.Te=if point==1 then 280 elseif point==2 then 290 else 285;\n    dut.Tc=if point==1 then 310 elseif point==2 then 320 else 305;\n    dut.dT=if point==1 then 5 elseif point==2 then 10 else 0;",
        {"r_temperature": 1e-8}, "Minimum firing temperature at three independent analytic reference points")
    add("ZeroOrderSingleEffectAHP", B+"ZeroOrderSingleEffectAHP", common+f'''    {B}ZeroOrderSingleEffectAHP dut;
    parameter Real expected[3]={{0.8,0.75,0.75}};
    Real r_eer=dut.EER-expected[point];
    Real r_energy=dut.Qh+dut.Qe-dut.Qc;
    Real r_cop=dut.COP-dut.EER-1;''',
        "    dut.Thi=if point==1 then 350 elseif point==2 then 380 else 400;\n    dut.Tci=if point==1 then 315 elseif point==2 then 332.5 else 350;\n    dut.Qh=1000*point;",
        {"r_eer":1e-9,"r_energy":1e-6,"r_cop":1e-10}, "Equal internal temperature lifts and analytic COP values")
    add("ZeroOrderSingleEffectAHP_ext", B+"ZeroOrderSingleEffectAHP_ext", common+f'''    {B}ZeroOrderSingleEffectAHP_ext dut;
    parameter Real expected[3]={{0.8181818181818182,0.7714285714285715,0.7837837837837838}};
    Real r_eer=dut.EER-expected[point];
    Real r_energy=dut.Qh+dut.Qe-dut.Qc;
    Real r_cop=dut.COP-dut.EER-1;''',
        "    dut.Th=if point==1 then 360 elseif point==2 then 380 else 400;\n    dut.Tc=if point==1 then 300 elseif point==2 then 310 else 330;",
        {"r_eer":1e-8,"r_energy":1e-5,"r_cop":1e-10}, "External UA network and three closed-form reference solutions")


def pumps():
    for name, medium in [("Pump", L), ("PumpW", W)]:
        decl = f"    inner Modelica.Fluid.System system;\n    {S}Components.{name} dut(redeclare package Medium_l={medium}" + (", T_in_start=300" if name=="Pump" else "") + ");\n"
        eq = "    dut.m_dot_in=if time<3 then 0.05 elseif time<6 then 0.01 else 0;\n"
        for b in [pressure_sink("source", "port_l_a", medium, 100000,300,", X={0.4,0.6}" if name=="Pump" else ""),
                  pressure_sink("sink", "port_l_b",medium, 500000,310,", X={0.4,0.6}" if name=="Pump" else "")]:
            decl+=b[0]; eq+=b[1]
        decl+=f'''    Real r_mass={port_flux(['port_l_a','port_l_b'],'mass')};
    Real r_energy={port_flux(['port_l_a','port_l_b'])}+dut.W_p;
    Real r_efficiency=dut.W_p-dut.etha*dut.W_el;
    Real r_inletTemperature=dut.T-300;
    Real r_temperature=dut.T_out-{medium}.temperature({medium}.setState_phX(dut.port_l_b.p,dut.port_l_b.h_outflow,inStream(dut.port_l_a.Xi_outflow)));
'''
        metrics={"r_mass":1e-10,"r_energy":1e-5,"r_efficiency":1e-8,"r_temperature":1e-4,"r_inletTemperature":1e-4}
        if name=="PumpW":
            # IAPWS R7-97(2012), section 5.2.1, equation (12): the Region 1
            # backward T(p,h) equation tolerates 25 mK inconsistency.
            metrics['r_inletTemperature']=0.025
        if name=="Pump":
            decl+=f"    Real r_salt={port_flux(['port_l_a','port_l_b'],'salt')};\n"
            metrics['r_salt']=1e-10
        add(name,S+"Components."+name,decl,eq,metrics,"Nominal flow, part load and zero flow; port enthalpy, work and outlet thermometer",
            notes="Forward flow at 100 to 500 kPa. PumpW inlet temperature uses the IF97 Region 1 backward-equation consistency limit of 0.025 K (IAPWS R7-97(2012), section 5.2.1, equation 12). Reverse flow is outside this fixture.")


def compressor():
    for suffix, ratio in [("",2),("UnityRatio",1)]:
        decl=f"    inner Modelica.Fluid.System system;\n    {S}Components.Compressor dut(redeclare package Medium_v={V},Pr_set={ratio});\n"
        eq=""
        for b in [flow_source('source','port_v_a',V,"if time<5 then 0.001 else 0.0003","350+time"), pressure_sink('sink','port_v_b',V,20000,400)]:
            decl+=b[0]; eq+=b[1]
        decl+=f'''    Real r_mass={port_flux(['port_v_a','port_v_b'],'mass')};
    Real r_energy={port_flux(['port_v_a','port_v_b'])}+dut.W;
    Real r_efficiency=dut.eff_is*(dut.port_v_b.h_outflow-inStream(dut.port_v_a.h_outflow))-(dut.h2s-inStream(dut.port_v_a.h_outflow));
    Real r_ratio=dut.port_v_b.p/dut.port_v_a.p-{ratio};'''
        metrics={"r_mass":1e-10,"r_energy":0.01,"r_efficiency":0.01,"r_ratio":1e-8}
        if ratio==1:
            decl+='\n    Real r_zeroPower=dut.W;\n    Real r_zeroEnthalpyRise=dut.port_v_b.h_outflow-inStream(dut.port_v_a.h_outflow);'
            metrics.update(r_zeroPower=1e-10,r_zeroEnthalpyRise=1e-8)
        add("Compressor"+suffix,S+"Components.Compressor",decl,eq,metrics,
            f"Adiabatic compressor energy and isentropic efficiency; pressure ratio {ratio}",
            ranges={"dut.W":[-1e-5,None]}, notes="Source steam is superheated; power must equal its enthalpy-flow rise.")


def flashing():
    for name, medium in [("FlashingWater",W),("FlashingLiBr",L)]:
        libr=name=="FlashingLiBr"
        decl=f"    inner Modelica.Fluid.System system;\n    {S}Components.{name} dut(redeclare package Medium_l={medium},redeclare package Medium_v={V},m_flow_nominal=0.05,dp_nominal=9000,T_out_start=320"
        decl+=(",X_LiBr_start=0.6,p_out_start=1000,T_out_intern_auxiliar(start=320)" if libr else "")+");\n"
        eq="    dut.opening=if time<120 then 1 else 0.5;\n"
        # 1000 Pa water boils near 280 K; solution with 60% LiBr near 320 K.
        temp=("323.15+10*cos(2*Modelica.Constants.pi*time/120)" if libr else "280.15+5*cos(2*Modelica.Constants.pi*time/120)")
        for b in [flow_source('source','port_a',medium,"0.05",temp,", X={0.4,0.6}" if libr else ""),
                  pressure_sink('liquidSink','port_l_b',medium,1000,300,", X={0.4,0.6}" if libr else ""),
                  pressure_sink('vaporSink','port_v_b',V,1000,320)]:
            decl+=b[0]; eq+=b[1]
        decl+=f'''    Real r_mass={port_flux(['port_a','port_l_b','port_v_b'],'mass')};
    Real r_energy={port_flux(['port_a','port_l_b','port_v_b'])};
    Real r_quality=dut.Q* dut.port_a.m_flow+dut.port_v_b.m_flow;
    Real r_hydraulic=dut.port_a.m_flow-dut.opening*0.05/9000*(dut.port_a.p-dut.port_l_b.p);
'''
        metrics={"r_mass":1e-10,"r_energy":0.05,"r_quality":1e-10,"r_hydraulic":1e-9}
        if libr:
            decl+=f"    Real r_salt={port_flux(['port_a','port_l_b'],'salt')};\n"
            metrics['r_salt']=1e-8
        add(name,S+"Components."+name,decl,eq,metrics,"Two cooling/heating cycles across flash onset, with valve opening step",stop=240,
            ranges={"dut.Q":[-1e-8,1+1e-8]},excursions={"dut.Q":{"min_at_most":1e-8,"max_at_least":1e-4}},
            notes="Forward liquid feed; 1000 Pa outlets. Both two-phase and subcooled regimes must actually occur in saved output.")


def hexes():
    for name in ["ConstantEffectiveness","PlateHeatExchangerEffectivenessNTU","simpleHX"]:
        decl=f"    inner Modelica.Fluid.System system;\n    {S}Components.HEX.{name} dut(redeclare package Medium1={CW},redeclare package Medium2={CW},m1_flow_nominal=1,m2_flow_nominal=2,dp1_nominal=100,dp2_nominal=100"
        if name=="ConstantEffectiveness": decl+=",eps=0.7"
        else: decl+=",configuration=Buildings.Fluid.Types.HeatExchangerConfiguration.CounterFlow"
        if name=="simpleHX":decl+=",UA_fix=1000"
        if name=="PlateHeatExchangerEffectivenessNTU":decl+=",Q_flow_nominal=10000,T_a1_nominal=353.15,T_a2_nominal=293.15"
        decl+=");\n"
        eq=""
        for b in [flow_source('hot','port_a1',CW,"if time<3 then 1 elseif time<6 then 0.4 else 0","353.15"),
                  flow_source('cold','port_a2',CW,"if time<3 then 2 elseif time<6 then 0.8 else 0","293.15"),
                  pressure_sink('hotSink','port_b1',CW,100000,353.15),
                  pressure_sink('coldSink','port_b2',CW,100000,293.15)]:
            decl+=b[0];eq+=b[1]
        decl+=f'''    Real flowFraction=if time<3 then 1 elseif time<6 then 0.4 else 0;
    parameter Real nominalEps=10000/(4184*60);
    parameter Real nominalNTU=-log((1-nominalEps)/(1-0.5*nominalEps))/0.5;
    Real expectedNTU=if time>=6 then 0 else '''+('1000/(flowFraction*4184);\n' if name=='simpleHX' else 'nominalNTU*flowFraction^(-0.2);\n')+f'''    Real r_mass1={port_flux(['port_a1','port_b1'],'mass')};
    Real r_mass2={port_flux(['port_a2','port_b2'],'mass')};
    Real r_energy={port_flux(['port_a1','port_b1','port_a2','port_b2'])};
    Real heatHot={port_flux(['port_a1','port_b1'])};
    Real expectedHeat=if time>=6 then 0 else '''
        if name=="ConstantEffectiveness":decl+="0.7*(if time<3 then 1 else 0.4)*4184*60;\n"
        else:decl+="flowFraction*4184*60*(1-exp(-0.5*expectedNTU))/(1-0.5*exp(-0.5*expectedNTU));\n"
        decl+="    Real r_heat=heatHot-expectedHeat;\n"
        add("HEX_"+name,S+"Components.HEX."+name,decl,eq,
            {"r_mass1":1e-9,"r_mass2":1e-9,"r_energy":0.01,"r_heat":0.1},
            "Capacity ratio 0.5; analytic heat duty at nominal, part and zero flow",
            notes="Constant-property water, cp=4184 J/(kg.K). Capacity ratio 0.5 avoids the Buildings smoothing near ratio 1; plate UA scales with flow^0.8. Positive hot-side heat means cooling.")


def dynamics():
    for kind in ["Absorber","Condenser","Evaporator","Generator"]:
        solution=kind in {"Absorber","Generator"}
        medium=L if solution else W
        p=7406 if kind in {"Generator","Condenser"} else 2000
        ports={"Absorber":["port_l_a","port_l_b","port_v","port_v_a"],"Generator":["port_l_a","port_l_b","port_v"],
               "Condenser":["port_v","port_l"],"Evaporator":["port_l_a","port_v_a","port_v"]}[kind]
        liquid=[port for port in ports if port.startswith('port_l')]
        for interface in ["heatport","internalHEX"]:
            target=D+kind+"Dyn_"+interface
            for through in [False,True]:
                name=kind+"Dyn_"+interface+("ThroughFlow" if through else "Closed")
                decl=f"    inner Modelica.Fluid.System system;\n    {target} dut(p_start={p},UA=50"+(",X_LiBr_start=0.6" if solution else "")+");\n"
                eq=""
                initial="    dut.T=dut.T_start; dut.V_l=dut.V_l_start;\n"
                if solution:initial+="    dut.X_LiBr=0.6;\n"
                if through:
                    if kind=="Absorber": rates={"port_l_a":"0.005","port_l_b":"-0.00502","port_v":"0.00002"}
                    elif kind=="Generator":rates={"port_l_a":"0.005","port_l_b":"-0.00498","port_v":"-0.00002"}
                    elif kind=="Condenser":rates={"port_v":"0.0002","port_l":"-0.0002"}
                    else:rates={"port_l_a":"0.0002","port_v":"-0.0002"}
                    for i,port in enumerate(ports):
                        pm=medium if port in liquid else V
                        temp="dut.T_start" if solution and port in liquid else ("dut.T_start-2" if port in liquid else "dut.T_start+5")
                        # A source defines its own state even when it is withdrawing fluid.
                        b=flow_source("flow"+str(i),port,pm,"("+rates.get(port,"0")+")*(if time<30 then 1 else 0.5)",temp,",X={0.4,0.6}" if solution and port in liquid else "")
                        decl+=b[0];eq+=b[1]
                if interface=="heatport":
                    decl+="    Modelica.Thermal.HeatTransfer.Sources.PrescribedHeatFlow heat;\n"
                    eq+="    heat.Q_flow=if time<20 then 100 elseif time<40 then 0 else -100;\n    connect(heat.port,dut.heatPort);\n"
                    heat="dut.heatPort.Q_flow"
                else:
                    cooling=kind in {"Absorber","Condenser"}
                    for b in [flow_source('externalSource','port_a_ext',W,"0.2",f"dut.T_start{'-' if cooling else '+'}(if time<30 then 5 else 3)"),
                              pressure_sink('externalSink','port_b_ext',W,300000,300)]:
                        decl+=b[0];eq+=b[1]
                    heat=port_flux(['port_a_ext','port_b_ext'])
                decl+=f'''    parameter Real initialMass(fixed=false);
    parameter Real initialEnergy(fixed=false);
    Real integratedMass(start=0,fixed=true);
    Real integratedEnergy(start=0,fixed=true);
    Real r_mass=dut.m-initialMass-integratedMass;
    Real r_energy=dut.U-initialEnergy-integratedEnergy;
    Real volumeFraction=dut.V_l/dut.V;
'''
                initial+="    initialMass=dut.m; initialEnergy=dut.U;\n"
                eq+=f"    der(integratedMass)={port_flux(ports,'mass')};\n    der(integratedEnergy)={port_flux(ports)}+({heat});\n"
                metrics={"r_mass":1e-5,"r_energy":0.2}
                ranges={"volumeFraction":[0.001,0.999],"dut.T":[273.15,450],"dut.p":[611.657,100000]}
                if solution:
                    decl+="    parameter Real initialSalt(fixed=false);\n    Real integratedSalt(start=0,fixed=true);\n    Real r_salt=dut.m_l*dut.X_LiBr-initialSalt-integratedSalt;\n"
                    initial+="    initialSalt=dut.m_l*dut.X_LiBr;\n"
                    eq+=f"    der(integratedSalt)={port_flux(liquid,'salt')};\n"
                    metrics['r_salt']=1e-5;ranges['dut.X_LiBr']=[0.4,0.7]
                add(name,target,decl,eq,metrics,("Mass/enthalpy through-flow with step" if through else "Sealed working-fluid volume with thermal excitation")+"; integrated inventory checks",
                    initial=initial,stop=60,ranges=ranges,notes="Mass and internal energy are the library default states. Independent boundary-flux integrals; no balance laws added to DUT.")


def evaporators_series():
    target=D+'EvaporatorDyn_heatport'
    for suffix, heat, feed in [('Nominal', False, False), ('HeatStep', True, False), ('FeedStep', False, True)]:
        declarations=f'''    extends {D}Validation.EvaporatorsSeries_heatport(
      useHeatStep={str(heat).lower()}, useFeedStep={str(feed).lower()});'''
        ranges={
            'eva1.T':[273.16,310], 'eva2.T':[273.16,310],
            'eva1.p':[611.657,4000], 'eva2.p':[611.657,4000],
            'liquidFraction1':[0.4,0.6], 'liquidFraction2':[0.4,0.6],
            'm_feed':[0.00019,0.00041], 'm_series':[0.0001,0.001],
            'm_out':[0.0002,0.002], 'dp_series':[1,300],
            'eva1.Qb_flow':[999,1401], 'eva2.Qb_flow':[799,1101],
        }
        excursions={'massChange2':{'min_at_most':-0.25}}
        if heat:
            excursions.update({'m_series':{'min_at_most':0.00043,'max_at_least':0.0005},
                               'm_out':{'min_at_most':0.0008,'max_at_least':0.00095}})
        if feed:
            excursions.update({'m_feed':{'min_at_most':0.00021,'max_at_least':0.00039},
                               'massChange1':{'min_at_most':-0.07}})
        add('EvaporatorsSeries'+suffix, target, declarations, '',
            {'r_mass1':1e-5,'r_mass2':1e-5,'r_massTotal':1e-5,
             'r_energy1':2,'r_energy2':2,'r_energyTotal':2,
             'r_seriesMass':1e-10,'r_seriesEnergy':1e-5},
            'Two evaporators in refrigerant-vapor series: '+suffix,
            stop=1200, ranges=ranges, excursions=excursions,
            notes='Liquid feed enters stage 1 only; stage 2 consumes its initial charge. '
                  'Vapor connectors are joined through an adiabatic resistance. '
                  'Per-stage and overall boundary-flux inventory checks; no added DUT balance equations.')
        cases[-1]['strict_initialization']=True


def bases():
    for name in ["LMTD","ChenMTD","MTD"]:
        variants=[("","")]
        if name=="MTD":variants += [("Chen","(usedT_log=false)"),("Events","(useNoEvent=false)"),("Homotopy","(useHomotopy=true)")]
        for suffix,mod in variants:
            target=S+"BaseClasses."+name
            decl=f'''    model Concrete
      extends {target}{mod};
    end Concrete;
    Concrete dut;
    Real r_equal=if time<2 then dut.dT_used-5 else 0;
    Real r_bound=if time<6 then max(0,max(min(dut.dT1,dut.dT2)-dut.dT_used,dut.dT_used-max(dut.dT1,dut.dT2))) else 0;
    Real r_reference=if time>=2 and time<4 then dut.dT_used-4.32808512266689 else 0;
    Real r_near=if time>=8 then dut.dT_used-5.000000005 else 0;'''
            eq="    dut.dT1=if time<2 then 5 elseif time<4 then 2 elseif time<6 then 0 elseif time<8 then -1 else 5.00000001;\n    dut.dT2=if time>=2 and time<4 then 8 else 5;"
            metrics={"r_equal":1e-10,"r_bound":1e-9,"r_reference":0.01 if name=="ChenMTD" or suffix=="Chen" else 1e-9,"r_near":1e-9}
            if name=="LMTD":
                decl+='\n    Real r_zeroLimit=if time>=4 and time<6 then dut.dT_used else 0;'
                metrics['r_zeroLimit']=1e-10
            add("Base_"+name+suffix,target,decl,eq,metrics,
                "Equal, unequal, zero, negative and nearly equal terminal temperature differences",
                notes="Negative differences check the documented numerical fallback only; no heat-transfer accuracy claim in that regime.")


def statics():
    groups={"SingleEffect_intern":["AbsorberStatic","CondenserStatic","EvaporatorStatic","GeneratorStatic"],
            "SingleEffect_UAfixed":["AbsorberStatic_wHT_UAfix","CondenserStatic_wHT_UAfix","EvaporatorStatic_wHT_UAfix","GeneratorStatic_wHT_UAfix"],
            "DoubleEffect":["CondenserStatic_de_UAfix","LowGeneratorStatic","LowGeneratorStatic_serie"],
            "TypeII":["AbsorberStatic_wHT_UAfix_TypeII","AbsorberStatic_wHT_UAfix_TypeII_ext","EvaporatorStatic_wHT_UAfix_TypeII","GeneratorStatic_wHT_UAfix_TypeII"],
            "Resorption":["AbsorberStatic_wHT_UAfix_Resorption_ext"]}
    for group,names in groups.items():
        for name in names:
            target=S+group+'.'+name
            source=(ROOT / (target.replace('.','/')+'.mo')).read_text(encoding='utf-8-sig')
            # Exact declared ports, never guessed names from class names.
            ports=re.findall(r'Modelica.Fluid.Interfaces.FluidPort_[ab]\s+(\w+)',source)
            working=[p for p in ports if not p.endswith('_ext')]
            absorber='Absorber' in name
            generator='Generator' in name
            solution=absorber or generator
            condenser='Condenser' in name
            low=name.startswith('LowGenerator')
            ext='port_a_ext' in ports
            liquid=[p for p in working if '_l' in p]
            vapor=[p for p in working if p not in liquid]
            medium=L if solution else W
            pressure=7406 if generator or condenser else 2000
            if absorber and group in {'TypeII','Resorption'}:pressure=20000
            modifiers=[f'redeclare package Medium_l={medium}',f'redeclare package Medium_v={V}']
            if 'p_start' in source:modifiers+=[f'p_start={pressure}']
            if solution:modifiers+=['X_LiBr_start=0.6']
            if ext:modifiers += [f'redeclare package Medium_ext={W}','UA=100']
            if low:modifiers+=['UA=100']
            if 'use_p_in' in source:modifiers+=['use_p_in=false']
            if 'use_X_LiBr_in' in source:modifiers+=['use_X_LiBr_in=false' if absorber else 'use_X_LiBr_in=true']
            decl=f"    inner Modelica.Fluid.System system;\n    {target} dut({','.join(modifiers)});\n"
            eq=''
            if 'use_X_LiBr_in' in source and not absorber:eq+='    dut.X_LiBr_in=0.62;\n'
            out='port_l_b' if solution else ('port_l' if condenser else 'port_v')
            input_port='port_l_high' if name.endswith('_serie') else ('port_l_a' if solution or not condenser else 'port_v')
            b=pressure_sink('outlet',out,medium if out in liquid else V,pressure,300,',X={0.4,0.6}' if solution else '')
            decl+=b[0];eq+=b[1]
            # UA water vessels determine throughput from heat exchange; internal
            # vessels determine heat duty from a prescribed throughput.
            free_throughput=(ext and not solution) or low
            if free_throughput:
                # Only ONE pressure is independent; use an enthalpy-only boundary
                # to leave the common saturation pressure at the outlet's value.
                decl+=f"    EnthalpyBoundary inlet(redeclare package Medium={medium if input_port in liquid else V},T={'350' if low else ('400' if condenser else '285')}"+(",X={0.4,0.6}" if low else "")+");\n"
                eq+=f"    connect(inlet.port,dut.{input_port});\n"
            else:
                tin='350' if solution and generator else ('365' if absorber and pressure==20000 else ('330' if absorber else ('400' if condenser else '285')))
                b=flow_source('inlet',input_port,medium if input_port in liquid else V,'(if time<5 then 0.005 else 0.004)' if solution else '(if time<5 then 0.001 else 0.0005)',tin,',X={0.4,0.6}' if solution else '')
                decl+=b[0];eq+=b[1]
            for i,port in enumerate(working):
                if port in {out,input_port}:continue
                if generator and port=='port_v':
                    # Vapor outlet shares the liquid outlet pressure through DUT.
                    decl+=f"    EnthalpyBoundary vaporOutlet(redeclare package Medium={V},T=400);\n"
                    eq+='    connect(vaporOutlet.port,dut.port_v);\n'
                elif absorber and port=='port_v':
                    if ext:
                        # Fixed p, liquid feed and cooling-water conditions plus
                        # UA determine absorption rate through DUT conservation.
                        decl+=f"    EnthalpyBoundary steam(redeclare package Medium={V},T=400);\n"
                        eq+='    connect(steam.port,dut.port_v);\n'
                    else:
                        b=flow_source('steam',port,V,'0.0004','400');decl+=b[0];eq+=b[1]
                else:
                    b=flow_source('unused'+str(i),port,medium if port in liquid else V,'0','350' if solution else ('400' if port in vapor else '285'),',X={0.4,0.6}' if solution and port in liquid else '')
                    decl+=b[0];eq+=b[1]
            if ext:
                temp='(if time<5 then 373.15 else 375.15)' if generator else ('(if time<5 then 300 else 298)' if condenser else ('(if time<5 then 300 else 302)' if not absorber else ('(if time<5 then 360 else 358)' if pressure==20000 else '(if time<5 then 310 else 308)')))
                for b in [flow_source('externalSource','port_a_ext',W,'0.2',temp),pressure_sink('externalOutlet','port_b_ext',W,300000,300)]:
                    decl+=b[0];eq+=b[1]
            if low:
                # Both scalar inputs are intentionally supplied. The two
                # pressures and heat duty are then allowed to determine flow.
                eq+='    dut.T_c=if time<5 then 370 else 372;\n'
                # Hb_flow_in is an inverse-use input in upstream examples;
                # this fixture drives heat duty and solves source throughput.
                eq+='    dut.Hb_flow_in=-1000;\n'
            decl+=f"    Real r_mass={port_flux(working,'mass')};\n"
            metrics={'r_mass':1e-8}
            if solution:
                decl+=f"    Real r_salt={port_flux(liquid,'salt')};\n";metrics['r_salt']=1e-8
            if ext:
                decl+=f"    Real r_energy={port_flux(ports)};\n    Real r_externalMass={port_flux(['port_a_ext','port_b_ext'],'mass')};\n"
                metrics.update(r_energy=.05,r_externalMass=1e-9)
            else:
                # Internal-only static vessels expose heat duty as an output.
                decl+=f"    Real r_duty={port_flux(working)}-dut.Hb_flow;\n";metrics['r_duty']=.01
            ranges={'dut.T':[273.15,500],f'dut.{input_port}.m_flow':[1e-8,None],f'dut.{out}.m_flow':[None,-1e-8],
                    'dut.Hb_flow':[-1e8,-1e-5] if generator or not absorber and not condenser else [1e-5,1e8]}
            if solution:ranges['dut.X_LiBr']=[0.4,0.7]
            if absorber and ext:ranges['dut.port_v.m_flow']=[1e-8,None]
            if group=='SingleEffect_intern' and generator:
                # OMC promotes T(p,X) to a calculated parameter, which CSV
                # does not contain. Check it in Modelica rather than guessing
                # a parameter value from init.xml start attributes.
                del ranges['dut.T']
                eq+='    assert(noEvent(dut.T>=273.15 and dut.T<=500), "Generator equilibrium temperature outside test range");\n'
            add(group+'_'+name,target,decl,eq,metrics,"Standalone steady vessel with physical fluid boundaries and a load/temperature step",
                ranges=ranges,notes="EnthalpyBoundary leaves flow and pressure unconstrained; it does not impose DUT conservation laws. A UA absorber solves its steam intake from the prescribed pressure, solution feed and cooling-water conditions. Auxiliary flow ports are sealed by zero-flow sources. Both inputs T_c and Hb_flow_in are supplied for the low generator, allowing throughput to be solved.")


def main():
    basics();pumps();compressor();flashing();hexes();dynamics();bases();statics();evaporators_series()
    header='''within ;
package ComponentTests "Standalone component tests; generated by tests/generate_components.py"
  model EnthalpyBoundary "Only the entering stream state is prescribed; p and m_flow are free"
    replaceable package Medium=Modelica.Media.Water.WaterIF97_R1pT;
    parameter Modelica.Units.SI.Temperature T=300;
    parameter Medium.MassFraction X[Medium.nX]=Medium.X_default;
    Modelica.Fluid.Interfaces.FluidPort_b port(redeclare package Medium=Medium);
  equation
    port.h_outflow=Medium.specificEnthalpy(Medium.setState_pTX(port.p,T,X));
    port.Xi_outflow=X[1:Medium.nXi];
    port.C_outflow=zeros(Medium.nC);
  end EnthalpyBoundary;
'''
    (HERE/'Components.mo').write_text(header+'\n'.join(models)+'end ComponentTests;\n',encoding='utf-8')
    (HERE/'components.json').write_text(json.dumps({'schema':1,'cases':cases},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f'{len(cases)} cases for {len(set(c["component"] for c in cases))} component targets')


if __name__=='__main__':main()
