"""Plot verified AHPse_Dyn_heatport results with explicit units and provenance.

Usage: python plot_heatport.py --modelica 4.1.0
Requires matplotlib and numpy; optionally installed in build/plot_dependencies.
The complete-day trajectory is reused. A matching compiled executable is used
only to obtain a dense 0–1000 s startup trajectory when no verified cache exists.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
LOCAL_PACKAGES = ROOT/'build/plot_dependencies'
if LOCAL_PACKAGES.is_dir():
    sys.path.insert(0, str(LOCAL_PACKAGES))
os.environ.setdefault('MPLCONFIGDIR', str(ROOT/'build/matplotlib_config'))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager, ticker
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import verify

VESSELS = ('eva', 'abs', 'gen', 'con')
NAMES = {'eva': '蒸发器', 'abs': '吸收器', 'gen': '发生器', 'con': '冷凝器'}
COLORS = {'eva': '#157FA4', 'abs': '#D88D22', 'gen': '#BE4D63', 'con': '#398C73'}
STYLES = {'eva': '-', 'abs': '--', 'gen': '-', 'con': '-.'}
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_values(path, required):
    """Preserve saved event rows and time order; do not interpolate or smooth."""
    values = {k: [] for k in ['time', *required]}
    with path.open(encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream)
        missing = set(values)-set(reader.fieldnames)
        if missing:
            raise ValueError('Missing result variables: '+str(sorted(missing)))
        for row in reader:
            for key in values:
                value = float(row[key])
                if not math.isfinite(value):
                    raise ValueError('Nonfinite result: '+key)
                values[key].append(value)
    arrays = {k: np.asarray(v) for k, v in values.items()}
    if not len(arrays['time']) or np.any(np.diff(arrays['time']) < -1e-10):
        raise ValueError('Empty or nonmonotonic result')
    return arrays


def startup_result(build, output, source_digest, required):
    executable = build/('model.exe' if os.name == 'nt' else 'model')
    if not executable.is_file():
        raise RuntimeError('Run tests/initialization.py to build the selected MSL version first.')
    if executable.stat().st_mtime < max(p.stat().st_mtime for p in (ROOT/'Absolut').rglob('*.mo')):
        raise RuntimeError('Compiled model predates the library. Rebuild with tests/initialization.py.')
    result_path = output/'data/startup_1000s.csv'
    log_path = output/'data/startup_1000s.log'
    record_path = output/'data/startup_run.json'
    if record_path.is_file() and result_path.is_file() and log_path.is_file():
        previous = json.loads(record_path.read_text(encoding='utf-8'))
        if (previous['source_sha256'] == source_digest and previous['executable_sha256'] == sha(executable)
                and previous['csv_sha256'] == sha(result_path) and previous['log_sha256'] == sha(log_path)
                and previous['pass']):
            return result_path, previous
    import re
    variables = list(required)+[f'der(ahp.{v}.U)' for v in VESSELS]
    variables += ['ahp.abs.mXLiBr[1]', 'ahp.gen.mXLiBr[1]', 'ahp.pump_abstogen.W_p',
                  'ahp.flashingLiBr.port_a.m_flow', 'ahp.flashingLiBr.port_l_b.m_flow',
                  'ahp.flashingLiBr.X_LiBr_in', 'ahp.flashingLiBr.X_LiBr_out']
    pattern = '^('+'|'.join(re.escape(v) for v in sorted(set(variables)))+')$'
    omc_home = Path(verify.find_omc(None)).parent.parent
    environment = os.environ.copy()
    environment['PATH'] = str(omc_home/'bin')+os.pathsep+str(omc_home/'tools/msys/mingw64/bin')+os.pathsep+environment['PATH']
    command = [str(executable), '-startTime=0', '-stopTime=1000', '-stepSize=0.1',
               '-tolerance=1e-7', '-s=dassl', '-outputFormat=csv', '-r='+str(result_path),
               '-variableFilter='+pattern, '-lv=LOG_STDOUT,LOG_ASSERT,LOG_STATS,LOG_SUCCESS']
    result_path.parent.mkdir(parents=True, exist_ok=True)
    if result_path.is_file():
        result_path.unlink()
    print('Preparing dense startup trajectory...', flush=True)
    with log_path.open('w', encoding='utf-8') as stream:
        process = subprocess.run(command, cwd=build, env=environment,
                                 stdout=stream, stderr=subprocess.STDOUT, timeout=180)
    log = log_path.read_text(encoding='utf-8')
    values = load_values(result_path, required)
    conservation = verify.heatport_conservation(result_path)
    init = verify.heatport_initialization_check(log)
    success = (process.returncode == 0 and 'simulation finished successfully' in log
               and values['time'][-1] == 1000 and conservation['pass'] and init['pass'])
    record = {'pass': success, 'command': command, 'source_sha256': source_digest,
              'executable_sha256': sha(executable), 'csv_sha256': sha(result_path),
              'log_sha256': sha(log_path), 'returncode': process.returncode,
              'rows': len(values['time']), 'final_time_s': float(values['time'][-1]),
              'conservation': conservation, 'initialization': init}
    record_path.write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    if not success:
        raise RuntimeError('Startup verification failed; see '+str(log_path))
    print('Startup trajectory completed and passed conservation checks.', flush=True)
    return result_path, record


def configure_style():
    for font_path in (Path('C:/Windows/Fonts/msyh.ttc'), Path('C:/Windows/Fonts/msyhbd.ttc')):
        if font_path.is_file():
            font_manager.fontManager.addfont(str(font_path))
    plt.rcParams.update({
        'font.family': ['Microsoft YaHei', 'DejaVu Sans'], 'font.size': 11,
        'axes.unicode_minus': False, 'axes.titleweight': 'bold',
        'axes.titlesize': 13, 'axes.labelsize': 10.5, 'axes.labelcolor': '#334155',
        'text.color': '#172B44', 'xtick.color': '#526174', 'ytick.color': '#526174',
        'xtick.labelsize': 9.5, 'ytick.labelsize': 9.5,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.edgecolor': '#BCC8D5', 'grid.color': '#DFE6EF', 'grid.linewidth': .65,
        'figure.facecolor': 'white', 'axes.facecolor': 'white',
        'legend.frameon': False, 'legend.fontsize': 9.5, 'legend.handlelength': 2.3,
        'svg.fonttype': 'path', 'pdf.fonttype': 42,
    })


def make_figure(values, version, stage):
    startup = stage == 'startup'
    selected = values['time'] <= 1000 if startup else values['time'] >= 1000
    x = values['time'][selected] / (1 if startup else 3600)
    if len(x) < 10:
        raise ValueError('Insufficient plotted samples')
    fig, axes = plt.subplots(3, 2, figsize=(15, 13), dpi=170)
    fig.subplots_adjust(left=.080, right=.975, bottom=.090, top=.815, wspace=.23, hspace=.57)
    fig.text(.080, .962, 'ABSOLUT  /  动态吸收式热泵', fontsize=10.5, color='#5A7086')
    fig.text(.080, .921, 'AHPse_Dyn_heatport', fontsize=26, weight='bold')
    title = '启动过程 · 0–1000 s' if startup else '24 小时运行 · 1000 s 之后的趋势'
    fig.text(.080, .886, f'{title}   |   Modelica {version} · DASSL · 容差 1e-7', fontsize=11.5, color='#526174')

    def line(ax, vessel, field, scale=1, offset=0, external=False):
        key = f'temperature_{vessel}_out.T' if external else f'ahp.{vessel}.{field}'
        y = values[key][selected]*scale+offset
        ax.plot(x, y, label=NAMES[vessel], color=COLORS[vessel],
                linestyle=STYLES[vessel], linewidth=1.65)

    def decorate(ax, title, unit, count=4):
        ax.set_title(title, loc='left', pad=36)
        ax.set_ylabel(unit)
        ax.set_xlabel('时间 / s' if startup else '时间 / h', labelpad=6)
        ax.grid(True, which='major')
        ax.set_axisbelow(True)
        ax.yaxis.set_major_locator(ticker.MaxNLocator(nbins=5, min_n_ticks=3))
        ax.yaxis.set_major_formatter(ticker.ScalarFormatter(useOffset=False))
        ax.ticklabel_format(axis='y', style='plain', useOffset=False)
        if startup:
            ax.set_xlim(0, 1000)
            ax.set_xticks(np.arange(0, 1001, 200))
        else:
            ax.set_xlim(1000/3600, 24)
            ax.set_xticks([1, 4, 8, 12, 16, 20, 24])
        ax.legend(loc='lower left', bbox_to_anchor=(0, 1.01), ncol=count,
                  borderaxespad=0, columnspacing=1.2)

    for v in VESSELS:
        line(axes[0, 0], v, 'T', offset=-273.15)
        line(axes[0, 1], v, 'Qb_flow', scale=.001)
        line(axes[1, 1], v, 'level', scale=1000)
        line(axes[2, 1], v, 'T', offset=-273.15, external=True)
    decorate(axes[0, 0], '01  容器温度', '温度 / ℃')
    axes[0, 1].axhline(0, color='#8C9CAF', lw=.8)
    decorate(axes[0, 1], '02  各容器热流 · 流入工质为正', '热流 / kW')
    for a, b in [('gen', 'con'), ('eva', 'abs')]:
        if np.max(np.abs(values[f'ahp.{a}.p']-values[f'ahp.{b}.p'])) > 1e-7:
            raise ValueError('Pressure pairing is not valid for this run')
    axes[1, 0].plot(x, values['ahp.gen.p'][selected]/1000, color=COLORS['gen'],
                    label='高压侧（发生器 / 冷凝器）', lw=1.8)
    axes[1, 0].plot(x, values['ahp.eva.p'][selected]/1000, color=COLORS['eva'],
                    label='低压侧（蒸发器 / 吸收器）', lw=1.8)
    decorate(axes[1, 0], '03  循环压力', '绝对压力 / kPa', count=2)
    decorate(axes[1, 1], '04  容器液位', '液位 / mm')
    for v in ('abs', 'gen'):
        line(axes[2, 0], v, 'X_LiBr', scale=100)
    decorate(axes[2, 0], '05  溴化锂浓度', 'LiBr 质量分数 / %', count=2)
    decorate(axes[2, 1], '06  外部水出口温度', '温度 / ℃')
    caption = ('启动段单独运行，输出间隔 0.1 s；保留事件点，未经平滑。' if startup else
               '图示采用全天运行中 t ≥ 1000 s 的原始保存点；前 1000 s 的启动峰值见另一张图。')
    fig.text(.080, .037, caption, fontsize=9.3, color='#63758B')
    fig.text(.080, .017, '默认参数工况 · 已通过数值与守恒检查 · 仿真结果', fontsize=9.3, color='#63758B')
    return fig, {'rows_plotted': int(np.sum(selected)),
                 'first_saved_time_s': float(values['time'][selected][0]),
                 'last_saved_time_s': float(values['time'][selected][-1])}


def scaled_export(values, path):
    columns = {'time_s': values['time'], 'time_h': values['time']/3600}
    for v in VESSELS:
        columns[f'{v}_temperature_C'] = values[f'ahp.{v}.T']-273.15
        columns[f'{v}_pressure_kPa'] = values[f'ahp.{v}.p']/1000
        columns[f'{v}_heat_into_fluid_kW'] = values[f'ahp.{v}.Qb_flow']/1000
        columns[f'{v}_level_mm'] = values[f'ahp.{v}.level']*1000
        columns[f'{v}_external_water_outlet_C'] = values[f'temperature_{v}_out.T']-273.15
    for v in ('abs', 'gen'):
        columns[f'{v}_LiBr_mass_percent'] = values[f'ahp.{v}.X_LiBr']*100
    with path.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows(zip(*columns.values()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--modelica', choices=('4.0.0', '4.1.0'), default='4.1.0')
    args = parser.parse_args()
    report_path = ROOT/'reports/initialization.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    case = next(r for r in report['results'] if r['modelica'] == args.modelica and r['model'] == verify.HEATPORT_CASE)
    current_digest = hashlib.sha256(b''.join(p.relative_to(ROOT).as_posix().encode()+b'\0'+p.read_bytes()
        for p in sorted((ROOT/'Absolut').rglob('*.mo')))).hexdigest()
    assert current_digest == report['source_sha256'], 'Library changed since the verified run'
    assert case['pass'] and case['conservation']['pass']
    day_path = ROOT/case['result']
    assert sha(day_path) == case['artifact_sha256']['result'], 'Changed day result CSV'
    output = ROOT/'reports/plots/AHPse_Dyn_heatport'/('MSL_'+args.modelica)
    output.mkdir(parents=True, exist_ok=True)
    required = [f'ahp.{v}.{field}' for v in VESSELS for field in ('T', 'p', 'level', 'Qb_flow', 'm', 'U')]
    required += ['ahp.abs.X_LiBr', 'ahp.gen.X_LiBr']+[f'temperature_{v}_out.T' for v in VESSELS]
    day = load_values(day_path, required)
    assert day['time'][0] == 0 and day['time'][-1] == 86400
    startup_path, startup_record = startup_result(day_path.parent, output, current_digest, required)
    startup = load_values(startup_path, required)
    day_copy = output/'data/full_day_86400s.csv'
    shutil.copy2(day_path, day_copy)
    assert sha(day_copy) == sha(day_path)
    configure_style()
    manifest = {'model': verify.HEATPORT_CASE, 'modelica': args.modelica,
                'created_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': current_digest,
                'matplotlib': matplotlib.__version__, 'numpy': np.__version__,
                'plot_script_sha256': sha(Path(__file__)),
                'full_day_csv': str(day_path.relative_to(ROOT)), 'full_day_csv_sha256': sha(day_path),
                'full_day_csv_copy': day_copy.relative_to(output).as_posix(),
                'startup_csv': startup_path.relative_to(output).as_posix(),
                'day_conservation': case['conservation'], 'startup_run': startup_record,
                'figures': {}, 'conventions': {'temperature': 'K - 273.15 -> degC', 'pressure': 'Pa / 1000 -> kPa',
                    'heat': 'Qb_flow / 1000 -> kW, positive into working fluid',
                    'level': 'm * 1000 -> mm', 'LiBr': 'mass fraction * 100 -> percent',
                    'sampling': 'Original saved values including events. Separate startup and full-day runs; no trajectory concatenation or smoothing.'}}
    summary = {NAMES[v]: {'temperature_C': float(day[f'ahp.{v}.T'][-1]-273.15),
                'pressure_kPa': float(day[f'ahp.{v}.p'][-1]/1000),
                'heat_into_fluid_kW': float(day[f'ahp.{v}.Qb_flow'][-1]/1000),
                'level_mm': float(day[f'ahp.{v}.level'][-1]*1000)} for v in VESSELS}
    ratio = float(day['ahp.eva.Qb_flow'][-1]/day['ahp.gen.Qb_flow'][-1])
    manifest['final_86400s'] = summary
    manifest['final_heat_ratio_Qeva_Qgen'] = ratio
    pdf_path = output/'AHPse_Dyn_heatport_results.pdf'
    with PdfPages(pdf_path, metadata={'Title': 'AHPse_Dyn_heatport results', 'Author': 'Absolut OpenModelica verification'}) as pdf:
        for stage, values in [('day', day), ('startup', startup)]:
            fig, info = make_figure(values, args.modelica, stage)
            stem = 'AHPse_Dyn_heatport_'+('24h_trends' if stage == 'day' else 'startup_1000s')
            for extension in ('png', 'svg'):
                path = output/(stem+'.'+extension)
                fig.savefig(path, dpi=180, facecolor='white')
                info[extension] = path.name
            pdf.savefig(fig, facecolor='white')
            manifest['figures'][stage] = info
            plt.close(fig)
    for name, values in [('day', day), ('startup', startup)]:
        scaled_export(values, output/('data/'+name+'_plot_units.csv'))
    (output/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    lines = ['# AHPse_Dyn_heatport 结果绘图', '',
             f'Modelica {args.modelica}，Buildings 12.0.0，默认案例参数，DASSL，容差 1e-7。', '',
             '采用本地已验证的完整案例数据。全天运行达到 86400 s；启动过程另用同版本可执行程序运行 0–1000 s，输出间隔 0.1 s。两次均检查成功结束、有限数值和工作流体守恒。', '',
             '## 图片', '',
             '- [24 小时运行趋势](AHPse_Dyn_heatport_24h_trends.png)：展示全天运行中 1000 s 之后的保存点，横轴为小时。',
             '- [前 1000 秒启动过程](AHPse_Dyn_heatport_startup_1000s.png)：横轴为秒，保留初始热流峰值。',
             '- [双页 PDF](AHPse_Dyn_heatport_results.pdf)：含上述两张图；同名 SVG 为矢量图。', '',
             '## 86400 s 终点数值', '', '| 容器 | 温度 / ℃ | 压力 / kPa | 热流 / kW | 液位 / mm |',
             '| --- | ---: | ---: | ---: | ---: |']
    for name, row in summary.items():
        lines.append(f"| {name} | {row['temperature_C']:.4f} | {row['pressure_kPa']:.5f} | {row['heat_into_fluid_kW']:.4f} | {row['level_mm']:.4f} |")
    lines += ['', f'终点热量比 Qeva/Qgen = {ratio:.6f}，该比值未计入泵功。', '',
              '热流保留原符号：正值流入工质，负值流出工质；启动阶段可能改变方向。压力为绝对压力；浓度为 LiBr 质量百分数。', '',
              '图中没有插值补点、拼接不同运行轨迹或平滑处理。图片中的折线只连接原始保存点；全天运行设置 500 个输出间隔，并保留事件点。', '',
              '当前结果仍可能有被恢复的非线性迭代警告。通过数值与守恒检查不等于实验验证，也不代表与 Dymola 逐点等价。', '',
              '原始 CSV 路径、文件校验值、转换规则、启动运行命令及守恒残差见 [manifest.json](manifest.json)。data 目录含全天和启动原始数据，以及两组换算单位后的绘图数据。', '',
              f'源码 SHA-256：`{current_digest}`。', '',
              '重现命令（从 OpenModelica 目录执行，需要 matplotlib、numpy）：', '',
              '```powershell', f'python .\\plot_heatport.py --modelica {args.modelica}', '```', '']
    (output/'README_zh.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'output': str(output), 'final_86400s': summary, 'heat_ratio': ratio}, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
