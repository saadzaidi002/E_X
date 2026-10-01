import io
import os
import tempfile
os.environ['MPLCONFIGDIR'] = tempfile.mkdtemp()
import time
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors as rl_colors

# ----------------- Helper Functions -----------------

RAW_METHOD = "Raw (Baseline)"

def format_short_name(name):
    # Method names use an en dash ("Goldreich\u2013Levin"); normalise it so the
    # abbreviations below match and chart fonts without that glyph still render.
    name = name.replace("\u2013", "-")
    short = name.split(". ", 1)[-1] if ". " in name else name
    for word in ["Extractor", "Extraction", "Method", "Hash", "Matrix"]:
        short = short.replace(word, "").replace(word.lower(), "").strip()
    if "Leftover Hash Lemma" in name: return "LHL"
    if "Quantum-Proof Strong" in name: return "Quantum"
    if "Goldreich-Levin" in name: return "Goldreich-L."
    if "Chor-Goldreich" in name: return "Chor-G."
    if "Juels-Wattenberg" in name: return "Juels-W."
    if "Hadamard" in name: return "Hadamard"
    if "Modular Arithmetic" in name: return "Modular"
    if "Toeplitz" in name: return "Toeplitz"
    if "Elias" in name: return "Elias"
    if "Bit-Shuffling" in name: return "Bit-Shuffle"
    if "Von Neumann" in name: return "Von Neumann"
    if "Arithmetic Coding" in name: return "Arithmetic"
    if "LFSR-Based" in name: return "LFSR"
    if "XOR-Summation" in name: return "XOR-Sum"
    if "Raw (Baseline)" in name: return "Raw"
    if len(short) > 12: return short[:10] + "..."
    return short

def setup_matplotlib():
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
    plt.rcParams['axes.spines.top'] = False
    plt.rcParams['axes.spines.right'] = False

def format_table_name(name):
    """Method name for the rankings table: no number prefix, no generic suffix."""
    name = name.split(". ", 1)[-1] if ". " in name else name
    for suffix in (" Extractor", " Method"):
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    return name

def without_raw(data_points):
    """The raw baseline is not extracted, so it has no speed or run time to chart."""
    return [d for d in data_points if d['method'] != RAW_METHOD]

def row_height(n):
    """Figure height (inches) for a horizontal bar chart with n rows."""
    return max(3.0, n * 0.27 + 0.9)

def save_plot():
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=200)
    buf.seek(0)
    plt.close()
    return buf

def chart_image(buf, width=500, max_height=440):
    """Flowable that keeps the chart's own aspect ratio (a fixed box squashes it)."""
    from reportlab.lib.utils import ImageReader
    buf.seek(0)
    px_w, px_h = ImageReader(buf).getSize()
    buf.seek(0)
    height = width * px_h / px_w
    if height > max_height:
        width, height = width * max_height / height, max_height
    return Image(buf, width=width, height=height)

# Colors
COLOR_PRIMARY = '#0077B6'
COLOR_SECONDARY = '#00B4D8'
COLOR_ACCENT = '#9B59B6'
COLOR_PASS = '#0077B6'
COLOR_FAIL = '#C0392B'
COLOR_INVALID = '#95A5A6'
COLOR_WARN = '#F39C12'
COLOR_EXCELLENT = '#27AE60'

# ----------------- Chart Generators -----------------

def generate_entropy_chart(data_points):
    setup_matplotlib()
    # Remove sorting to match web exactly
    sorted_data = data_points
    names = [format_short_name(d['method']) for d in sorted_data]
    shannons = [d['shannon'] for d in sorted_data]
    mins = [d['minEntropy'] for d in sorted_data]

    fig, ax = plt.subplots(figsize=(9, 5.2))
    x = range(len(names))
    width = 0.35

    ax.bar([pos - width/2 for pos in x], shannons, width, label='Shannon Entropy', color=COLOR_SECONDARY)
    ax.bar([pos + width/2 for pos in x], mins, width, label='Min-Entropy', color=COLOR_PRIMARY)

    ax.axhline(y=1.0, color='#333333', linestyle='--', linewidth=1.5, alpha=0.5)
    ax.text(len(names)-1, 1.01, 'Ideal (1.0)', ha='right', va='bottom', fontsize=10, fontweight='bold', color='#333333')

    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=45, ha='right', fontsize=10)
    ax.set_ylim(0, 1.1)
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.25), ncol=2, frameon=False, fontsize=10)
    ax.set_title("Entropy Comparison (Higher is Better)", fontsize=12, fontweight='bold', pad=15)

    # Value labels only if <= 10 methods so it's not overcrowded, else no labels for entropy
    if len(names) <= 10:
        for i, (s, m) in enumerate(zip(shannons, mins)):
            ax.text(i - width/2, s + 0.002, f"{s:.3f}", ha='center', va='bottom', fontsize=7, rotation=90)
            ax.text(i + width/2, m + 0.002, f"{m:.3f}", ha='center', va='bottom', fontsize=7, rotation=90)

    return save_plot()

def generate_nist_chart(data_points):
    setup_matplotlib()
    sorted_data = sorted(data_points, key=lambda d: d['pass'], reverse=False)
    names = [format_short_name(d['method']) for d in sorted_data]
    passes = [d['pass'] for d in sorted_data]
    fails = [d['fail'] for d in sorted_data]
    invalids = [d['invalid'] for d in sorted_data]

    fig, ax = plt.subplots(figsize=(9, row_height(len(names))))
    y = range(len(names))

    ax.barh(y, passes, color=COLOR_PASS, label='Pass')
    ax.barh(y, fails, left=passes, color=COLOR_FAIL, label='Fail')
    ax.barh(y, invalids, left=[p+f for p,f in zip(passes, fails)], color=COLOR_INVALID, label='Insufficient data')

    for i, p in enumerate(passes):
        if p > 0: ax.text(p/2, i, str(p), ha='center', va='center', color='white', fontweight='bold', fontsize=9)

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=10)
    ax.set_xlim(0, 16)
    ax.grid(axis='x', linestyle='--', alpha=0.3)
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.02), ncol=3, frameon=False, fontsize=10)
    ax.set_title("NIST SP 800-22 Test Pass Rate", fontsize=12, fontweight='bold', pad=30)

    return save_plot()

def generate_throughput_chart(data_points):
    setup_matplotlib()
    sorted_data = sorted(without_raw(data_points), key=lambda d: d['bitRate'], reverse=False)
    names = [format_short_name(d['method']) for d in sorted_data]
    rates = [d['bitRate'] for d in sorted_data]

    fig, ax = plt.subplots(figsize=(9, row_height(len(names))))
    y = range(len(names))
    bars = ax.barh(y, rates, color=COLOR_SECONDARY)

    for i, (bar, rate) in enumerate(zip(bars, rates)):
        label = f"{rate/1e6:.2f} Mbps" if rate >= 1e6 else (f"{rate/1e3:.1f} kbps" if rate >= 1000 else f"{int(rate)} bps")
        ax.text(rate + max(rates)*0.01, i, label, va='center', fontsize=9, fontweight='bold', color='#333333')

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=10)
    ax.set_xlim(0, max(rates) * 1.16 if rates and max(rates) > 0 else 1)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v/1e6:g}"))
    ax.set_xlabel("Megabits per second", fontsize=10)
    ax.grid(axis='x', linestyle='--', alpha=0.3)
    ax.set_title("Throughput (Higher is Better)", fontsize=12, fontweight='bold', pad=15)

    return save_plot()

def generate_efficiency_chart(data_points):
    setup_matplotlib()
    # Handle cases where time is 0 due to fast execution
    data_points = without_raw(data_points)
    for d in data_points:
        d['exec_ms'] = max(d.get('executionTime', 0.1), 0.1)

    sorted_data = sorted(data_points, key=lambda d: d['exec_ms'], reverse=True)
    names = [format_short_name(d['method']) for d in sorted_data]
    times = [d['exec_ms'] for d in sorted_data]

    fig, ax = plt.subplots(figsize=(9, row_height(len(names))))
    y = range(len(names))
    bars = ax.barh(y, times, color=COLOR_ACCENT)

    for i, (bar, t) in enumerate(zip(bars, times)):
        label = f"{t:.1f} ms" if t < 1 else f"{int(t)} ms"
        ax.text(t + max(times)*0.01, i, label, va='center', fontsize=9, fontweight='bold', color='#333333')

    ax.set_xlim(0, max(times) * 1.12 if times else 1)
    ax.set_xlabel("Milliseconds", fontsize=10)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=10)
    ax.grid(axis='x', linestyle='--', alpha=0.3)
    ax.set_title("Computational Efficiency (Execution Time, Lower is Better)", fontsize=12, fontweight='bold', pad=15)

    return save_plot()

def generate_bias_chart(data_points):
    setup_matplotlib()
    sorted_data = sorted(data_points, key=lambda d: d['bias'], reverse=True)
    names = [format_short_name(d['method']) for d in sorted_data]
    biases = [d['bias'] for d in sorted_data]

    fig, ax = plt.subplots(figsize=(9, row_height(len(names))))
    y = range(len(names))

    colors = [COLOR_EXCELLENT if b < 0.01 else (COLOR_WARN if b < 0.05 else COLOR_FAIL) for b in biases]
    bars = ax.barh(y, biases, color=colors)

    for i, (bar, b) in enumerate(zip(bars, biases)):
        ax.text(b + max(biases)*0.01, i, f"{b:.5f}", va='center', fontsize=9, fontweight='bold', color='#333333')

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=10)
    ax.set_xlim(0, max(biases) * 1.14 if biases and max(biases) > 0 else 1)
    ax.grid(axis='x', linestyle='--', alpha=0.3)
    ax.set_title("Bias Level (Lower is Better)", fontsize=12, fontweight='bold', pad=15)

    legend_elements = [
        mpatches.Patch(color=COLOR_EXCELLENT, label='Excellent (< 0.01)'),
        mpatches.Patch(color=COLOR_WARN, label='Moderate (< 0.05)'),
        mpatches.Patch(color=COLOR_FAIL, label='High (>= 0.05)')
    ]
    ax.legend(handles=legend_elements, loc='lower center', bbox_to_anchor=(0.5, -0.2), ncol=3, frameon=False, fontsize=10)

    return save_plot()

def generate_compression_chart(data_points):
    setup_matplotlib()
    sorted_data = sorted(data_points, key=lambda d: d.get('compression', {}).get('pass_count', 0), reverse=False)
    names = [format_short_name(d['method']) for d in sorted_data]

    passes = [d.get('compression', {}).get('pass_count', 0) for d in sorted_data]
    fails = [4 - p for p in passes]

    fig, ax = plt.subplots(figsize=(9, row_height(len(names))))
    y = range(len(names))

    ax.barh(y, passes, color=COLOR_PASS, label='Pass')
    ax.barh(y, fails, left=passes, color=COLOR_FAIL, label='Fail')

    for i, p in enumerate(passes):
        if p > 0: ax.text(p/2, i, str(p), ha='center', va='center', color='white', fontweight='bold', fontsize=9)

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=10)
    ax.set_xlim(0, 4)
    ax.grid(axis='x', linestyle='--', alpha=0.3)
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.02), ncol=2, frameon=False)
    ax.set_title("Compression Tests (4 Algorithms)", fontsize=12, fontweight='bold', pad=30)
    return save_plot()

def _suite_chart(data_points, key, title, weak_label):
    """Stacked pass / weak / fail / insufficient bars for TestU01 or Dieharder.
    Inputs with no usable result get a full-width "insufficient data" bar so an
    empty row is never mistaken for zero passes."""
    setup_matplotlib()
    rows = []
    for d in data_points:
        r = d.get(key, {}) or {}
        ran = bool(r.get('total')) and not r.get('error')
        rows.append({
            'name': format_short_name(d['method']),
            'pass': r.get('pass', 0) if ran else 0,
            'weak': r.get('weak', 0) if ran else 0,
            'fail': r.get('fail', 0) if ran else 0,
            'skipped': len(r.get('insufficient_tests', []) or []),
            'ran': ran,
        })
    full = max([r['pass'] + r['weak'] + r['fail'] for r in rows if r['ran']] or [1])
    rows.sort(key=lambda r: (r['ran'], r['pass']))
    any_skipped = any(r['skipped'] for r in rows if r['ran'])

    names = [r['name'] for r in rows]
    passes = [r['pass'] for r in rows]
    weaks = [r['weak'] for r in rows]
    fails = [r['fail'] for r in rows]
    # Inputs with no usable result get one full-width grey bar.
    skipped = [0 if r['ran'] else full for r in rows]

    fig, ax = plt.subplots(figsize=(9, row_height(len(names))))
    y = range(len(names))
    ax.barh(y, passes, color=COLOR_PASS, label='Pass')
    ax.barh(y, weaks, left=passes, color=COLOR_WARN, label=weak_label)
    ax.barh(y, fails, left=[p + w for p, w in zip(passes, weaks)], color=COLOR_FAIL, label='Fail')
    ax.barh(y, skipped, left=[p + w + f for p, w, f in zip(passes, weaks, fails)], color=COLOR_INVALID, label='Insufficient data')

    for i, r in enumerate(rows):
        if r['pass'] > 0:
            ax.text(r['pass'] / 2, i, str(r['pass']), ha='center', va='center', color='white', fontweight='bold', fontsize=9)
        elif not r['ran']:
            ax.text(full / 2, i, 'insufficient data', ha='center', va='center', color='white', fontweight='bold', fontsize=9)
        if r['ran'] and r['skipped']:
            ax.text(r['pass'] + r['weak'] + r['fail'] + full * 0.01, i, f"{r['skipped']} tests lacked data",
                    va='center', fontsize=8, color='#666666')

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=10)
    ax.set_xlim(0, full * (1.24 if any_skipped else 1.0))
    ax.set_xlabel("Number of test results", fontsize=10)
    ax.grid(axis='x', linestyle='--', alpha=0.3)
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.02), ncol=4, frameon=False, fontsize=10)
    ax.set_title(title, fontsize=12, fontweight='bold', pad=30)
    return save_plot()

def generate_testu01_chart(data_points):
    return _suite_chart(data_points, 'testu01', "TestU01 (Alphabit + Rabbit) Results", 'Suspect')

def generate_dieharder_chart(data_points):
    return _suite_chart(data_points, 'dieharder', "Dieharder Results", 'Weak')

# ----------------- PDF Document Generators -----------------

def header_footer(canvas, doc, title_text="RNG Extractors - Analysis Report"):
    canvas.saveState()
    # Header
    canvas.setFont('Helvetica-Bold', 9)
    canvas.setFillColor(rl_colors.HexColor('#0077B6'))
    canvas.drawString(doc.leftMargin, doc.pagesize[1] - 40, title_text)
    canvas.line(doc.leftMargin, doc.pagesize[1] - 45, doc.pagesize[0] - doc.rightMargin, doc.pagesize[1] - 45)

    # Footer
    canvas.setFont('Helvetica', 9)
    canvas.setFillColor(rl_colors.gray)
    page_num = f"Page {doc.page}"
    canvas.drawString(doc.pagesize[0] - doc.rightMargin - 40, 30, page_num)
    canvas.restoreState()

def first_page_setup(canvas, doc):
    pass # Cover page has no header/footer

def later_pages_setup(canvas, doc):
    header_footer(canvas, doc)

def generate_pdf_report(data_points, total_bits, ranked_methods, selected_tests=None, file_size_bytes=None):
    if selected_tests is None:
        selected_tests = []
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer, pagesize=letter,
        rightMargin=50, leftMargin=50,
        topMargin=60, bottomMargin=50
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'TitleStyle', parent=styles['Title'],
        fontName='Helvetica-Bold', fontSize=28,
        textColor=rl_colors.HexColor('#03045E'), spaceAfter=20, alignment=0
    )
    subtitle_style = ParagraphStyle(
        'Subtitle', parent=styles['Normal'],
        fontName='Helvetica-Oblique', fontSize=14,
        textColor=rl_colors.HexColor('#0077B6'), spaceAfter=30
    )
    h1_style = ParagraphStyle(
        'Heading1', parent=styles['Heading1'],
        fontName='Helvetica-Bold', fontSize=18,
        textColor=rl_colors.HexColor('#03045E'), spaceBefore=20, spaceAfter=10,
        borderPadding=5, borderColor=rl_colors.HexColor('#0077B6'), borderWidth=0, borderBottomWidth=1
    )
    h2_style = ParagraphStyle(
        'Heading2', parent=styles['Heading2'],
        fontName='Helvetica-Bold', fontSize=14,
        textColor=rl_colors.HexColor('#0077B6'), spaceBefore=15, spaceAfter=8
    )
    body_style = ParagraphStyle(
        'Body', parent=styles['Normal'],
        fontName='Helvetica', fontSize=11, leading=16,
        textColor=rl_colors.HexColor('#333333'), spaceAfter=12
    )

    elements = []

    # --- Cover Page ---
    elements.append(Spacer(1, 100))
    elements.append(Paragraph("RNG Extractors", title_style))
    elements.append(Paragraph("Comparative Analysis of Randomness Extraction Methods", subtitle_style))

    deep_selected = [t for t in ('testu01', 'dieharder') if t in selected_tests]
    deep_names = " and ".join("TestU01" if t == 'testu01' else "Dieharder" for t in deep_selected)
    windowed = bool(file_size_bytes) and file_size_bytes * 8 > total_bits
    size_lines = ""
    if file_size_bytes:
        size_lines += f"<b>Input File Size:</b> {file_size_bytes:,} bytes ({file_size_bytes * 8:,} bits)<br/>"
    size_lines += f"<b>{'Core Metrics Computed On' if windowed else 'Input Dataset Size'}:</b> {'the first ' if windowed else ''}{total_bits:,} bits<br/>"
    if windowed and deep_selected:
        size_lines += f"<b>{deep_names} Computed On:</b> each method's output over the whole file<br/>"
    metadata = f"""
    <b>Generation Date:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}<br/>
    {size_lines}
    <b>Methods Analyzed:</b> {len(data_points) - 1} algorithms + 1 raw baseline<br/>
    """
    elements.append(Paragraph(metadata, body_style))
    elements.append(Spacer(1, 250))

    credit = "NED University of Engineering & Technology — Department of Physics, in collaboration with the Centre for Quantum Technologies"
    elements.append(Paragraph(credit, ParagraphStyle('Credit', parent=body_style, fontName='Helvetica-Oblique', fontSize=10, textColor=rl_colors.gray)))
    elements.append(PageBreak())

    # --- Executive Summary ---
    elements.append(Paragraph("Executive Summary", h1_style))
    best_method = ranked_methods[0]['method'] if ranked_methods else "N/A"
    # Methods whose score rounds to the same value as the leader are tied with it.
    tied = [m for m in ranked_methods if round(m['score'], 1) == round(ranked_methods[0]['score'], 1)] if ranked_methods else []
    n_tied = len(tied)
    summary_parts = []
    if 'performance' in selected_tests:
        summary_parts.extend(["maximizing cryptographic entropy", "eliminating bias"])
    if 'nist' in selected_tests:
        summary_parts.append("passing the NIST SP 800-22 statistical test suite")
    if 'testu01' in selected_tests:
        summary_parts.append("passing the TestU01 Alphabit and Rabbit batteries")
    if 'dieharder' in selected_tests:
        summary_parts.append("passing the Dieharder test suite")
    if 'compression' in selected_tests:
        summary_parts.append("resisting data compression")

    objective_text = "evaluating statistical quality"
    if summary_parts:
        if len(summary_parts) > 1:
            objective_text = ", ".join(summary_parts[:-1]) + ", and " + summary_parts[-1]
        else:
            objective_text = summary_parts[0]

    summary_text = (
        f"This report presents a comparative analysis of {len(data_points)-1} randomness extraction algorithms "
        f"applied to an input {f'file of {file_size_bytes:,} bytes' if file_size_bytes else f'bitstream of {total_bits:,} bits'}. The objective is to identify the most effective "
        f"post-processing method for {objective_text}. "
    )
    if n_tied > 1:
        summary_text += (
            f"{n_tied} algorithms share the highest combined score ({ranked_methods[0]['score']:.1f}); "
            f"<b>{best_method}</b> is listed first among them, and the differences between the tied methods are not significant."
        )
    else:
        summary_text += (
            f"Among the evaluated algorithms, <b>{best_method}</b> achieved the highest combined score across the evaluated metrics."
        )
    elements.append(Paragraph(summary_text, body_style))

    # --- Methodology ---
    elements.append(Paragraph("Methodology", h1_style))
    methodology_lines = []
    if 'performance' in selected_tests:
        methodology_lines.append("<b>Shannon & Min-Entropy:</b> Shannon entropy measures the average unpredictability of the bitstream, while Min-entropy measures the worst-case predictability—a vital metric for cryptographic security. Values approaching the ideal 1.0 bit/bit indicate perfect uniformity.")
        methodology_lines.append("<b>Bias:</b> Measures the deviation from an equal probability of 1s and 0s. Lower values (closer to 0.0) represent a perfectly balanced stream.")
        methodology_lines.append("<b>Throughput (Bit Rate):</b> Represents the speed of the extraction process, measured in bits per second (bps). High throughput is essential for real-time applications.")
        methodology_lines.append("<b>Computational Efficiency:</b> The total execution time required by the algorithm in milliseconds. Lower times indicate better performance.")
    if 'nist' in selected_tests:
        methodology_lines.append("<b>NIST SP 800-22 Compliance:</b> The suite's 15 tests, reported as 16 results (Cumulative Sums is run forward and backward), on a 1,000,000-bit sample. 'Pass' means the p-value reached the 0.01 significance threshold, 'Fail' indicates a detectable pattern, and 'Insufficient data' means the test was not applicable to the sample (for example, Random Excursions needs at least 500 excursion cycles). Results marked insufficient are not counted against a method.")
    if 'compression' in selected_tests:
        methodology_lines.append("<b>Compression Viability:</b> Evaluates if the output can be compressed by standard algorithms like zlib, lzma, bzip2, and gzip. Truly random data cannot be compressed efficiently.")
    if 'testu01' in selected_tests:
        methodology_lines.append("<b>TestU01 1.2.3 (Alphabit + Rabbit):</b> The official TestU01 batteries designed for fixed-length bit sequences. SmallCrush runs only on inputs large enough (~908 MB) that no data is reused.")
    if 'dieharder' in selected_tests:
        methodology_lines.append("<b>Dieharder Test Suite:</b> The tests Dieharder itself rates 'Good', run at standard settings. Most tests read hundreds of megabytes; a test that would have to reuse data is reported as 'Insufficient data' and is not counted.")

    item_style = ParagraphStyle('MethodItem', parent=body_style, fontSize=10, leading=14, spaceAfter=6)
    elements.append(Paragraph(f"The evaluation uses {len(methodology_lines)} quantitative metrics to assess extractor performance:", body_style))
    for line in methodology_lines:
        elements.append(Paragraph(line, item_style))
    elements.append(PageBreak())

    def section(title, chart_buf, text):
        # Heading, chart and caption stay on one page: no orphaned caption lines.
        elements.append(KeepTogether([
            Paragraph(title, h2_style),
            chart_image(chart_buf),
            Spacer(1, 6),
            Paragraph(text, body_style),
            Spacer(1, 10),
        ]))

    # --- Results ---
    elements.append(Paragraph("Results & Analysis", h1_style))

    if 'performance' in selected_tests:
        section("Entropy Analysis", generate_entropy_chart(data_points),
                "Shannon entropy and min-entropy for the raw baseline and each method. Values at the 1.0 line mean the output is unbiased at the bit level.")
    if 'nist' in selected_tests:
        section("NIST SP 800-22 Compliance", generate_nist_chart(data_points),
                "NIST results passed (blue), failed (red) and not applicable to the sample (grey). Results that are not applicable are not counted against a method.")
    if 'performance' in selected_tests:
        section("Throughput Analysis", generate_throughput_chart(data_points),
                "Output bits produced per second of extraction time; the raw baseline is not extracted and is omitted. Methods that discard more input rank lower.")
        section("Computational Efficiency", generate_efficiency_chart(data_points),
                "Time each extractor took to process the analysed input. The raw baseline is not extracted and is omitted.")
        section("Bias Analysis", generate_bias_chart(data_points),
                "Residual bias: the difference between the proportions of ones and zeros. Green is below 0.01, amber below 0.05, red 0.05 or more.")
    if 'compression' in selected_tests:
        section("Compression Viability", generate_compression_chart(data_points),
                "How many of 4 compressors (zlib, lzma, bzip2, gzip) could not shrink the output. A pass means the compressed size is at least 99.9% of the original.")
    if 'testu01' in selected_tests:
        section("TestU01 (Alphabit + Rabbit)", generate_testu01_chart(data_points),
                "TestU01 Alphabit and Rabbit results. 'Suspect' means a p-value outside [0.001, 0.999]; 'Fail' means within 1e-10 of 0 or 1. With this many results, an occasional suspect value is expected by chance.")
    if 'dieharder' in selected_tests:
        section("Dieharder Test Suite", generate_dieharder_chart(data_points),
                "Dieharder's own Pass / Weak / Fail assessments. Tests that could not run without reusing data are noted beside each bar; methods that keep less of their input complete fewer tests.")
    elements.append(PageBreak())

    # --- Performance Rankings Table ---
    elements.append(Paragraph("Performance Rankings", h1_style))

    headers = ['Rank', 'Method', 'Score']
    cols_order = []
    if 'nist' in selected_tests:
        headers.append('NIST')
        cols_order.append('nist')
    if 'compression' in selected_tests:
        headers.append('Comp.')
        cols_order.append('comp')
    if 'testu01' in selected_tests:
        headers.append('U01')
        cols_order.append('u01')
    if 'dieharder' in selected_tests:
        headers.append('Die.')
        cols_order.append('die')
    if 'performance' in selected_tests:
        headers.extend(['Shannon', 'Min Ent.', 'Bias', 'Mbps'])
        cols_order.extend(['shannon', 'min', 'bias', 'bps'])

    table_data = [headers]
    for i, m in enumerate(ranked_methods):
        row = [str(i + 1), format_table_name(m['method']), f"{m['score']:.1f}"]
        if 'nist' in cols_order: row.append(f"{m['nistPass']}/16")
        if 'comp' in cols_order: row.append(f"{m.get('compressionPass', 0)}/4")
        if 'u01' in cols_order: row.append(f"{m.get('testu01Pass', 0)}/{m.get('testu01Total', 0)}" if m.get('testu01Total') else "n/a")
        if 'die' in cols_order: row.append(f"{m.get('dieharderPass', 0)}/{m.get('dieharderTotal', 0)}" if m.get('dieharderTotal') else "n/a")
        if 'performance' in selected_tests:
            row.extend([
                f"{m['shannon']:.4f}",
                f"{m['minEntropy']:.4f}",
                f"{m['bias']:.5f}",
                f"{m['bitRate'] / 1e6:,.1f}"
            ])
        table_data.append(row)

    colWidths = [26, 132, 32]
    for col in cols_order:
        if col in ['nist', 'comp', 'u01', 'die']: colWidths.append(36)
        elif col == 'shannon': colWidths.append(44)
        elif col == 'min': colWidths.append(44)
        elif col == 'bias': colWidths.append(46)
        elif col == 'bps': colWidths.append(40)

    t = Table(table_data, colWidths=colWidths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#0077B6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), rl_colors.HexColor('#F8F9FA')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor('#F1F5F9')]),
        ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.HexColor('#E2E8F0')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    elements.append(t)
    notes = []
    if 'nist' in cols_order:
        notes.append("NIST: results passed out of 16; results not applicable to the sample are not counted against a method.")
    if 'u01' in cols_order or 'die' in cols_order:
        notes.append("U01 / Die.: results passed out of the tests that had enough data to run; n/a means none could run.")
    notes.append("Score: weighted combination of the selected suites, scaled to 100. Methods with equal scores are tied.")
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("<br/>".join(notes), ParagraphStyle('Note', parent=body_style, fontSize=8, leading=11, textColor=rl_colors.gray)))
    elements.append(Spacer(1, 12))

    # --- Conclusion ---
    conclusion_heading = Paragraph("Conclusion", h1_style)
    if len(ranked_methods) > 0:
        top = ranked_methods[0]
        if n_tied > 1:
            others = ", ".join(format_table_name(m['method']) for m in tied[1:])
            conclusion_text = (
                f"Based on the analysis of {len(ranked_methods)} post-processing algorithms, {n_tied} methods share the top "
                f"score of {top['score']:.1f}: <b>{format_table_name(top['method'])}</b>, {others}. These results do not "
                f"separate them, so no single method can be called the best on this bitstream. <b>{top['method']}</b>, "
                f"listed first, reached that score"
            )
        else:
            conclusion_text = (
                f"Based on the analysis of {len(ranked_methods)} post-processing algorithms, <b>{top['method']}</b> "
                f"achieved the highest combined score for this bitstream, {top['score']:.1f}"
            )

        reasons = []
        if 'nist' in selected_tests:
            reasons.append(f"successfully passing {top['nistPass']} NIST statistical tests")
        if 'performance' in selected_tests:
            reasons.append(f"maintaining a min-entropy of {top['minEntropy']:.4f} per bit")

        if reasons:
            conclusion_text += ", " + " while ".join(reasons) + ". "
        else:
            conclusion_text += ". "

        conclusion_text += "It combines " if n_tied > 1 else "It offers the best measured balance of "

        balance_parts = []
        if 'performance' in selected_tests:
            balance_parts.extend(["high entropy", f"low bias ({top['bias']:.5f})", "computational throughput"])
        if 'compression' in selected_tests:
            balance_parts.append("incompressibility")
        if 'testu01' in selected_tests or 'dieharder' in selected_tests or 'nist' in selected_tests:
            balance_parts.append("statistical robustness")

        if balance_parts:
            if len(balance_parts) > 1:
                conclusion_text += ", ".join(balance_parts[:-1]) + ", and " + balance_parts[-1] + ". "
            else:
                conclusion_text += balance_parts[0] + ". "
        else:
            conclusion_text += "measured metrics. "

        if n_tied > 1:
            conclusion_text += "Where several methods are tied, throughput and the proportion of input retained are reasonable grounds for choosing between them."
        else:
            conclusion_text += f"On these results, {top['method']} is the recommended post-processing method for this source."
    else:
        conclusion_text = "No post-processing methods were successfully analyzed. Please ensure input data is provided and at least one algorithm is selected."

    elements.append(KeepTogether([conclusion_heading, Paragraph(conclusion_text, body_style)]))

    doc.build(elements, onFirstPage=first_page_setup, onLaterPages=later_pages_setup)
    pdf_buffer.seek(0)
    return pdf_buffer
