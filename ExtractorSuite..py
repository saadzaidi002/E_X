# ExtractorSuite.py - FULL CORRECTED & COMPLETE VERSION

import os
import threading
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import time
from tkinter import *
from tkinter.filedialog import askopenfilename, askdirectory
from tkinter import messagebox
import queue
from tkinter import ttk

from GUI import CustomButton
from GUI import Input
from GUI import LabelTag
from Extractors import Extractors

# ---- Real NIST SP 800-22 test modules (same ones used by Main.py) ----
from ApproximateEntropy import ApproximateEntropy as aet
from Complexity import ComplexityTest as ct
from CumulativeSum import CumulativeSums as cst
from FrequencyTest import FrequencyTest as ft
from Matrix import Matrix as mt
from RandomExcursions import RandomExcursions as ret
from RunTest import RunTest as rt
from Serial import Serial as serial
from Spectral import SpectralTest as st
from TemplateMatching import TemplateMatching as tm
from Universal import Universal as ut

plt.rcParams['figure.max_open_warning'] = 0
plt.rcParams['font.size'] = 11
plt.rcParams['font.family'] = 'serif'

RAW_LABEL = "Raw (No Extraction)"


class QRNGExtractorSuite(Frame):

    def __init__(self, master=None):
        Frame.__init__(self, master=master)
        self._master = master
        self.init_variables()
        self.init_window()

    def init_variables(self):
        self.extractor_list = Extractors.get_all_extractors()
        self._input_bits = None
        self._results = {}
        self._ui_queue = queue.Queue()
        self._anim_angle = 0
        self._anim_running = False
        self._tick_shown = False

    def init_window(self):
        self.master.title("QRNG Extractor Suite - 20 Methods + NIST")
        self.master.geometry("1350x730")
        self.master.resizable(0, 0)

        LabelTag(self.master, "QRNG Post-Processing Extractor Suite (20 Methods + NIST)", 20, 15, 1310, font_size=15)

        # Input Section
        input_frame = LabelFrame(self.master, text="Input Raw Bits Data", padx=10, pady=10)
        input_frame.place(x=20, y=55, width=1310, height=120)

        self.__binary_file_input = Input(input_frame, 'Binary Bits File (.txt)', 10, 10, True, self.select_binary_file, button_xcoor=1080, button_width=190)
        self.__string_file_input = Input(input_frame, 'String / URL File', 10, 48, True, self.select_string_file, button_xcoor=1080, button_width=190)

        # Extraction Methods
        extractor_frame = LabelFrame(self.master, text="Select Extraction Methods (20)", padx=10, pady=5)
        extractor_frame.place(x=20, y=190, width=1310, height=390)

        canvas = Canvas(extractor_frame, width=700)
        scrollbar = Scrollbar(extractor_frame, orient="vertical", command=canvas.yview)
        scroll_frame = Frame(canvas)
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=False)
        scrollbar.pack(side="left", fill="y")

        self._extractor_vars = []
        for i, (name, _) in enumerate(self.extractor_list):
            var = IntVar()
            cb = ttk.Checkbutton(scroll_frame, text=name, variable=var, command=self.on_checkbox_change)
            cb.grid(row=i//2, column=i%2, sticky="w", padx=35, pady=6)
            self._extractor_vars.append((name, var))

        self._anim_canvas = Canvas(extractor_frame, bg="#f0f0f0", highlightthickness=0)
        self._anim_canvas.pack(side="left", fill="both", expand=True, padx=10, pady=5)

        # Buttons
        btn_y = 605
        CustomButton(self.master, "Select All", 30, btn_y, 110, self.select_all_extractors)
        CustomButton(self.master, "Deselect All", 160, btn_y, 130, self.deselect_all_extractors)
        self.execute_btn = CustomButton(self.master, "Execute + NIST", 310, btn_y, 180, self.execute_extraction)
        CustomButton(self.master, "Save All Bits", 510, btn_y, 160, self.save_all_bits)
        CustomButton(self.master, "Save Graphs", 690, btn_y, 150, self.save_graphs_only)
        CustomButton(self.master, "Reset", 860, btn_y, 80, self.reset)
        CustomButton(self.master, "Exit", 960, btn_y, 80, lambda: self.master.quit())

        self.status_label = ttk.Label(self.master, text="Ready", font=("Calibri", 12, "bold"))
        self.status_label.place(x=30, y=665)

        self.progress = ttk.Progressbar(self.master, length=1050, mode='determinate')
        self.progress.place(x=30, y=690)

    def on_checkbox_change(self):
        any_selected = any(var.get() == 1 for _, var in self._extractor_vars)
        if any_selected:
            self.progress['value'] = 100
            self.status_label.config(text="Ready", foreground="black")
        else:
            self.progress['value'] = 0
            self.status_label.config(text="Ready", foreground="black")

    # ==================== Animation ====================
    def start_spinner(self):
        self._anim_running = True
        self._tick_shown = False
        self._anim_angle = 0
        self._anim_canvas.delete("all")
        self._draw_spinner()

    def _draw_spinner(self):
        if not self._anim_running: return
        c = self._anim_canvas
        c.delete("all")
        w = c.winfo_width() or 400
        h = c.winfo_height() or 360
        cx, cy, r = w // 2, h // 2, min(w, h) // 4
        c.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#cccccc", width=8)
        a = self._anim_angle
        c.create_arc(cx - r, cy - r, cx + r, cy + r, start=a, extent=270, outline="#3498db", width=8, style=ARC)
        c.create_text(cx, cy + r + 30, text="Processing...", font=("Calibri", 12, "bold"), fill="#3498db")
        self._anim_angle = (self._anim_angle + 8) % 360
        self.master.after(30, self._draw_spinner)

    def show_success_tick(self):
        self._anim_running = False
        self._tick_shown = True
        self._tick_anim_step = 0
        self._animate_tick()

    def _animate_tick(self):
        c = self._anim_canvas
        c.delete("all")
        w = c.winfo_width() or 400
        h = c.winfo_height() or 360
        cx, cy, r = w // 2, h // 2, min(w, h) // 4
        step = self._tick_anim_step
        if step <= 20:
            extent = (step / 20) * 360
            c.create_arc(cx - r, cy - r, cx + r, cy + r, start=90, extent=-extent, outline="#2ecc71", width=8, style=ARC)
        else:
            c.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#2ecc71", width=8)
            progress = (step - 20) / 20.0
            p1 = (cx - r * 0.45, cy + r * 0.05)
            p2 = (cx - r * 0.1,  cy + r * 0.4)
            p3 = (cx + r * 0.45, cy - r * 0.35)
            if progress < 0.5:
                t = progress / 0.5
                mx = p1[0] + (p2[0] - p1[0]) * t
                my = p1[1] + (p2[1] - p1[1]) * t
                c.create_line(p1[0], p1[1], mx, my, fill="#2ecc71", width=6, capstyle=ROUND)
            else:
                c.create_line(p1[0], p1[1], p2[0], p2[1], fill="#2ecc71", width=6, capstyle=ROUND)
                t = (progress - 0.5) / 0.5
                mx = p2[0] + (p3[0] - p2[0]) * t
                my = p2[1] + (p3[1] - p2[1]) * t
                c.create_line(p2[0], p2[1], mx, my, fill="#2ecc71", width=6, capstyle=ROUND)
        if step < 40:
            self._tick_anim_step += 1
            self.master.after(25, self._animate_tick)
        else:
            c.delete("all")
            c.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#2ecc71", width=8)
            p1 = (cx - r * 0.45, cy + r * 0.05)
            p2 = (cx - r * 0.1,  cy + r * 0.4)
            p3 = (cx + r * 0.45, cy - r * 0.35)
            c.create_line(p1[0], p1[1], p2[0], p2[1], fill="#2ecc71", width=6, capstyle=ROUND, joinstyle=ROUND)
            c.create_line(p2[0], p2[1], p3[0], p3[1], fill="#2ecc71", width=6, capstyle=ROUND, joinstyle=ROUND)
            c.create_text(cx, cy + r + 30, text="Complete!", font=("Calibri", 12, "bold"), fill="#27ae60")

    # ==================== File Selection ====================
    def select_binary_file(self):
        file = askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if file: self.__binary_file_input.set_data(file)

    def select_string_file(self):
        file = askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if file: self.__string_file_input.set_data(file)

    def load_input_bits(self):
        if self.__binary_file_input.get_data().strip():
            with open(self.__binary_file_input.get_data(), 'r', encoding='utf-8') as f:
                text = f.read()
            return np.array([int(c) for c in text if c in '01'], dtype=np.int8)
        elif self.__string_file_input.get_data().strip():
            with open(self.__string_file_input.get_data(), 'r', encoding='utf-8') as f:
                text = f.read()
            return np.array([int(c) for c in text if c in '01'], dtype=np.int8)
        messagebox.showwarning("Input Required", "Please select a file.")
        return None

    # ==================== Execution ====================
    def execute_extraction(self):
        self._input_bits = self.load_input_bits()
        if self._input_bits is None: return

        selected = [(name, func) for name, var in self._extractor_vars if var.get() == 1 
                    for n, func in self.extractor_list if n == name]
        if not selected:
            messagebox.showwarning("No Selection", "Select at least one method.")
            return

        self.execute_btn.config(state=DISABLED)
        self.start_spinner()
        threading.Thread(target=self._extraction_worker, args=(selected,), daemon=True).start()

    def _extraction_worker(self, selected):
        self._results = {}

        # ---- Raw input baseline (always included for comparison graphs) ----
        try:
            raw_start = time.time()
            raw_elapsed = max(0.001, time.time() - raw_start)
            raw_metrics = self.calculate_metrics(self._input_bits, raw_elapsed)
            raw_nist = self.run_nist_suite(self._input_bits)
            self._results[RAW_LABEL] = {
                'bits': self._input_bits, 'metrics': raw_metrics, 'nist': raw_nist
            }
        except Exception as e:
            print(f"Error computing raw baseline: {e}")

        for i, (name, func) in enumerate(selected):
            self._ui_queue.put({'type':'progress', 'current':i+1, 'total':len(selected), 'name':name})
            try:
                start_time = time.time()
                extracted = func(self._input_bits)
                exec_time = time.time() - start_time
                metrics = self.calculate_metrics(extracted, exec_time)
                nist_result = self.run_nist_suite(extracted)
                self._results[name] = {'bits': extracted, 'metrics': metrics, 'nist': nist_result}
            except Exception as e:
                print(f"Error in {name}: {e}")
        self._ui_queue.put({'type':'complete'})

    def calculate_metrics(self, bits, exec_time=0.0):
        bits = np.asarray(bits, dtype=np.int8)
        total = len(bits)
        if total == 0:
            return {'total':0, 'bias':1.0, 'shannon':0.0, 'min_entropy':0.0, 'bit_rate':0, 'efficiency':0.0, 'time_sec':exec_time}
        ones = int(np.sum(bits))
        zeros = total - ones
        p1 = ones / total
        p0 = zeros / total
        bias = abs(ones - zeros) / total
        shannon = -(p1 * np.log2(p1) + p0 * np.log2(p0)) if 0 < p1 < 1 else 0.0
        min_entropy = -np.log2(max(p1, p0)) if total > 0 else 0.0
        bit_rate = int(total / max(0.001, exec_time))
        efficiency = total / (len(self._input_bits) + 1e-9)
        return {'total': total, 'bias': bias, 'shannon': shannon, 'min_entropy': min_entropy,
                'bit_rate': bit_rate, 'efficiency': efficiency, 'time_sec': exec_time}

    def run_nist_suite(self, bits):
        """Run the REAL NIST SP 800-22 statistical test suite (16 tests) on the
        extracted bitstream, using the same test modules Main.py uses
        (FrequencyTest, RunTest, Matrix, Spectral, TemplateMatching, Universal,
        Complexity, Serial, ApproximateEntropy, CumulativeSum, RandomExcursions).

        Returns a dict: {'pass': int, 'fail': int, 'invalid': int, 'total': int,
                          'pass_rate': float} so comparison graphs can build
        stacked PASS/FAIL/Invalid bars exactly like the reference NIST chart.
        """
        bits = np.asarray(bits, dtype=np.int8)
        binary_data = ''.join(map(str, bits.tolist()))
        length = len(binary_data)

        # One representative p_value per NIST test TYPE -> always 16 slots total,
        # matching the 16-row "_test_type" list used by Main.py.
        p_values = []

        def safe_run(fn, *args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception:
                return None

        def single(result):
            """(p_value, bool) tuple -> representative p_value, or NaN on failure."""
            if result is None:
                return float('nan')
            return float(result[0])

        def serial_combined(result):
            """Serial test returns ((p1, bool1), (p2, bool2)); use the worse
            (minimum) p_value as the representative for this single test slot."""
            if result is None:
                return float('nan')
            return float(min(result[0][0], result[1][0]))

        def excursions_combined(result):
            """Random Excursions / Variant return a list of per-state tuples
            (state, x, y, p_value, bool); use the minimum valid p_value as the
            representative for this single test slot (standard NIST convention:
            the test type fails if any visited state fails)."""
            if result is None:
                return float('nan')
            valid_p = [float(item[-2]) for item in result if not math.isnan(float(item[-2]))]
            if not valid_p:
                return float('nan')
            return min(valid_p)

        if length < 100:
            # Not enough bits to run anything meaningful: mark all 16 as invalid
            p_values = [float('nan')] * 16
        else:
            # 1. Frequency (Monobit) Test
            p_values.append(single(safe_run(ft.monobit_test, binary_data)))
            # 2. Frequency Test within a Block
            p_values.append(single(safe_run(ft.block_frequency, binary_data)))
            # 3. Runs Test
            p_values.append(single(safe_run(rt.run_test, binary_data)))
            # 4. Test for the Longest Run of Ones in a Block
            p_values.append(single(safe_run(rt.longest_one_block_test, binary_data)))
            # 5. Binary Matrix Rank Test
            p_values.append(single(safe_run(mt.binary_matrix_rank_text, binary_data)))
            # 6. Discrete Fourier Transform (Spectral) Test
            p_values.append(single(safe_run(st.spectral_test, binary_data)))
            # 7. Non-overlapping Template Matching Test
            p_values.append(single(safe_run(tm.non_overlapping_test, binary_data)))
            # 8. Overlapping Template Matching Test
            p_values.append(single(safe_run(tm.overlapping_patterns, binary_data)))
            # 9. Maurer's "Universal Statistical" Test (requires length >= 387,840)
            if length >= 387840:
                p_values.append(single(safe_run(ut.statistical_test, binary_data)))
            else:
                p_values.append(-1.0)
            # 10. Linear Complexity Test
            p_values.append(single(safe_run(ct.linear_complexity_test, binary_data)))
            # 11. Serial Test
            p_values.append(serial_combined(safe_run(serial.serial_test, binary_data)))
            # 12. Approximate Entropy Test
            p_values.append(single(safe_run(aet.approximate_entropy_test, binary_data)))
            # 13. Cumulative Sums Test (Forward)
            p_values.append(single(safe_run(cst.cumulative_sums_test, binary_data, mode=0)))
            # 14. Cumulative Sums Test (Backward)
            p_values.append(single(safe_run(cst.cumulative_sums_test, binary_data, mode=1)))
            # 15. Random Excursions Test
            p_values.append(excursions_combined(safe_run(ret.random_excursions_test, binary_data)))
            # 16. Random Excursions Variant Test
            p_values.append(excursions_combined(safe_run(ret.variant_test, binary_data)))

        passes = sum(1 for p in p_values if (not math.isnan(p)) and p != -1.0 and p >= 0.01)
        fails = sum(1 for p in p_values if (not math.isnan(p)) and p != -1.0 and 0 <= p < 0.01)
        invalid = sum(1 for p in p_values if math.isnan(p) or p == -1.0)
        total = len(p_values) if p_values else 1
        pass_rate = passes / total if total > 0 else 0.0

        return {'pass': passes, 'fail': fails, 'invalid': invalid, 'total': total, 'pass_rate': pass_rate}

    def process_ui_queue(self):
        try:
            while True:
                msg = self._ui_queue.get_nowait()
                if msg['type'] == 'progress':
                    self.status_label.config(text=f"Processing: {msg['name']}", foreground="blue")
                    self.progress['value'] = (msg['current'] / msg['total']) * 100
                elif msg['type'] == 'complete':
                    self.status_label.config(text="✅ All Done", foreground="green")
                    self.progress['value'] = 100
                    self.execute_btn.config(state=NORMAL)
                    self.show_success_tick()
                    self.generate_all_comparison_graphs()
        except queue.Empty:
            pass
        self.master.after(100, self.process_ui_queue)

    # ==================== Graphs ====================
    def generate_all_comparison_graphs(self, folder=None):
        if folder is None: folder = "results"
        os.makedirs(folder, exist_ok=True)
        self.generate_shannon_minentropy_graph(folder)
        self.generate_bitrate_graph(folder)
        self.generate_efficiency_graph(folder)
        self.generate_bias_graph(folder)
        self.generate_nist_graph(folder)

    def _extractor_names(self):
        """All result names except the raw baseline, in original execution order."""
        return [n for n in self._results.keys() if n != RAW_LABEL]

    # ---------- 1. Shannon Entropy & Min-Entropy (grouped bars + ideal line) ----------
    def generate_shannon_minentropy_graph(self, folder):
        names = self._extractor_names()
        if RAW_LABEL in self._results:
            names = names + [RAW_LABEL]

        shannons = [self._results[n]['metrics']['shannon'] for n in names]
        min_ents = [self._results[n]['metrics']['min_entropy'] for n in names]

        fig, ax = plt.subplots(figsize=(20, 9))
        x = np.arange(len(names))
        width = 0.35

        ax.bar(x - width / 2, shannons, width, label='Shannon Entropy',
               color='#3498db', edgecolor='white', linewidth=1)
        ax.bar(x + width / 2, min_ents, width, label='Min-Entropy',
               color='#e74c3c', edgecolor='white', linewidth=1)

        ax.axhline(y=1.0, color='green', linestyle='--', linewidth=2, label='Ideal (1.0)')

        ax.set_ylabel('Entropy (bits/bit)', fontsize=13, fontweight='bold')
        ax.set_title('Shannon Entropy & Min-Entropy — All 20 Methods + Raw Data',
                     fontsize=16, fontweight='bold', pad=20)

        ax.set_xticks(x)
        ax.set_xticklabels(names, fontsize=9.5, ha='right')
        plt.xticks(rotation=45, ha='right')

        ax.set_ylim(0.90, 1.02)
        ax.legend(fontsize=11, loc='upper right')
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        plt.savefig(os.path.join(folder, "Shannon_MinEntropy_Comparison.png"), dpi=300, bbox_inches='tight')
        plt.close()

    # ---------- 2. Bit Rate (two-panel: raw vs top extractors) ----------
    def generate_bitrate_graph(self, folder):
        raw_rate = self._results.get(RAW_LABEL, {}).get('metrics', {}).get('bit_rate', 0)

        extractor_names = self._extractor_names()
        rates = [(n, self._results[n]['metrics']['bit_rate']) for n in extractor_names]
        rates.sort(key=lambda x: x[1], reverse=True)
        top = rates[:15]
        names_sorted = [r[0] for r in top]
        rates_sorted = [r[1] for r in top]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10), gridspec_kw={'width_ratios': [1, 3]})

        ax1.barh(['Raw'], [raw_rate], color='#e74c3c', height=0.6)
        ax1.set_title('Raw Data Bit Rate', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Bits per second')
        if raw_rate > 0:
            ax1.text(raw_rate * 0.05, 0, f'{int(raw_rate):,}',
                     va='center', ha='left', fontweight='bold', fontsize=12)

        bars = ax2.barh(names_sorted, rates_sorted, color='#3498db',
                         edgecolor='black', alpha=0.85)
        ax2.set_title('Bit Rate After Post-Processing (Top 15 Extractors)',
                       fontsize=14, fontweight='bold')
        ax2.set_xlabel('Bit Rate (bits per second)')
        ax2.invert_yaxis()

        for bar in bars:
            width = bar.get_width()
            ax2.text(width + width * 0.02, bar.get_y() + bar.get_height() / 2,
                      f'{int(width):,}', va='center', fontsize=10, fontweight='bold')

        plt.suptitle('Bit Rate Comparison: Raw vs Post-Processed Data',
                     fontsize=16, fontweight='bold', y=1.02)

        plt.tight_layout()
        plt.savefig(os.path.join(folder, "Bit_Rate_Comparison.png"), dpi=300, bbox_inches='tight')
        plt.close()

    # ---------- 3. Computational Efficiency (sorted ascending, purple bars) ----------
    def generate_efficiency_graph(self, folder):
        names = self._extractor_names()
        runtimes = [(n, self._results[n]['metrics']['time_sec'] * 1000) for n in names]
        runtimes.sort(key=lambda x: x[1])

        names_sorted = [r[0] for r in runtimes]
        times_sorted = [r[1] for r in runtimes]

        fig, ax = plt.subplots(figsize=(15, 10))
        bars = ax.barh(range(len(names_sorted)), times_sorted, color='#9b59b6',
                        height=0.65, edgecolor='white', linewidth=1.2)

        for bar, t_ms in zip(bars, times_sorted):
            ax.text(t_ms + max(times_sorted + [1]) * 0.01, bar.get_y() + bar.get_height() / 2,
                     f'{t_ms:.1f} ms', va='center', fontsize=10, fontweight='bold', color='#2c3e50')

        ax.set_yticks(range(len(names_sorted)))
        ax.set_yticklabels(names_sorted, fontsize=11)

        ax.set_xlabel('Execution Time (milliseconds)', fontsize=13, fontweight='bold', labelpad=10)
        ax.set_title('Computational Efficiency — All 20 Methods', fontsize=16, fontweight='bold', pad=20)

        ax.grid(axis='x', linestyle='--', alpha=0.4)
        ax.invert_yaxis()

        plt.tight_layout()
        plt.savefig(os.path.join(folder, "Computational_Efficiency_Comparison.png"), dpi=300, bbox_inches='tight')
        plt.close()

    # ---------- 4. Bias (sorted ascending, green/orange/red by threshold) ----------
    def generate_bias_graph(self, folder):
        names = self._extractor_names()
        if RAW_LABEL in self._results:
            names = names + [RAW_LABEL]

        biases = [self._results[n]['metrics']['bias'] for n in names]
        sorted_pairs = sorted(zip(names, biases), key=lambda x: x[1])
        names_sorted = [p[0] for p in sorted_pairs]
        biases_sorted = [p[1] for p in sorted_pairs]

        colors = ['#27ae60' if b < 0.01 else '#f39c12' if b < 0.05 else '#c0392b'
                  for b in biases_sorted]

        fig, ax = plt.subplots(figsize=(15, 10))
        bars = ax.barh(range(len(names_sorted)), biases_sorted, color=colors,
                        height=0.65, edgecolor='white', linewidth=1.2)

        max_bias = max(biases_sorted) if biases_sorted else 1.0
        for bar, b in zip(bars, biases_sorted):
            ax.text(b + max_bias * 0.01, bar.get_y() + bar.get_height() / 2,
                     f'{b:.6f}', va='center', fontsize=9.5, fontweight='bold', color='#2c3e50')

        ax.set_yticks(range(len(names_sorted)))
        ax.set_yticklabels(names_sorted, fontsize=11)

        ax.set_xlabel('Bias (ε)', fontsize=13, fontweight='bold', labelpad=10)
        ax.set_title('Bias Comparison — All 20 Methods + Raw Data\n(Lower is Better)',
                     fontsize=16, fontweight='bold', pad=20)

        ax.axvline(x=0.0, color='black', linewidth=1)
        ax.grid(axis='x', linestyle='--', alpha=0.4)
        ax.invert_yaxis()

        legend_elements = [
            mpatches.Patch(color='#27ae60', label='Excellent (ε < 0.01)'),
            mpatches.Patch(color='#f39c12', label='Moderate (0.01 ≤ ε < 0.05)'),
            mpatches.Patch(color='#c0392b', label='High (ε ≥ 0.05)')
        ]
        ax.legend(handles=legend_elements, loc='lower right', fontsize=10)

        plt.tight_layout()
        plt.savefig(os.path.join(folder, "Bias_Comparison.png"), dpi=300, bbox_inches='tight')
        plt.close()

    # ---------- 5. NIST Compliance (stacked Pass/Fail/Invalid, sorted by pass count) ----------
    def generate_nist_graph(self, folder):
        names = self._extractor_names()
        if RAW_LABEL in self._results:
            names = names + [RAW_LABEL]

        comparison_data = []
        for n in names:
            nist = self._results[n]['nist']
            comparison_data.append({
                'method': n, 'pass': nist['pass'], 'fail': nist['fail'],
                'invalid': nist['invalid'], 'total': nist['total']
            })
        comparison_data.sort(key=lambda d: d['pass'], reverse=True)

        methods = [d['method'] for d in comparison_data]
        passes = [d['pass'] for d in comparison_data]
        fails = [d['fail'] for d in comparison_data]
        invalids = [d['invalid'] for d in comparison_data]
        max_total = max((d['total'] for d in comparison_data), default=16)

        fig, ax = plt.subplots(figsize=(15, 11))
        y_pos = range(len(methods))

        ax.barh(y_pos, passes, color='#27ae60', label='PASS', height=0.6)
        ax.barh(y_pos, fails, left=passes, color='#c0392b', label='FAIL', height=0.6)
        ax.barh(y_pos, invalids, left=[p + f for p, f in zip(passes, fails)],
                color='#95a5a6', label='Invalid', height=0.6)

        ax.set_yticks(y_pos)
        ax.set_yticklabels(methods, fontsize=10)
        ax.set_xlabel('Number of NIST Tests', fontsize=13, fontweight='bold')
        ax.set_title('NIST SP 800-22 Compliance — All 20 Methods + Raw Data',
                     fontsize=15, fontweight='bold', pad=20)

        ax.legend(loc='lower right', fontsize=11)
        ax.set_xlim(0, max_total + 1)
        ax.axvline(x=max_total, color='black', linestyle=':', linewidth=1.2, alpha=0.7)
        ax.grid(axis='x', alpha=0.3)
        ax.invert_yaxis()

        plt.tight_layout()
        plt.savefig(os.path.join(folder, "NIST_Compliance_Comparison.png"), dpi=300, bbox_inches='tight')
        plt.close()

    # ==================== Save Functions ====================
    def save_all_bits(self):
        if not self._results:
            messagebox.showwarning("No Results", "Run extraction first!")
            return
        folder = askdirectory(title="Select Folder to Save Extracted Bits")
        if not folder: return
        for name, data in self._results.items():
            clean = "".join(c if c.isalnum() else "_" for c in name)
            with open(os.path.join(folder, f"{clean}.txt"), "w") as f:
                f.write("".join(map(str, data['bits'])))
        messagebox.showinfo("Saved", f"Bits saved successfully in:\n{folder}")

    def save_graphs_only(self):
        if not self._results:
            messagebox.showwarning("No Results", "Run extraction first!")
            return
        folder = askdirectory(title="Select Folder to Save Graphs")
        if not folder: return
        try:
            self.generate_all_comparison_graphs(folder)
            messagebox.showinfo("Success", f"✅ All graphs saved in:\n{folder}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save graphs:\n{str(e)}")

    def select_all_extractors(self):
        for _, var in self._extractor_vars: var.set(1)
        self.on_checkbox_change()

    def deselect_all_extractors(self):
        for _, var in self._extractor_vars: var.set(0)
        self.on_checkbox_change()

    def reset(self):
        self.__binary_file_input.set_data('')
        self.__string_file_input.set_data('')
        for _, var in self._extractor_vars: var.set(0)
        self._results = {}
        self.status_label.config(text="Ready", foreground="black")
        self.progress['value'] = 0
        self._anim_running = False
        self._tick_shown = False
        self._anim_canvas.delete("all")

if __name__ == "__main__":
    root = Tk()
    app = QRNGExtractorSuite(root)
    app.pack()
    root.after(100, app.process_ui_queue)
    root.mainloop()