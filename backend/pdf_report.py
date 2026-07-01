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
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors as rl_colors

# ----------------- Helper Functions -----------------

def format_short_name(name):
    short = name.split(". ", 1)[-1] if ". " in name else name
    for word in ["Extractor", "Extraction", "Method", "Hash", "Matrix"]:
        short = short.replace(word, "").replace(word.lower(), "").strip()
    if "Leftover Hash Lemma" in name: return "LHL"
    if "Quantum-Proof Strong" in name: return "Quantum"
    if "Goldreich-Levin" in name: return "Goldreich-L."
    if "Chor-Goldreich" in name: return "Chor-G."
    if "Von Neumann" in name: return "Von Neumann"
    if "Arithmetic Coding" in name: return "Arithmetic"
    if "LFSR-Based" in name: return "LFSR"
    if "XOR-Summation" in name: return "XOR-Sum"
    if "Raw (Baseline)" in name: return "Raw"
    if len(short) > 12: return short[:10] + "..."
    return short

def setup_matplotlib():
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'DejaVu Sans']
    plt.rcParams['axes.spines.top'] = False
    plt.rcParams['axes.spines.right'] = False

def save_plot():
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=200)
    buf.seek(0)
    plt.close()
    return buf

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

    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = range(len(names))
    width = 0.35

    ax.bar([pos - width/2 for pos in x], shannons, width, label='Shannon Entropy', color=COLOR_SECONDARY)
    ax.bar([pos + width/2 for pos in x], mins, width, label='Min-Entropy', color=COLOR_PRIMARY)
    
    ax.axhline(y=1.0, color='#333333', linestyle='--', linewidth=1.5, alpha=0.5)
    ax.text(len(names)-1, 1.01, 'Ideal (1.0)', ha='right', va='bottom', fontsize=9, fontweight='bold', color='#333333')

    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=45, ha='right', fontsize=9)
    ax.set_ylim(0, 1.1)
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.25), ncol=2, frameon=False, fontsize=9)
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

    fig, ax = plt.subplots(figsize=(9, max(4, len(names)*0.3)))
    y = range(len(names))

    ax.barh(y, passes, color=COLOR_PASS, label='Pass')
    ax.barh(y, fails, left=passes, color=COLOR_FAIL, label='Fail')
    ax.barh(y, invalids, left=[p+f for p,f in zip(passes, fails)], color=COLOR_INVALID, label='Insufficient data')

    for i, p in enumerate(passes):
        if p > 0: ax.text(p/2, i, str(p), ha='center', va='center', color='white', fontweight='bold', fontsize=8)

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xlim(0, 16)
    ax.grid(axis='x', linestyle='--', alpha=0.3)
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.02), ncol=3, frameon=False)
    ax.set_title("NIST SP 800-22 Test Pass Rate", fontsize=12, fontweight='bold', pad=30)

    return save_plot()

def generate_throughput_chart(data_points):
    setup_matplotlib()
    sorted_data = sorted(data_points, key=lambda d: d['bitRate'], reverse=False)
    names = [format_short_name(d['method']) for d in sorted_data]
    rates = [d['bitRate'] for d in sorted_data]

    fig, ax = plt.subplots(figsize=(9, max(4, len(names)*0.3)))
    y = range(len(names))
    bars = ax.barh(y, rates, color=COLOR_SECONDARY)

    for i, (bar, rate) in enumerate(zip(bars, rates)):
        label = f"{rate/1e6:.2f} Mbps" if rate >= 1e6 else (f"{rate/1e3:.1f} kbps" if rate >= 1000 else f"{int(rate)} bps")
        ax.text(rate + max(rates)*0.01, i, label, va='center', fontsize=8, fontweight='bold', color='#333333')

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=9)
    ax.grid(axis='x', linestyle='--', alpha=0.3)
    ax.set_title("Throughput (Bits Per Second)", fontsize=12, fontweight='bold', pad=15)

    return save_plot()

def generate_efficiency_chart(data_points):
    setup_matplotlib()
    # Handle cases where time is 0 due to fast execution
    for d in data_points:
        d['exec_ms'] = max(d.get('executionTime', 0.1), 0.1)
        
    sorted_data = sorted(data_points, key=lambda d: d['exec_ms'], reverse=True)
    names = [format_short_name(d['method']) for d in sorted_data]
    times = [d['exec_ms'] for d in sorted_data]

    fig, ax = plt.subplots(figsize=(9, max(4, len(names)*0.3)))
    y = range(len(names))
    bars = ax.barh(y, times, color=COLOR_ACCENT)

    for i, (bar, t) in enumerate(zip(bars, times)):
        label = f"{t:.1f} ms" if t < 1 else f"{int(t)} ms"
        ax.text(t + max(times)*0.01, i, label, va='center', fontsize=8, fontweight='bold', color='#333333')

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=9)
    ax.grid(axis='x', linestyle='--', alpha=0.3)
    ax.set_title("Computational Efficiency (Execution Time, Lower is Better)", fontsize=12, fontweight='bold', pad=15)

    return save_plot()

def generate_bias_chart(data_points):
    setup_matplotlib()
    sorted_data = sorted(data_points, key=lambda d: d['bias'], reverse=True)
    names = [format_short_name(d['method']) for d in sorted_data]
    biases = [d['bias'] for d in sorted_data]

    fig, ax = plt.subplots(figsize=(9, max(4, len(names)*0.3)))
    y = range(len(names))
    
    colors = [COLOR_EXCELLENT if b < 0.01 else (COLOR_WARN if b < 0.05 else COLOR_FAIL) for b in biases]
    bars = ax.barh(y, biases, color=colors)

    for i, (bar, b) in enumerate(zip(bars, biases)):
        ax.text(b + max(biases)*0.01, i, f"{b:.4f}", va='center', fontsize=8, fontweight='bold', color='#333333')

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=9)
    ax.grid(axis='x', linestyle='--', alpha=0.3)
    ax.set_title("Bias Level (Lower is Better)", fontsize=12, fontweight='bold', pad=30)
    
    legend_elements = [
        mpatches.Patch(color=COLOR_EXCELLENT, label='Excellent (< 0.01)'),
        mpatches.Patch(color=COLOR_WARN, label='Moderate (< 0.05)'),
        mpatches.Patch(color=COLOR_FAIL, label='High (>= 0.05)')
    ]
    ax.legend(handles=legend_elements, loc='upper right', frameon=True, facecolor='white', framealpha=0.9, fontsize=9)

    return save_plot()

def generate_compression_chart(data_points):
    setup_matplotlib()
    sorted_data = sorted(data_points, key=lambda d: d.get('compression', {}).get('pass_count', 0), reverse=False)
    names = [format_short_name(d['method']) for d in sorted_data]
    
    passes = [d.get('compression', {}).get('pass_count', 0) for d in sorted_data]
    fails = [4 - p for p in passes]
    
    fig, ax = plt.subplots(figsize=(9, max(4, len(names)*0.3)))
    y = range(len(names))
    
    ax.barh(y, passes, color=COLOR_PASS, label='Pass')
    ax.barh(y, fails, left=passes, color=COLOR_FAIL, label='Fail')
    
    for i, p in enumerate(passes):
        if p > 0: ax.text(p/2, i, str(p), ha='center', va='center', color='white', fontweight='bold', fontsize=8)
        
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xlim(0, 4)
    ax.grid(axis='x', linestyle='--', alpha=0.3)
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.02), ncol=2, frameon=False)
    ax.set_title("Compression Tests (4 Algorithms)", fontsize=12, fontweight='bold', pad=30)
    return save_plot()

def generate_testu01_chart(data_points):
    setup_matplotlib()
    sorted_data = sorted(data_points, key=lambda d: d.get('testu01', {}).get('pass', 0), reverse=False)
    names = [format_short_name(d['method']) for d in sorted_data]
    
    passes = [d.get('testu01', {}).get('pass', 0) for d in sorted_data]
    fails = [d.get('testu01', {}).get('fail', 0) for d in sorted_data]
    totals = [p + f for p, f in zip(passes, fails)]
    
    max_total = max(totals) if totals else 15
    if max_total == 0: max_total = 15
    
    fig, ax = plt.subplots(figsize=(9, max(4, len(names)*0.3)))
    y = range(len(names))
    
    ax.barh(y, passes, color=COLOR_PASS, label='Pass')
    ax.barh(y, fails, left=passes, color=COLOR_FAIL, label='Fail')
    
    for i, p in enumerate(passes):
        if p > 0: ax.text(p/2, i, str(p), ha='center', va='center', color='white', fontweight='bold', fontsize=8)
        
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xlim(0, max_total)
    ax.grid(axis='x', linestyle='--', alpha=0.3)
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.02), ncol=2, frameon=False)
    ax.set_title("TestU01 SmallCrush Pass Rate", fontsize=12, fontweight='bold', pad=30)
    return save_plot()

def generate_dieharder_chart(data_points):
    setup_matplotlib()
    sorted_data = sorted(data_points, key=lambda d: d.get('dieharder', {}).get('pass', 0), reverse=False)
    names = [format_short_name(d['method']) for d in sorted_data]
    
    passes = [d.get('dieharder', {}).get('pass', 0) for d in sorted_data]
    fails = [d.get('dieharder', {}).get('fail', 0) for d in sorted_data]
    weaks = [d.get('dieharder', {}).get('weak', 0) for d in sorted_data]
    totals = [p + f + w for p, f, w in zip(passes, fails, weaks)]
    
    max_total = max(totals) if totals else 100
    if max_total == 0: max_total = 100
    
    fig, ax = plt.subplots(figsize=(9, max(4, len(names)*0.3)))
    y = range(len(names))
    
    ax.barh(y, passes, color=COLOR_PASS, label='Pass')
    ax.barh(y, weaks, left=passes, color=COLOR_WARN, label='Weak')
    ax.barh(y, fails, left=[p+w for p,w in zip(passes, weaks)], color=COLOR_FAIL, label='Fail')
    
    for i, p in enumerate(passes):
        if p > 0: ax.text(p/2, i, str(p), ha='center', va='center', color='white', fontweight='bold', fontsize=8)
        
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xlim(0, max_total)
    ax.grid(axis='x', linestyle='--', alpha=0.3)
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.02), ncol=3, frameon=False)
    ax.set_title("Dieharder Pass Rate", fontsize=12, fontweight='bold', pad=30)
    return save_plot()

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

def generate_pdf_report(data_points, total_bits, ranked_methods):
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
    
    metadata = f"""
    <b>Generation Date:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}<br/>
    <b>Input Dataset Size:</b> {total_bits:,} bits<br/>
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
    summary_text = (
        f"This report presents a rigorous comparative analysis of {len(data_points)-1} randomness extraction algorithms "
        f"applied to an input bitstream of {total_bits:,} bits. The objective is to identify the most effective "
        f"post-processing method for maximizing cryptographic entropy, eliminating bias, and passing the comprehensive "
        f"NIST SP 800-22 statistical test suite. Among the evaluated algorithms, <b>{best_method}</b> emerged as the optimal "
        f"method, demonstrating the highest combined performance across all statistical and computational metrics."
    )
    elements.append(Paragraph(summary_text, body_style))

    # --- Methodology ---
    elements.append(Paragraph("Methodology", h1_style))
    methodology_text = (
        "The evaluation utilizes five key quantitative metrics to assess extractor performance:<br/><br/>"
        "<b>Shannon & Min-Entropy:</b> Shannon entropy measures the average unpredictability of the bitstream, while Min-entropy measures "
        "the worst-case predictability—a vital metric for cryptographic security. Values approaching the ideal 1.0 bit/bit indicate perfect uniformity.<br/>"
        "<b>Bias:</b> Measures the deviation from an equal probability of 1s and 0s. Lower values (closer to 0.0) represent a perfectly balanced stream.<br/>"
        "<b>Throughput (Bit Rate):</b> Represents the speed of the extraction process, measured in bits per second (bps). High throughput is essential for real-time applications.<br/>"
        "<b>Computational Efficiency:</b> The total execution time required by the algorithm in milliseconds. Lower times indicate better performance.<br/>"
        "<b>NIST SP 800-22 Compliance:</b> A rigorous suite of 16 statistical tests. Methods are evaluated based on their pass rate, "
        "where 'Pass' means the p-value exceeded the 0.01 significance threshold, 'Fail' indicates a detectable pattern, and 'Insufficient data' "
        "means the input was too short to perform the test."
    )
    elements.append(Paragraph(methodology_text, body_style))
    elements.append(PageBreak())

    # --- Results ---
    elements.append(Paragraph("Results & Analysis", h1_style))

    # 1. Entropy
    elements.append(Paragraph("Entropy Analysis", h2_style))
    elements.append(Image(generate_entropy_chart(data_points), width=450, height=225))
    elements.append(Paragraph("The chart above visualizes both Shannon entropy and Min-entropy. Methods approaching the 1.0 ideal line offer the highest theoretical unpredictability, mitigating vulnerabilities associated with raw, unextracted bitstreams.", body_style))
    elements.append(Spacer(1, 15))

    # 2. NIST
    elements.append(Paragraph("NIST SP 800-22 Compliance", h2_style))
    elements.append(Image(generate_nist_chart(data_points), width=450, height=225))
    elements.append(Paragraph("NIST compliance is the gold standard for statistical randomness. The stacked bars illustrate the proportion of tests passed (teal) versus failed (red). The top-performing methods successfully clear the majority of applicable tests.", body_style))
    elements.append(PageBreak())

    # 3. Throughput
    elements.append(Paragraph("Throughput Analysis", h2_style))
    elements.append(Image(generate_throughput_chart(data_points), width=450, height=225))
    elements.append(Paragraph("Throughput is evaluated in bits per second. While complex cryptographic hashes may yield excellent entropy, simpler debiasing techniques often provide superior throughput, representing a critical trade-off for system design.", body_style))
    elements.append(Spacer(1, 15))

    # 4. Computational Efficiency
    elements.append(Paragraph("Computational Efficiency", h2_style))
    elements.append(Image(generate_efficiency_chart(data_points), width=450, height=225))
    elements.append(Paragraph("Execution time (latency) in milliseconds. Efficient extractors are positioned at the top with minimal latency, while quadratic-time algorithms are visually distinct due to higher execution times.", body_style))
    elements.append(PageBreak())

    # 5. Bias
    elements.append(Paragraph("Bias Analysis", h2_style))
    elements.append(Image(generate_bias_chart(data_points), width=450, height=225))
    elements.append(Paragraph("This chart measures residual bias. Bars in green indicate excellent performance (bias < 0.01), amber signifies moderate bias, and red indicates high deviation from uniformity. An ideal extractor completely eliminates systemic bias.", body_style))
    elements.append(PageBreak())

    # 6. Compression
    elements.append(Paragraph("Compression Viability", h2_style))
    elements.append(Image(generate_compression_chart(data_points), width=450, height=225))
    elements.append(Paragraph("Genuinely random data cannot be efficiently compressed. This chart shows the pass rate of 4 compression algorithms (zlib, lzma, bzip2, gzip), where passing means the compression ratio is >= 0.999.", body_style))
    elements.append(Spacer(1, 15))
    
    # 7. TestU01
    elements.append(Paragraph("TestU01 (SmallCrush)", h2_style))
    elements.append(Image(generate_testu01_chart(data_points), width=450, height=225))
    elements.append(Paragraph("TestU01 is a software library offering empirical statistical tests for uniform random number generators. The SmallCrush battery is used here.", body_style))
    elements.append(PageBreak())
    
    # 8. Dieharder
    elements.append(Paragraph("Dieharder Test Suite", h2_style))
    elements.append(Image(generate_dieharder_chart(data_points), width=450, height=225))
    elements.append(Paragraph("Dieharder evaluates random number generators via a collection of rigorous statistical tests. Requires substantial data size to yield meaningful results.", body_style))
    elements.append(PageBreak())

    # --- Performance Rankings Table ---
    elements.append(Paragraph("Performance Rankings", h1_style))
    
    table_data = [['Rank', 'Method', 'Score', 'NIST', 'Comp.', 'U01', 'Die.', 'Shannon', 'Min Ent.', 'Bias', 'bps']]
    for i, m in enumerate(ranked_methods):
        table_data.append([
            str(i + 1),
            format_short_name(m['method']),
            f"{m['score']:.1f}",
            f"{m['nistPass']}/15",
            f"{m.get('compressionPass', 0)}/4",
            f"{m.get('testu01Pass', 0)}/15",
            f"{m.get('dieharderPass', 0)}/100",
            f"{m['shannon']:.4f}",
            f"{m['minEntropy']:.4f}",
            f"{m['bias']:.4f}",
            f"{int(m['bitRate']):,}"
        ])

    t = Table(table_data, colWidths=[25, 90, 30, 35, 35, 35, 35, 45, 45, 40, 60])
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
    elements.append(Spacer(1, 20))

    # --- Conclusion ---
    elements.append(Paragraph("Conclusion", h1_style))
    if len(ranked_methods) > 0:
        top = ranked_methods[0]
        conclusion_text = (
            f"Based on the comprehensive analysis of {len(ranked_methods)} post-processing algorithms, <b>{top['method']}</b> "
            f"is definitively the optimal extraction method for this specific bitstream. It achieved the highest cumulative score "
            f"of {top['score']:.1f}, successfully passing {top['nistPass']} NIST statistical tests while maintaining an exceptional "
            f"min-entropy level of {top['minEntropy']:.4f} per bit. The data clearly indicates that this algorithm provides the best "
            f"balance of cryptographic unpredictability, minimal bias ({top['bias']:.4f}), and computational throughput. We recommend "
            f"integrating {top['method']} for secure, real-time randomness generation under these operational conditions."
        )
    else:
        conclusion_text = "No post-processing methods were successfully analyzed. Please ensure input data is provided and at least one algorithm is selected."
        
    elements.append(Paragraph(conclusion_text, body_style))

    doc.build(elements, onFirstPage=first_page_setup, onLaterPages=later_pages_setup)
    pdf_buffer.seek(0)
    return pdf_buffer
