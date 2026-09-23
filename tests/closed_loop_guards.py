"""Prove that invalid closed-loop balance delegation is rejected at runtime.

These are negative tests: both simulations MUST build and then fail the
appropriate conservation assertion. They do not count as component scenarios.
"""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--omc')
    parser.add_argument('--buildings', type=Path, default=ROOT.parent/'Buildings 12.0.0/package.mo')
    args = parser.parse_args()
    omc = verify.find_omc(args.omc)
    header = verify.preamble(args.buildings.resolve())
    header += 'setCommandLineOptions("--preOptModules-=evalFunc");\n'
    header += f'loadFile({verify.quote(ROOT/"tests/Components.mo")});\ngetErrorString();\n'
    results = []
    for case, flow, concentration, message in [
        ('MassMismatch', -0.006, 0.5, 'Closed-circuit mass balance is not satisfied'),
        ('SaltMismatch', -0.0054, 0.58, 'Closed-circuit LiBr balance is not satisfied'),
    ]:
        directory = ROOT / 'build/closed_loop_guards' / case
        exe = directory / ('model.exe' if sys.platform == 'win32' else 'model')
        if exe.is_file():
            exe.unlink()
        definition = f'''model {case}
  extends ComponentTests.SingleEffect_intern_AbsorberStatic(
    dut(useClosedLoopMassBalance=true, useClosedLoopSaltBalance=true));
equation
  dut.port_l_b.m_flow={flow};
  dut.X_LiBr={concentration};
end {case};'''
        script = header + f'loadString({verify.quote(definition)});\ngetErrorString();\n'
        script += f'simulate({case}, stopTime=1, numberOfIntervals=10, fileNamePrefix="model");\ngetErrorString();\n'
        result = verify.run_omc(omc, directory, script, 120)
        log = (directory / 'omc.log').read_text(encoding='utf-8', errors='replace')
        passed = exe.is_file() and message in log and 'simulation finished successfully' not in log and not result['timeout']
        result.update(case=case, status='pass' if passed else 'fail',
                      expected_assertion=message, built=exe.is_file(),
                      log_sha256=hashlib.sha256((directory/'omc.log').read_bytes()).hexdigest())
        results.append(result)
        print(f'{result["status"].upper()} {case}: expected simulation rejection', flush=True)
    report = dict(timestamp_utc=datetime.now(timezone.utc).isoformat(),
                  compiler=subprocess.check_output([omc, '--version'], text=True).strip(),
                  source_sha256=hashlib.sha256(b''.join(
                      p.relative_to(ROOT).as_posix().encode()+b'\0'+p.read_bytes()
                      for p in sorted((ROOT/'Absolut').rglob('*.mo')))).hexdigest(),
                  test_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  results=results, summary={s:sum(r['status']==s for r in results) for s in ['pass','fail']})
    (ROOT/'reports/closed_loop_guards.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return 0 if report['summary']['fail']==0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
