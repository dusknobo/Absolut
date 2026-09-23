"""Run every reusable component in isolation and assess physical residuals.

python component_tests.py --jobs 2
python component_tests.py --case FlashingLiBr --jobs 1
python component_tests.py --resume --jobs 2

Failed physics checks produce a nonzero exit code even if OMC reports success.
This runner never changes the library, supplies missing conservation equations,
or silently accepts earlier results from a different source/compiler/test set.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

import verify

ROOT=Path(__file__).resolve().parent


def digest(paths):
    return hashlib.sha256(b''.join(p.relative_to(ROOT).as_posix().encode()+b'\0'+p.read_bytes() for p in sorted(paths))).hexdigest()


def fixture_hash(package, name):
    helper=re.search(r'^  model EnthalpyBoundary\b[\s\S]*?^  end EnthalpyBoundary;',package,re.M).group(0)
    model=re.search(r'^  model '+re.escape(name)+r'\b[\s\S]*?^  end '+re.escape(name)+';',package,re.M).group(0)
    return hashlib.sha256((helper+'\n'+model).encode()).hexdigest()


def assess_csv(path, case):
    limits=case['residual_limits']
    maximum={k:0.0 for k in limits}
    observed={k:[math.inf,-math.inf] for k in set(case['ranges']) | set(case.get('excursions',{}))}
    finite=True
    rows=0
    first=last=None
    with path.open(encoding='utf-8',newline='') as stream:
        reader=csv.DictReader(stream)
        required={'time'} | set(limits) | set(observed)
        missing=required-set(reader.fieldnames or [])
        if missing:raise ValueError('Missing result columns: '+', '.join(sorted(missing)))
        for raw in reader:
            values={key:float(value) for key,value in raw.items()}
            finite=finite and all(math.isfinite(v) for v in values.values())
            t=values['time']
            if first is None:first=t
            last=t;rows+=1
            for key in maximum:maximum[key]=max(maximum[key],abs(values[key]))
            for key in observed:
                observed[key]=[min(observed[key][0],values[key]),max(observed[key][1],values[key])]
    failures=[]
    if not finite:failures.append('Non-finite output')
    if first is None or not math.isclose(first,0,abs_tol=1e-10) or not math.isclose(last,case['stop'],abs_tol=1e-8):
        failures.append(f'Incomplete trajectory: {first} to {last}; expected 0 to {case["stop"]}')
    for key,maximum_value in maximum.items():
        if maximum_value>limits[key]:failures.append(f'{key}: {maximum_value:.9g} > {limits[key]:.9g}')
    for key,(lo,hi) in observed.items():
        l,u=case['ranges'].get(key,[None,None])
        if (l is not None and lo<l) or (u is not None and hi>u):failures.append(f'{key}: observed [{lo:.9g}, {hi:.9g}], expected [{l}, {u}]')
        excursion=case.get('excursions',{}).get(key,{})
        if lo>excursion.get('min_at_most',math.inf) or hi<excursion.get('max_at_least',-math.inf):
            failures.append(f'{key}: required regimes were not both reached; observed [{lo:.9g}, {hi:.9g}]')
    return dict(rows=rows,finite=finite,first_time=first,final_time=last,maximum_residuals=maximum,
                observed_ranges=observed,physics_failures=failures)


def run_case(args,case,header,key):
    build_name='components' if args.modelica=='4.0.0' else 'components_msl_'+args.modelica
    directory=ROOT/'build'/build_name/case['case']
    directory.mkdir(parents=True,exist_ok=True)
    saved=directory/'assessment.json'
    if args.resume and saved.is_file():
        old=json.loads(saved.read_text(encoding='utf-8'))
        if old.get('validation_key')==key and old.get('status')=='pass':
            print('CACHED  '+case['case'],flush=True)
            return old
    result=dict(case,validation_key=key,executed_utc=datetime.now(timezone.utc).isoformat())
    result_file=directory/'model_res.csv'
    if result_file.is_file():result_file.unlink()
    script=header+f'''
checkModel({case['model']});
getErrorString();
simulate({case['model']},startTime=0,stopTime={case['stop']},numberOfIntervals=500,
  tolerance={case['tolerance']},method="dassl",outputFormat="csv",fileNamePrefix="model",
  simflags="-w -lv=LOG_STATS");
getErrorString();
'''
    result.update(verify.run_omc(args.omc,directory,script,args.timeout))
    log=(directory/'omc.log').read_text(encoding='utf-8',errors='replace')
    result['status']='fail'
    result['failure_stage']='translation_or_simulation'
    result['diagnostics']=re.findall(r'.*(?:Error:|LOG_ASSERT|LOG_WARNING|failed|singular|under-determined|over-determined).*',log)[:20]
    result['warning_count']=len(re.findall(r'Warning:|LOG_WARNING',log))
    counts=re.search(r'has (\d+) equation\(s\) and (\d+) variable\(s\)',log)
    if counts:result['equations']=int(counts[1]);result['variables']=int(counts[2])
    result['fixture_equation_count_equal']=not counts or counts[1]==counts[2]
    result['loaded_modelica_version_matches']=f'MSL_VERSION={args.modelica}' in log
    result['successful_simulation']=('simulation finished successfully' in log and not result['timeout']
                                     and result['returncode']==0 and result['loaded_modelica_version_matches'])
    if case.get('strict_initialization'):
        result['initialization']=verify.heatport_initialization_check(log)
    if result_file.is_file():
        result['result']=str(result_file.relative_to(ROOT))
        try:
            result.update(assess_csv(result_file,case))
            if result['successful_simulation']:
                result['failure_stage']='physics' if result['physics_failures'] else None
                result['status']='fail' if result['physics_failures'] else 'pass'
                if case.get('strict_initialization') and not result['initialization']['pass']:
                    result['status']='fail'
                    result['failure_stage']='initialization'
                    result['diagnostics'].append('Explicit initialization check failed')
                if not result['fixture_equation_count_equal']:
                    result['status']='fail'
                    result['failure_stage']='equation_balance'
        except (ValueError,KeyError,OSError) as exc:
            result['diagnostics'].append(str(exc))
    result['artifact_sha256']={field:hashlib.sha256((ROOT/result[field]).read_bytes()).hexdigest() for field in ('log','result') if field in result}
    saved.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f'{result["status"].upper():7} {case["case"]} ({result["seconds"]} s)'+(' '+ '; '.join(result.get('physics_failures',[])[:3]) if result['status']=='fail' else ''),flush=True)
    return result


def inventory():
    tests=verify.TEST_DIRS
    records=[]
    for path in sorted((ROOT/'Absolut').rglob('*.mo')):
        text=path.read_text(encoding='utf-8-sig')
        match=re.search(r'^\s*(partial model|model|function|package)\s+(\w+)',text,re.M)
        if not match:continue
        rel=path.relative_to(ROOT)
        name='.'.join(rel.with_suffix('').parts)
        kind=match[1]
        if tests.intersection(rel.parts):scope='existing_example_or_media_test'
        elif kind=='function':scope='function_not_component'
        elif kind=='package':scope='namespace'
        elif '.Dynamic.AHP.' in name:scope='system_assembly'
        elif name.endswith('.ReferenceData'):scope='reference_constants'
        else:scope='component'
        records.append(dict(name=name,path=rel.as_posix(),kind=kind,scope=scope))
    return records


def write_report(report,args):
    results=report['results']
    by_component={}
    for item in results:by_component.setdefault(item['component'],[]).append(item)
    report['case_summary']={s:sum(r['status']==s for r in results) for s in ('pass','fail')}
    report['components']=[dict(component=c,status='pass' if all(t['status']=='pass' for t in tests) else 'fail',
                              cases=[t['case'] for t in tests]) for c,tests in sorted(by_component.items())]
    report['component_summary']={s:sum(c['status']==s for c in report['components']) for s in ('pass','fail')}
    expected={x['name'] for x in report['inventory'] if x['scope']=='component'}
    report['uncovered_components']=sorted(expected-set(by_component))
    report['complete_coverage']=not report['uncovered_components']
    out=ROOT/'reports'/args.report
    out.parent.mkdir(exist_ok=True)
    out.with_suffix('.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    lines=['# 组件独立测试结果','',f"生成时间：{report['timestamp_utc']}。编译器：`{report['compiler']}`。Modelica：`{report['modelica']}`。",'',
           f"库源码 SHA-256：`{report['source_sha256']}`。测试包 SHA-256：`{report['test_source_sha256']}`。",'',
           f"本次执行 {len(results)} 个工况，涉及 {len(by_component)} 个组件/基类；工况通过 {report['case_summary']['pass']}、失败 {report['case_summary']['fail']}；组件通过 {report['component_summary']['pass']}、失败 {report['component_summary']['fail']}。",'',
           '“通过”要求编译运行成功、覆盖完整仿真时间、所有保存值有限，且独立物理残差与范围检查全部通过。没有把未能编译的模型、恢复后仍不守恒的运行或缺少结果的运行算作通过。', '',
           '测试范围为全部可复用叶组件及具体化后的换热基类；8 个整机组装模型、参考常数、函数和包单独列在 JSON 清单中。已有整机/物性案例报告不能替代此处的组件测试。', '',
           '## 各组件与工况','', '| 组件 | 工况 | 结果 | 失败原因 |','|---|---|---|---|']
    for r in sorted(results,key=lambda x:(x['component'],x['case'])):
        issues=r.get('physics_failures',[]) if r['successful_simulation'] else r.get('diagnostics',[])
        explanation='；'.join(issues[:2]).replace('|','/').replace('\n',' ')
        if r['timeout']:explanation='执行超时；'+explanation
        lines.append(f"| `{r['component'].removeprefix('Absolut.')}` | [{r['case']}](../{r['log'].replace(chr(92),'/')}) | {r['status']} | {explanation} |")
    lines+=['','## 如何复现','','在 `OpenModelica` 目录执行：','','```powershell','python component_tests.py --jobs 2','python component_tests.py --case FlashingLiBr','```','',
            f"OMEdit 中依次加载 Modelica {report['modelica']}、Buildings 12.0.0、`Absolut/package.mo` 和 `tests/Components.mo`，在 `ComponentTests` 包内选择具体工况并仿真。测试夹具只输出残差，完整的通过/失败判定由 Python 脚本按 `tests/components.json` 中的预设阈值执行。", '',
            '## 判据与局限','',
            '静态设备从连接器的质量流量、实际流向焓和组分计算残差；动态设备将边界通量积分，与实际库存变化比较。压缩机采用绝热焓升功率，泵同时检查液体功率、电功率效率及出口温度。换热器在恒定比热介质下对照解析换热量；基础模块使用解析参考点与热力学恒等式。具体阈值、最大残差、工况参数和警告保存在 JSON。', '',
            '这些是数值与模型一致性测试，不能代替实验验证。覆盖预设正向工况及列出的边界变化，并非穷举全部介质、倒流、失效和参数组合；所有输出量有限也不代表未采样时间处没有问题。', '',
            '组件内部仍须闭合其守恒关系；连接点的守恒方程只约束连接点，不能替代容器内部方程。参见 [Modelica Fluid 组件定义](https://doc.modelica.org/Modelica%204.0.0/Resources/helpDymola/Modelica_Fluid_UsersGuide_ComponentDefinition.html) 和 [Modelica 3.6 方程平衡规范](https://specification.modelica.org/maint/3.6/class-predefined-types-and-declarations.html#balanced-models)。','']
    if report['uncovered_components']:lines+=['本次为筛选运行；尚未执行：'+', '.join(report['uncovered_components']),'']
    out.with_suffix('.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'cases':report['case_summary'],'components':report['component_summary'],'complete_coverage':report['complete_coverage']}),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--omc')
    parser.add_argument('--modelica',choices=('4.0.0','4.1.0'),default='4.0.0')
    parser.add_argument('--buildings',type=Path,default=ROOT.parent/'Buildings 12.0.0/package.mo')
    parser.add_argument('--jobs',type=int,default=2)
    parser.add_argument('--timeout',type=int,default=300)
    parser.add_argument('--case',action='append',help='Exact fixture name, repeatable')
    parser.add_argument('--resume',action='store_true',help='Reuse passing results only if all source, test, runner and compiler hashes match')
    parser.add_argument('--report',help='Defaults to components, or components_selected for a filtered run')
    parser.add_argument('--merge-from',type=Path,help='Retain unchanged cases from a prior report after verifying fixture, criteria and result hashes')
    args=parser.parse_args()
    args.report=args.report or ('components_selected' if args.case else 'components')
    if args.modelica!='4.0.0' and args.report in ('components','components_selected'):
        args.report+='_msl_'+args.modelica.replace('.','_')
    if args.jobs<1 or args.timeout<1:parser.error('jobs and timeout must be positive')
    if Path(args.report).name!=args.report:parser.error('report must be a basename')
    args.omc=verify.find_omc(args.omc)
    manifest=json.loads((ROOT/'tests/components.json').read_text(encoding='utf-8'))
    package=(ROOT/'tests/Components.mo').read_text(encoding='utf-8')
    for case in manifest['cases']:
        spec=hashlib.sha256(json.dumps(case,sort_keys=True).encode()).hexdigest()
        case['case_source_sha256']=fixture_hash(package,case['case'])
        case['case_spec_sha256']=spec
    selected=manifest['cases']
    if args.case:
        missing=set(args.case)-{c['case'] for c in selected}
        if missing:parser.error('Unknown case: '+', '.join(sorted(missing)))
        selected=[c for c in selected if c['case'] in args.case]
    compiler=subprocess.check_output([args.omc,'--version'],text=True).strip()
    source_hash=digest((ROOT/'Absolut').rglob('*.mo'))
    test_hash=digest([ROOT/'tests/Components.mo',ROOT/'tests/components.json',Path(__file__).resolve(),ROOT/'verify.py'])
    key=hashlib.sha256((source_hash+test_hash+compiler+args.modelica+str(args.buildings.resolve())).encode()).hexdigest()
    header=verify.preamble(args.buildings.resolve()).replace('{"4.0.0"}', '{"'+args.modelica+'"}')
    header+=f'if not loadFile({verify.quote(ROOT/"tests/Components.mo")}) then print(getErrorString()); exit(1); end if;\ngetErrorString();\nsetCommandLineOptions("--preOptModules-=evalFunc -d=initialization");\n'
    header+='print("MSL_VERSION=" + getVersion(Modelica) + "\\n");\n'
    report=dict(timestamp_utc=datetime.now(timezone.utc).isoformat(),compiler=compiler,source_sha256=source_hash,test_source_sha256=test_hash,
                modelica=args.modelica,buildings='12.0.0',translation_flags='--preOptModules-=evalFunc -d=initialization',method='dassl',inventory=inventory(),results=[])
    if args.merge_from:
        previous=json.loads(args.merge_from.read_text(encoding='utf-8'))
        if previous['source_sha256']!=source_hash or previous['compiler']!=compiler or previous['modelica']!=args.modelica:
            parser.error('Cannot merge results from a different library source, compiler or Modelica version')
        available={c['case']:c for c in manifest['cases']}
        rerunning={c['case'] for c in selected}
        for result in previous['results']:
            name=result['case']
            if name in rerunning or name not in available:continue
            case=available[name]
            if any(result.get(k)!=case[k] for k in ('case_source_sha256','case_spec_sha256')):
                parser.error('Changed fixture or criteria must be rerun: '+name)
            for field,checksum in result.get('artifact_sha256',{}).items():
                if hashlib.sha256((ROOT/result[field]).read_bytes()).hexdigest()!=checksum:
                    parser.error('Changed evidence artifact: '+name+' '+field)
            if 'log' not in result.get('artifact_sha256',{}):parser.error('Prior report lacks evidence hashes: '+name)
            if 'result' in result:
                result.update(assess_csv(ROOT/result['result'],case))
                if result['successful_simulation']:
                    result['status']='fail' if result['physics_failures'] else 'pass'
                    result['failure_stage']='physics' if result['physics_failures'] else None
                    if case.get('strict_initialization'):
                        result['initialization']=verify.heatport_initialization_check(
                            (ROOT/result['log']).read_text(encoding='utf-8',errors='replace'))
                        if not result['initialization']['pass']:
                            result['status']='fail'
                            result['failure_stage']='initialization'
                    if not result.get('fixture_equation_count_equal',True):
                        result['status']='fail'
                        result['failure_stage']='equation_balance'
            result['reused_unchanged_trajectory']=True
            result['trajectory_test_source_sha256']=previous['test_source_sha256']
            report['results'].append(result)
        report['merge_audit']=dict(previous_report=str(args.merge_from.resolve()),
                                  retained_cases=len(report['results']),
                                  verification='Library/compiler identity, per-model source and criteria identity, log/CSV SHA-256, and renewed assessment of saved trajectories.')
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        pending={pool.submit(run_case,args,c,header,key):c for c in selected}
        for future in concurrent.futures.as_completed(pending):report['results'].append(future.result())
    report['results'].sort(key=lambda r:r['case'])
    if digest((ROOT/'Absolut').rglob('*.mo'))!=source_hash:raise RuntimeError('Library source changed during testing; rerun the suite')
    if digest([ROOT/'tests/Components.mo',ROOT/'tests/components.json',Path(__file__).resolve(),ROOT/'verify.py'])!=test_hash:
        raise RuntimeError('Test source changed during testing; rerun the suite')
    write_report(report,args)
    return int(bool(report['case_summary']['fail']))


if __name__=='__main__':sys.exit(main())
