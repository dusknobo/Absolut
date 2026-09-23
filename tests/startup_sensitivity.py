"""Check the extended heatport startup at two DASSL tolerances."""
from pathlib import Path
import concurrent.futures
import csv
import hashlib
import json
import math
import os
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import verify

BUILD = ROOT/'build/initialization/4.0.0/heatport_extended'
EXE = BUILD/('model.exe' if os.name == 'nt' else 'model')
OUT = ROOT/'build/initialization/startup_sensitivity'
OUT.mkdir(parents=True, exist_ok=True)
source_sha = hashlib.sha256(b''.join(p.relative_to(ROOT).as_posix().encode()+b'\0'+p.read_bytes()
    for p in sorted((ROOT/'Absolut').rglob('*.mo')))).hexdigest()
initialization = json.loads((ROOT/'reports/initialization.json').read_text())
assert initialization['source_sha256'] == source_sha
assert initialization['summary'] == {'pass': 6, 'fail': 0}
assert EXE.stat().st_mtime >= max(p.stat().st_mtime for p in (ROOT/'Absolut').rglob('*.mo'))
variables = [f'ahp.{v}.{f}' for v in ('abs', 'gen', 'con', 'eva') for f in ('T','p','m','U','Qb_flow')]
variables += [f'der(ahp.{v}.U)' for v in ('abs','gen','con','eva')]
variables += ['ahp.abs.mXLiBr[1]', 'ahp.gen.mXLiBr[1]', 'ahp.pump_abstogen.W_p',
              'ahp.flashingLiBr.port_a.m_flow', 'ahp.flashingLiBr.port_l_b.m_flow',
              'ahp.flashingLiBr.X_LiBr_in', 'ahp.flashingLiBr.X_LiBr_out',
              'ahp.hex_abs.Q2_flow', 'ahp.hex_gen.Q2_flow']
pattern = '^('+'|'.join(re.escape(v) for v in variables)+')$'
environment = os.environ.copy()
omc_home = Path(verify.find_omc(None)).parent.parent
environment['PATH'] = str(omc_home/'bin')+os.pathsep+str(omc_home/'tools/msys/mingw64/bin')+os.pathsep+environment['PATH']


def run(tolerance):
    csv_path = OUT/f'tol_{tolerance}.csv'
    log_path = OUT/f'tol_{tolerance}.log'
    if csv_path.is_file():
        csv_path.unlink()
    command = [str(EXE), '-startTime=0', '-stopTime=2000', '-stepSize=1',
               '-tolerance='+tolerance, '-s=dassl', '-outputFormat=csv',
               '-r='+str(csv_path), '-variableFilter='+pattern,
               '-lv=LOG_STDOUT,LOG_ASSERT,LOG_STATS,LOG_SUCCESS']
    with log_path.open('w', encoding='utf-8') as stream:
        process = subprocess.run(command, cwd=BUILD, env=environment, stdout=stream, stderr=subprocess.STDOUT, timeout=180)
    log = log_path.read_text(encoding='utf-8')
    with csv_path.open(newline='', encoding='utf-8') as stream:
        rows = [{k:float(v) for k,v in row.items()} for row in csv.DictReader(stream)]
    result = {'tolerance': tolerance, 'returncode': process.returncode, 'command': command,
              'log': str(log_path.relative_to(ROOT)), 'result': str(csv_path.relative_to(ROOT)),
              'finite': bool(rows) and all(math.isfinite(v) for row in rows for v in row.values()),
              'final_time': rows[-1]['time'] if rows else None,
              'success': 'simulation finished successfully' in log,
              'initialization': verify.heatport_initialization_check(log),
              'conservation': verify.heatport_conservation(csv_path, ('ahp.hex_abs.Q2_flow', 'ahp.hex_gen.Q2_flow'))}
    result['artifact_sha256'] = {f: hashlib.sha256((ROOT/result[f]).read_bytes()).hexdigest() for f in ('log', 'result')}
    result['pass'] = (process.returncode == 0 and result['finite'] and result['success']
                      and result['final_time'] == 2000 and result['conservation']['pass']
                      and result['initialization']['pass'])
    print(json.dumps(result), flush=True)
    samples = {round(row['time']): row for row in rows if abs(row['time']-round(row['time'])) < 1e-7}
    return result, samples


with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    runs = list(pool.map(run, ('1e-7','1e-8')))
before, after = [r[1] for r in runs]
common = set(before) & set(after)
assert len(common) >= 1990 and 0 in common and 2000 in common
groups = {'temperature_K': 'T', 'pressure_Pa': 'p', 'heat_W': 'Qb_flow'}
maximum = {label: max(abs(before[t][f'ahp.{v}.{field}']-after[t][f'ahp.{v}.{field}'])
                     for t in common for v in ('abs','gen','con','eva')) for label, field in groups.items()}
limits = {'temperature_K': 0.01, 'pressure_Pa': 1.0, 'heat_W': 10.0}
passed = all(r[0]['pass'] for r in runs) and all(maximum[k] <= limits[k] for k in limits)
report = {'source_sha256': source_sha, 'test_source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
           for p in (Path(__file__), ROOT/'verify.py')},
          'model': verify.HEATPORT_CASE+'_extended', 'modelica': '4.0.0',
          'pass': passed, 'common_points': len(common), 'maximum_absolute_difference': maximum,
          'limits': limits, 'results': [r[0] for r in runs]}
(ROOT/'reports/startup_sensitivity.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'pass': passed, 'maximum': maximum}), flush=True)
raise SystemExit(0 if passed else 1)
