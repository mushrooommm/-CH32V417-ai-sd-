#!/usr/bin/env python3
"""
XENON 睡眠监测 — SD 卡日志分析报告（snore.py）

从 SNORE.CSV 生成 4 张对比图 + 约 150 字专业健康建议。

用法（演示电脑）:
  pip install matplotlib
  python snore.py --input E:\\SNORE.CSV --out-dir report

用法（工程 demo 目录）:
  python snore.py --input SNORE.CSV --out-dir report
"""

from __future__ import annotations

import argparse
import csv
import re
import time
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
from matplotlib import font_manager

LINE_PATTERN = re.compile(r"STAT,[^\r\n]*")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Snore monitor visual report")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", type=Path, help="SNORE.CSV from SD card or demo folder")
    src.add_argument("--stats", type=Path, help="stats.csv from sd_log_analyzer.py")
    p.add_argument(
        "--out-dir",
        type=Path,
        default=Path("report"),
        help="Output folder for PNG + health_advice.txt",
    )
    return p.parse_args()


def setup_chinese_font() -> None:
    candidates = ["Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans CJK SC", "Arial Unicode MS"]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
            break
    plt.rcParams["axes.unicode_minus"] = False


def parse_kv_line(line: str) -> Dict[str, str]:
    kv: Dict[str, str] = {}
    for token in line.split(",")[1:]:
        if "=" in token:
            k, v = token.split("=", 1)
            kv[k.strip()] = v.strip()
    return kv


def load_from_snore_csv(path: Path) -> List[Dict[str, str]]:
    text = path.read_bytes().decode("latin-1", errors="ignore")
    rows: List[Dict[str, str]] = []
    for m in LINE_PATTERN.finditer(text):
        rows.append(parse_kv_line(m.group(0)))
    return rows


def load_from_stats_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fp:
        return list(csv.DictReader(fp))


def to_int(v: str, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def add_interval_deltas(rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    prev_open = prev_closed = prev_noise = 0
    for r in rows:
        ts = to_int(r.get("ts", "0"))
        open_c = to_int(r.get("open", "0"))
        closed_c = to_int(r.get("closed", "0"))
        noise = to_int(r.get("noise_frames", "0"))
        d_open = max(0, open_c - prev_open)
        d_closed = max(0, closed_c - prev_closed)
        d_noise = max(0, noise - prev_noise)
        out.append(
            {
                "ts": ts,
                "open": open_c,
                "closed": closed_c,
                "noise_frames": noise,
                "risk": to_int(r.get("risk", "0")),
                "rate_x10": to_int(r.get("rate_x10", "0")),
                "stability_x100": to_int(r.get("stability_x100", "0")),
                "last_cls": r.get("last_cls", ""),
                "d_open": d_open,
                "d_closed": d_closed,
                "d_noise": d_noise,
            }
        )
        prev_open, prev_closed, prev_noise = open_c, closed_c, noise
    return out


def minutes_label(ts_s: int) -> str:
    return f"{ts_s // 60:02d}:{ts_s % 60:02d}"


def plot_pie(data: List[Dict[str, object]], out_path: Path) -> None:
    """按每 5 秒时段的 last_cls 统计占比，避免用 noise_frames 帧数导致噪声虚高。"""
    n_noise = n_open = n_closed = 0
    for d in data:
        lc = str(d.get("last_cls", "")).upper()
        if lc == "SNORE_OPEN":
            n_open += 1
        elif lc == "SNORE_CLOSED":
            n_closed += 1
        else:
            n_noise += 1
    if n_noise + n_open + n_closed == 0:
        n_noise = 1

    labels = ["环境噪声", "张嘴打齁", "闭嘴打齁"]
    sizes = [n_noise, n_open, n_closed]
    colors = ["#5B9BD5", "#ED7D31", "#70AD47"]
    explode = (0.03, 0.06, 0.06)

    fig, ax = plt.subplots(figsize=(8, 7), dpi=120)
    _, _, autotexts = ax.pie(
        sizes,
        labels=labels,
        autopct=lambda p: f"{p:.1f}%" if p > 0 else "",
        startangle=90,
        colors=colors,
        explode=explode,
        pctdistance=0.78,
        labeldistance=1.08,
        textprops={"fontsize": 12},
    )
    for t in autotexts:
        t.set_fontsize(11)
        t.set_fontweight("bold")
    ax.set_title("睡眠声学事件占比\n（按监测时段分布）", fontsize=14, fontweight="bold", pad=16)
    legend = [f"{l}: {v}段" for l, v in zip(labels, sizes)]
    ax.legend(legend, loc="lower center", bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=10)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def plot_peak_line(
    data: List[Dict[str, object]], key: str, title: str, color: str, out_path: Path
) -> None:
    ts = [int(d["ts"]) for d in data]
    y = [int(d[key]) for d in data]
    x_labels = [minutes_label(t) for t in ts]

    fig, ax = plt.subplots(figsize=(10, 5), dpi=120)
    ax.fill_between(range(len(ts)), y, alpha=0.35, color=color)
    ax.plot(range(len(ts)), y, color=color, linewidth=2.2, marker="o", markersize=4)
    ax.set_xticks(range(0, len(ts), max(1, len(ts) // 12)))
    ax.set_xticklabels([x_labels[i] for i in range(0, len(ts), max(1, len(ts) // 12))], rotation=45, ha="right")
    ax.set_xlabel("监测时间 (分:秒)")
    ax.set_ylabel("本时段新增次数")
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.45)
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def plot_open_closed_bars(data: List[Dict[str, object]], out_path: Path) -> None:
    ts = [int(d["ts"]) for d in data]
    d_open = [int(d["d_open"]) for d in data]
    d_closed = [int(d["d_closed"]) for d in data]
    x_labels = [minutes_label(t) for t in ts]
    x = range(len(ts))
    width = 0.38
    step = max(1, len(ts) // 20)

    fig, ax = plt.subplots(figsize=(12, 5.5), dpi=120)
    ax.bar([i - width / 2 for i in x], d_open, width, label="张嘴打齁", color="#ED7D31")
    ax.bar([i + width / 2 for i in x], d_closed, width, label="闭嘴打齁", color="#70AD47")
    ax.set_xticks(list(range(0, len(ts), step)))
    ax.set_xticklabels([x_labels[i] for i in range(0, len(ts), step)], rotation=45, ha="right")
    ax.set_xlabel("监测时间 (分:秒)")
    ax.set_ylabel("本时段新增次数")
    ax.set_title("张嘴 vs 闭嘴打齁 时段分布对比", fontsize=13, fontweight="bold")
    ax.legend(loc="upper left")
    ax.grid(True, axis="y", linestyle="--", alpha=0.45)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def build_health_advice(data: List[Dict[str, object]]) -> str:
    if not data:
        return "未检测到有效 STAT 数据，无法生成健康建议。"

    last = data[-1]
    risk = int(last["risk"])
    stab = int(last["stability_x100"]) / 100.0
    total_open = int(last["open"])
    total_closed = int(last["closed"])
    open_dominant = total_open >= total_closed

    if risk >= 65:
        risk_para = (
            "本次声学监测提示夜间上气道在睡眠中反复出现狭窄与软组织振动，"
            "呼吸负荷与微觉醒风险处于需重视区间，与阻塞性睡眠呼吸暂停（OSA）相关的早期信号较为明显。"
        )
        care_para = (
            "建议限期至睡眠医学专科就诊，完善病史询问与必要时多导睡眠监测（PSG）；"
            "在此之前请戒烟限酒、避免睡前镇静药物，尽量侧卧并将头胸部略抬高，控制体重并保持规律作息。"
        )
    elif risk >= 35:
        risk_para = (
            "监测显示睡眠期上气道稳定性欠佳，鼾声与气流紊乱交替出现，"
            "存在一定进展为睡眠呼吸紊乱的可能，宜持续观察而非忽视。"
        )
        care_para = (
            "建议连续家庭声学监测三至七个夜晚，记录体位与饮酒等诱因；"
            "坚持侧卧、减轻体重、改善鼻腔通气，若趋势升高应预约睡眠专科随访。"
        )
    else:
        risk_para = (
            "当前声学负担总体可控，未见显著高危模式，但仍需结合主观睡眠质量和日间功能综合判断。"
        )
        care_para = (
            "建议维持规律作息与体重管理，避免仰卧与睡前饮酒，可继续周期性家庭监测以建立个人基线。"
        )

    if open_dominant:
        morph_para = (
            "声学特征以张口型通气为主，提示口咽及软腭区域在入睡后松弛下垂，"
            "气流通过时易产生涡流与宽频振动；可尝试口腔颌位训练、加强口咽肌锻炼，睡眠时优先侧卧。"
        )
    else:
        morph_para = (
            "声学特征以闭口型鼾声为主，提示鼻后及软腭区域阻力可能升高；"
            "可关注过敏性鼻炎、鼻中隔偏曲等鼻部问题，保持卧室适当湿度并避免干燥。"
        )

    if stab < 15:
        stab_para = "鼾声事件间隔波动较大，提示睡眠片段化或浅睡眠成分可能增多，恢复性睡眠或受影响。"
    elif stab < 25:
        stab_para = "呼吸事件节律稳定性一般，提示夜间可能存在轻度睡眠结构干扰。"
    else:
        stab_para = "事件节律相对稳定，但仍需结合整夜趋势判断是否具有临床意义。"

    warning = (
        "若合并日间不可恢复性嗜睡、晨起头痛口干、记忆力下降、目击呼吸暂停或夜间憋醒，"
        "请尽快就医，勿自行延误评估。"
    )
    disclaimer = (
        "本报告由家庭声学监测设备生成，仅作健康管理与趋势参考，不能替代医师面诊与临床诊断。"
    )

    return f"【睡眠声学监测意见】{risk_para}{morph_para}{stab_para}{care_para}{warning}{disclaimer}"


def write_advice_txt(text: str, out_path: Path) -> None:
    out_path.write_text(text + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    setup_chinese_font()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("正在读取 SD 卡日志…")
    time.sleep(1.2)

    if args.input:
        if not args.input.exists():
            raise FileNotFoundError(args.input)
        rows = load_from_snore_csv(args.input)
        print(f"  输入: {args.input.resolve()}")
    else:
        if not args.stats.exists():
            raise FileNotFoundError(args.stats)
        rows = load_from_stats_csv(args.stats)
        print(f"  输入: {args.stats.resolve()}")

    if not rows:
        raise RuntimeError("No STAT rows found in input.")

    print(f"  共 {len(rows)} 条 STAT 记录")
    time.sleep(0.8)
    print("正在生成图表与健康建议…")
    time.sleep(0.6)

    data = add_interval_deltas(rows)

    print("  [1/4] 声学事件占比饼图")
    plot_pie(data, args.out_dir / "01_pie_noise_open_closed.png")
    time.sleep(0.4)
    print("  [2/4] 张嘴打齁趋势")
    plot_peak_line(
        data, "d_open", "张嘴打齁 变化趋势（时段增量）", "#ED7D31", args.out_dir / "02_line_open_snore.png"
    )
    time.sleep(0.4)
    print("  [3/4] 闭嘴打齁趋势")
    plot_peak_line(
        data, "d_closed", "闭嘴打齁 变化趋势（时段增量）", "#70AD47", args.out_dir / "03_line_closed_snore.png"
    )
    time.sleep(0.4)
    print("  [4/4] 张嘴 vs 闭嘴对比")
    plot_open_closed_bars(data, args.out_dir / "04_bar_open_vs_closed.png")

    advice = build_health_advice(data)
    write_advice_txt(advice, args.out_dir / "health_advice.txt")

    print(f"Report folder: {args.out_dir.resolve()}")
    print("  01_pie_noise_open_closed.png")
    print("  02_line_open_snore.png")
    print("  03_line_closed_snore.png")
    print("  04_bar_open_vs_closed.png")
    print("  health_advice.txt")
    print(f"Advice length: {len(advice)} chars")


if __name__ == "__main__":
    main()
