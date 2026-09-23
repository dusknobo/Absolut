"""Check heatport initialization and complete trajectories with MSL 4.0 and 4.1."""
from pathlib import Path
import concurrent.futures
import csv
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import verify

OMC = verify.find_omc(None)
FLAGS = '--preOptModules-=evalFunc -d=initialization'


def run(case):
    version, suffix = case
    model = verify.HEATPORT_CASE + suffix
    directory = ROOT / 'build/initialization' / version / ('heatport' + suffix)
    csv_path = directory / 'model_res.csv'
    if csv_path.is_file():
        csv_path.unlink()
    script = verify.preamble(ROOT.parent / 'Buildings 12.0.0/package.mo')
    script = script.replace('{"4.0.0"}', '{"' + version + '"}')
    script += f'print("MSL_VERSION=" + getVersion(Modelica) + "\\n");\n'
    script += f'setCommandLineOptions({verify.quote(FLAGS)});\n'
    script += f'simulate({model}, startTime=0, stopTime=86400, numberOfIntervals=500, tolerance=1e-7, method="dassl", outputFormat="csv", fileNamePrefix="model");\ngetErrorString();\n'
    result = verify.run_omc(OMC, directory, script, 300)
    log_path = directory / 'omc.log'
    log = log_path.read_text(encoding='utf-8', errors='replace')
    result.update(model=model, modelica=version)
    initialization = verify.heatport_initialization_check(log)
    result.update({key: value for key, value in initialization.items() if key not in ('pass', 'success')})
    result['remaining_warnings'] = [line for line in log.splitlines() if line.startswith('Warning:')]
    result['success'] = 'simulation finished successfully' in log
    result['initialization_success'] = 'initialization finished successfully' in log
    result['finite'] = False
    result['reached_stop'] = False
    if csv_path.is_file():
        with csv_path.open(newline='', encoding='utf-8') as stream:
            reader = csv.DictReader(stream)
            finite = True
            rows = 0
            for row in reader:
                finite = finite and all(math.isfinite(float(v)) for v in row.values())
                final_time = float(row['time'])
                rows += 1
        result.update(rows=rows, finite=finite and rows > 0,
                      final_time=final_time if rows else None,
                      reached_stop=rows > 0 and math.isclose(final_time, 86400, abs_tol=1e-7))
        extra = ('ahp.hex_abs.Q2_flow', 'ahp.hex_gen.Q2_flow') if suffix == '_extended' else ()
        result['conservation'] = verify.heatport_conservation(csv_path, extra)
        result['result'] = str(csv_path.relative_to(ROOT))
    result['pass'] = bool(result['returncode'] == 0 and not result['timeout']
        and f'MSL_VERSION={version}' in log
        and result['success'] and result['initialization_success']
        and not result['translation_errors'] and not result['initialization_adjustments']
        and not result['runtime_domain_errors']
        and result['finite'] and result['reached_stop']
        and result.get('conservation', {}).get('pass'))
    result['artifact_sha256'] = {field: hashlib.sha256((ROOT/result[field]).read_bytes()).hexdigest()
                                 for field in ('log', 'result') if field in result}
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result


if __name__ == '__main__':
    cases = [(version, suffix) for version in ('4.0.0', '4.1.0')
             for suffix in ('', '_nocp', '_extended')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, cases))
    report = {'timestamp_utc': datetime.now(timezone.utc).isoformat(),
              'translation_flags': FLAGS,
              'source_sha256': hashlib.sha256(b''.join(
                  p.relative_to(ROOT).as_posix().encode()+b'\0'+p.read_bytes()
                  for p in sorted((ROOT/'Absolut').rglob('*.mo')))).hexdigest(),
              'test_source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in (Path(__file__), ROOT/'verify.py')},
              'summary': {'pass': sum(r['pass'] for r in results),
                          'fail': sum(not r['pass'] for r in results)},
              'results': results}
    (ROOT/'reports/initialization.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    raise SystemExit(0 if all(r['pass'] for r in results) else 1)
