"""Reproducible OpenModelica checks; Python standard library only."""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
TEST_DIRS = {"Examples", "Validation", "CheckDerivatives", "CheckThermalOil", "Test", "LabValidation"}
MISSING_DATA = {
    "Absolut.FluidBased.Dynamic.LabValidation.Data.sBSc_1m_Cfg0_20220804",
    "Absolut.FluidBased.Dynamic.LabValidation.Test_AHX_wcp_extended_wheatloss_pump_controlled",
}
SMOKE = {
    "Absolut.Basic.Examples.CoolingCOP",
    "Absolut.Media.LiBrH2O.Validation.Enthalpy",
    "Absolut.FluidBased.Static.SingleEffect_intern.Validation.AHP_se_eps",
    "Absolut.FluidBased.Dynamic.Components.Validation.AHPse_Dyn_heatport",
}
HEX_TEMPLATES = {
    "Absolut.FluidBased.Static.Components.HEX." + name
    for name in ("ConstantEffectiveness", "PlateHeatExchangerEffectivenessNTU", "simpleHX")
}
HEATPORT_CASE = "Absolut.FluidBased.Dynamic.Components.Validation.AHPse_Dyn_heatport"


def quote(value):
    return json.dumps(str(value).replace("\\", "/"), ensure_ascii=False)


def discover():
    models = {}
    for path in sorted((ROOT / "Absolut").rglob("*.mo")):
        source = path.read_text(encoding="utf-8-sig")
        if re.search(r"^\s*model\s+\w+", source, re.M):
            name = ".".join(path.relative_to(ROOT).with_suffix("").parts)
            models[name] = path
    return models


def find_omc(value):
    candidates = [value, shutil.which("omc")]
    if os.environ.get("OPENMODELICAHOME"):
        candidates.append(str(Path(os.environ["OPENMODELICAHOME"]) / "bin" / ("omc.exe" if os.name == "nt" else "omc")))
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    raise SystemExit("omc not found. Set OPENMODELICAHOME or pass --omc /path/to/omc.")


def preamble(buildings):
    return "\n".join([
        'getVersion();',
        'if not loadModel(Modelica, {"4.0.0"}, requireExactVersion=true) then',
        '  print(getErrorString()); exit(1);',
        'end if;',
        f'if not loadFile({quote(buildings)}) then',
        '  print(getErrorString()); exit(1);',
        'end if;',
        'if getVersion(Buildings) <> "12.0.0" then',
        '  print("Buildings 12.0.0 is required."); exit(1);',
        'end if;',
        f'if not loadFile({quote(ROOT / "Absolut/package.mo")}) then',
        '  print(getErrorString()); exit(1);',
        'end if;',
        'getErrorString();',
    ]) + "\n"


def run_omc(omc, directory, script, timeout):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "run.mos").write_text(script, encoding="utf-8")
    started = time.monotonic()
    timed_out = False
    with (directory / "omc.log").open("wb") as log:
        proc = subprocess.Popen([omc, "run.mos"], cwd=directory, stdout=log, stderr=subprocess.STDOUT)
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                proc.kill()
            proc.wait()
    return {
        "returncode": proc.returncode,
        "timeout": timed_out,
        "seconds": round(time.monotonic() - started, 2),
        "log": str((directory / "omc.log").relative_to(ROOT)),
    }


def checks(args, models, header):
    script = header
    for name in models:
        target = name
        if name in HEX_TEMPLATES:
            # These reusable Buildings components intentionally have partial media.
            # Check a representative redeclaration, rather than inventing library defaults.
            target = "OMCheck" + name.rsplit(".", 1)[1]
            modifiers = "redeclare package Medium1=Modelica.Media.Water.WaterIF97_R1pT, redeclare package Medium2=Modelica.Media.Water.WaterIF97_R1pT, m1_flow_nominal=1, m2_flow_nominal=1, dp1_nominal=1000, dp2_nominal=1000"
            if not name.endswith(".ConstantEffectiveness"):
                modifiers += ", configuration=Buildings.Fluid.Types.HeatExchangerConfiguration.CounterFlow"
            if name.endswith(".PlateHeatExchangerEffectivenessNTU"):
                modifiers += ", Q_flow_nominal=10000, T_a1_nominal=353.15, T_a2_nominal=293.15"
            definition = f"model {target} extends {name}({modifiers}); end {target};"
            script += f'loadString({quote(definition)});\n'
        script += f'print("\\n=== {name} ===\\n");\ncheckModel({target});\ngetErrorString();\n'
    directory = ROOT / "build/check"
    process = run_omc(args.omc, directory, script, max(args.timeout, 600))
    log = (directory / "omc.log").read_text(encoding="utf-8", errors="replace")
    sections = re.split(r"=== (Absolut\.[\w.]+) ===", log)
    output = dict(zip(sections[1::2], sections[2::2]))
    results = []
    for name in models:
        section = output.get(name, "")
        ok = "completed successfully" in section and "Error:" not in section
        counts = re.search(r"has (\d+) equation\(s\) and (\d+) variable\(s\)", section)
        result = {"model": name, "status": "pass" if ok else "fail", "errors": re.findall(r".*Error:.*", section)}
        if counts:
            result.update(equations=int(counts[1]), variables=int(counts[2]))
        result["warnings"] = section.count("Warning:")
        if name in HEX_TEMPLATES:
            result["configuration"] = "Both media redeclared to WaterIF97_R1pT; see generated run.mos for nominal parameters."
        results.append(result)
    return results, process


def heatport_conservation(path, extra_solution_heat=()):
    """Check independent closed-loop and massless-valve conservation invariants."""
    limits = {"mass_drift_kg":1e-5, "libr_drift_kg":1e-4,
              "energy_residual_W":0.1, "flash_libr_residual_kg_s":1e-8}
    maximum = dict.fromkeys(limits, 0.0)
    initial = None
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            value = lambda name: float(row[name])
            mass = sum(value(f"ahp.{v}.m") for v in ("abs", "gen", "con", "eva"))
            salt = sum(value(f"ahp.{v}.mXLiBr[1]") for v in ("abs", "gen"))
            if initial is None:
                initial = mass, salt
            residuals = {
                "mass_drift_kg":mass-initial[0],
                "libr_drift_kg":salt-initial[1],
                "energy_residual_W":sum(value(f"der(ahp.{v}.U)")-value(f"ahp.{v}.Qb_flow")
                                        for v in ("abs", "gen", "con", "eva"))-value("ahp.pump_abstogen.W_p")
                    -sum(value(column) for column in extra_solution_heat),
                "flash_libr_residual_kg_s":value("ahp.flashingLiBr.port_a.m_flow")*value("ahp.flashingLiBr.X_LiBr_in")
                    +value("ahp.flashingLiBr.port_l_b.m_flow")*value("ahp.flashingLiBr.X_LiBr_out"),
            }
            for key, residual in residuals.items():
                if not math.isfinite(residual):
                    raise ValueError(f"Non-finite physical residual: {key}")
                maximum[key] = max(maximum[key], abs(residual))
    return {"pass":initial is not None and all(maximum[k]<=limits[k] for k in limits),
            "maximum":maximum, "limits":limits,
            "extra_solution_heat":list(extra_solution_heat),
            "scope":"Working-fluid inventory, energy equations including listed external solution heat exchangers, and forward-flow flashing-valve LiBr balance at saved output times; not experimental validation."}


def static_cycle_balances(path, name):
    """Verify every balance explicitly delegated to the surrounding closed loop."""
    source = ROOT / (name.replace('.', '/') + '.mo')
    if not source.is_file():
        return None
    references = re.findall(
        r'\bAbsorberStatic\w*\s+(\w+)\(\s*useClosedLoopMassBalance=(true|false),'
        r'\s*useClosedLoopSaltBalance=(true|false),', source.read_text(encoding='utf-8-sig'))
    columns = [f'{instance}.{field}Residual' for instance, mass, salt in references
               for field, enabled in [('mass', mass), ('salt', salt)] if enabled == 'true']
    if not columns:
        return None
    maximum = dict.fromkeys(columns, 0.0)
    rows = 0
    with path.open(encoding='utf-8', newline='') as stream:
        for row in csv.DictReader(stream):
            rows += 1
            for column in columns:
                value = float(row[column])
                if not math.isfinite(value):
                    raise ValueError(f'Non-finite closed-circuit balance: {column}')
                maximum[column] = max(maximum[column], abs(value))
    return {'pass': bool(rows) and all(v <= 1e-8 for v in maximum.values()),
            'maximum_kg_s': maximum, 'limit_kg_s': 1e-8,
            'scope': 'All saved mass and LiBr residuals replacing redundant equations in a closed steady circuit; also asserted by the Modelica component.'}


def forward_flow_check(path):
    """Check the design-flow assumption used by the two heatport variants."""
    with path.open(encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream)
        columns = [c for c in reader.fieldnames if
                   (c.startswith('ahp.pipe_') and '.m_flows[' in c) or
                   (c.startswith('ahp.hex') and '.port_a' in c and c.endswith('.m_flow'))]
        if not columns:
            raise ValueError('No pipe or heat exchanger flows found for direction check')
        minimum = min(float(row[c]) for row in reader for c in columns)
    return {'pass': math.isfinite(minimum) and minimum >= -1e-8,
            'minimum_kg_s': minimum, 'lower_limit_kg_s': -1e-8,
            'columns_checked': len(columns)}


def heatport_initialization_check(log):
    """Reject compiler-repaired initialization and invalid temperature evaluations.

    A rejected nonlinear step followed by a successful retry is recorded separately;
    it is not a temperature-domain error or proof of a failed initialization.
    """
    errors = re.findall(r'^.*Error:.*$', log, re.M)
    adjustments = re.findall(
        r'^.*(?:Assuming fixed start|initial conditions are (?:not fully|over) specified).*$', log, re.M)
    domain_errors = re.findall(
        r'^.*(?:Argument of log\(T\)|[Dd]ivision by zero|assertion failed during initialization).*$', log, re.M)
    success = 'initialization finished successfully' in log
    return {'pass': success and not errors and not adjustments and not domain_errors,
            'success': success, 'translation_errors': errors,
            'initialization_adjustments': adjustments, 'runtime_domain_errors': domain_errors,
            'nonlinear_retries': len(re.findall(r'Solving non-linear system \d+ failed at time=', log))}


def simulate(args, name, header):
    result = {"model": name}
    if name in MISSING_DATA and args.data_file is None:
        return dict(result, status="blocked", reason="The upstream release does not include the experimental data file.")
    directory = ROOT / "build/sim" / (args.report or args.mode) / hashlib.sha256(name.encode()).hexdigest()[:10]
    # Remove only the old result file so a failed rerun cannot reuse stale output.
    old_result = directory / "model_res.csv"
    if old_result.is_file():
        old_result.unlink()
    target = name
    script = header
    if name in MISSING_DATA:
        target = "OMLaboratoryRun"
        definition = f'model {target} extends {name}(dataFile={quote(args.data_file)}); end {target};'
        script += f'loadString({quote(definition)});\ngetErrorString();\n'
    script += f'''
(t0, t1, tol, n, dt) := getSimulationOptions({name});
print("ORIGINAL_INTERVALS=" + String(n) + "\\n");
n := min(n, {args.max_intervals});
print("EXPECTED_STOP=" + String(t1, significantDigits=16) + "\\n");
simulate({target}, startTime=t0, stopTime=t1, tolerance=tol,
  numberOfIntervals=n, method={quote(args.method)}, simflags={quote(args.simflags)},
  outputFormat="csv", fileNamePrefix="model");
getErrorString();
'''
    result.update(run_omc(args.omc, directory, script, args.timeout))
    log = (directory / "omc.log").read_text(encoding="utf-8", errors="replace")
    result["status"] = "fail"
    result["errors"] = re.findall(r".*(?:Error:|LOG_ASSERT|failed|assertion).*", log)[:12]
    expected = re.search(r"EXPECTED_STOP=([-+\d.eE]+)", log)
    if expected:
        result["expected_stop"] = float(expected[1])
    original = re.search(r"ORIGINAL_INTERVALS=(\d+)", log)
    if original:
        result["original_intervals"] = int(original[1])
        result["output_intervals"] = min(int(original[1]), args.max_intervals)
    if old_result.is_file():
        try:
            with old_result.open(encoding="utf-8", newline="") as stream:
                reader = csv.reader(stream)
                columns = next(reader)
                time_col = columns.index("time")
                rows = 0
                all_finite = True
                for row in reader:
                    if not row:
                        continue
                    values = [float(v) for v in row]
                    all_finite = all_finite and all(math.isfinite(v) for v in values)
                    final_time = values[time_col]
                    rows += 1
                if rows:
                    result.update(final_time=final_time, rows=rows, finite=all_finite)
                    reached_end = expected and math.isclose(final_time, float(expected[1]), rel_tol=1e-9, abs_tol=1e-8)
                    if reached_end and all_finite and result["returncode"] == 0 and not result["timeout"] and "simulation finished successfully" in log:
                        result["status"] = "pass"
                    result["result"] = str(old_result.relative_to(ROOT))
                    if result['status'] == 'pass':
                        balances = static_cycle_balances(old_result, name)
                        if balances is not None:
                            result['static_cycle_balances'] = balances
                            if not balances['pass']:
                                result['status'] = 'fail'
                                result['errors'].append('Closed-circuit mass or LiBr balance failed')
                    if result["status"] == "pass" and name in {HEATPORT_CASE, HEATPORT_CASE+'_nocp', HEATPORT_CASE+'_extended'}:
                        result['initialization'] = heatport_initialization_check(log)
                        if not result['initialization']['pass']:
                            result['status'] = 'fail'
                            result['errors'].append('Heatport initialization or temperature-domain check failed')
                        extra_heat = ('ahp.hex_abs.Q2_flow', 'ahp.hex_gen.Q2_flow') if name.endswith('_extended') else ()
                        result["conservation"] = heatport_conservation(old_result, extra_heat)
                        if not result["conservation"]["pass"]:
                            result["status"] = "fail"
                            result["errors"].append("Working-fluid conservation check failed")
                        if name != HEATPORT_CASE:
                            result['forward_flow'] = forward_flow_check(old_result)
                            if not result['forward_flow']['pass']:
                                result['status'] = 'fail'
                                result['errors'].append('Forward-flow assumption violated')
        except (ValueError, StopIteration, OSError, KeyError) as error:
            result["status"] = "fail"
            result["errors"].append(str(error))
    print(f'{result["status"].upper():7} {name} ({result["seconds"]} s)', flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["check", "smoke", "simulate", "regression", "list"])
    parser.add_argument("--model", action="append", help="Model name substring; may be repeated")
    parser.add_argument("--omc")
    parser.add_argument("--buildings", type=Path, default=ROOT.parent / "Buildings 12.0.0/package.mo")
    parser.add_argument("--data-file", type=Path, help="Original laboratory data table (not included in the upstream release)")
    parser.add_argument("--timeout", type=int, default=600, help="Seconds per simulation including compilation")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--max-intervals", type=int, default=2000, help="Output sampling cap; does not shorten simulation or change solver tolerance")
    parser.add_argument("--method", default="dassl", help="OpenModelica integration method")
    parser.add_argument("--simflags", default="", help="Simulation runtime options")
    parser.add_argument("--flags", default="--preOptModules-=evalFunc", help="omc translation options; defaults to the validated workaround for partial function evaluation")
    parser.add_argument("--report", default=None, help="Report basename (without extension)")
    args = parser.parse_args()
    if args.report and Path(args.report).name != args.report:
        parser.error("--report must be a basename")
    if args.data_file:
        args.data_file = args.data_file.resolve()
        if not args.data_file.is_file():
            parser.error(f"Laboratory data file not found: {args.data_file}")
    models = discover()
    if args.mode == "regression":
        models = {"Regression." + name: ROOT / "tests/Regression.mo" for name in ("GibbsSecondDerivative", "MediumRoundTrip", "StableLogMean", "FlashingLiBrConservation")}
    if args.model:
        models = {name: path for name, path in models.items() if any(query in name for query in args.model)}
    if args.mode in {"simulate", "list"} and not args.model:
        models = {name: path for name, path in models.items() if TEST_DIRS.intersection(path.relative_to(ROOT).parts)}
    if args.mode == "smoke":
        models = {name: path for name, path in models.items() if name in SMOKE}
    if not models:
        parser.error("No matching models")
    if args.mode == "list":
        print("\n".join(models))
        return 0
    args.omc = find_omc(args.omc)
    args.buildings = args.buildings.resolve()
    if not args.buildings.is_file():
        parser.error(f"Buildings package not found: {args.buildings}")
    if args.jobs < 1 or args.timeout < 1 or args.max_intervals < 1:
        parser.error("--jobs, --timeout and --max-intervals must be positive")
    header = preamble(args.buildings)
    if args.mode == "regression":
        header += f'loadFile({quote(ROOT / "tests/Regression.mo")});\ngetErrorString();\n'
    if args.flags:
        header += f'setCommandLineOptions({quote(args.flags)});\n'
    version = subprocess.check_output([args.omc, "--version"], text=True).strip()
    report = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "compiler": version, "modelica": "4.0.0", "buildings": "12.0.0", "mode": args.mode, "translation_flags": args.flags, "method": args.method, "simulation_flags": args.simflags, "max_output_intervals": args.max_intervals}
    report["source_sha256"] = hashlib.sha256(b"".join(
        str(p.relative_to(ROOT)).replace("\\", "/").encode() + b"\0" + p.read_bytes()
        for p in sorted((ROOT / "Absolut").rglob("*.mo"))
    )).hexdigest()
    if args.mode == "regression":
        report["regression_source_sha256"] = hashlib.sha256((ROOT / "tests/Regression.mo").read_bytes()).hexdigest()
    if args.mode == "check":
        results, process = checks(args, models, header)
        report["process"] = process
    else:
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
            futures = {pool.submit(simulate, args, name, header): name for name in models}
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
    report["results"] = sorted(results, key=lambda item: item["model"])
    report["summary"] = {status: sum(item["status"] == status for item in results) for status in ("pass", "fail", "blocked")}
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    name = args.report or args.mode
    path = reports / (name + ".json")
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"]), flush=True)
    print(f"Report: {path}")
    # Missing laboratory data is visible in the report and gives a distinct exit code.
    return 1 if report["summary"]["fail"] else (2 if report["summary"]["blocked"] else 0)


if __name__ == "__main__":
    sys.exit(main())
