"use client";
import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useLenis } from 'lenis/react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine, Cell
} from 'recharts';
import { ChartData } from '@/lib/api';
import { TerminalCard } from '../TerminalCard';
import { Maximize2, X } from 'lucide-react';

interface ChartProps {
  data: ChartData[];
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white border border-quantum-light p-3 rounded-lg shadow-xl z-50 relative">
        <p className="font-sans font-bold text-quantum-navy mb-2">{label}</p>
        <div className="space-y-1">
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex items-center gap-2 font-sans font-semibold text-sm">
              <span className="w-3 h-3 rounded-full shadow-sm" style={{ backgroundColor: entry.color }}></span>
              <span className="text-quantum-blue">{entry.name}:</span>
              <span className="text-quantum-navy">{Number(entry.value).toLocaleString(undefined, { maximumFractionDigits: 4 })}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
};

const formatShortName = (name: string) => {
  let short = name.replace(/\u2013/g, '-').replace(/^\d+\.\s*/, '');
  short = short.replace(/Extractor|Extraction|Method|Hash|Matrix/ig, '').trim();
  if (short.includes('Leftover Hash Lemma')) return 'LHL';
  if (short.includes('Quantum-Proof Strong')) return 'Quantum';
  if (short.includes('Goldreich-Levin')) return 'Goldreich-L.';
  if (short.includes('Chor-Goldreich')) return 'Chor-G.';
  if (short.includes('Juels-Wattenberg')) return 'Juels-W.';
  if (short.includes('Hadamard')) return 'Hadamard';
  if (short.includes('Modular Arithmetic')) return 'Modular';
  if (short.includes('Toeplitz')) return 'Toeplitz';
  if (short.includes('Elias')) return 'Elias';
  if (short.includes('Bit-Shuffling')) return 'Bit-Shuffle';
  if (short.includes('Von Neumann')) return 'Von Neumann';
  if (short.includes('Arithmetic Coding')) return 'Arithmetic';
  if (short.includes('LFSR-Based')) return 'LFSR';
  if (short.includes('XOR-Summation')) return 'XOR-Sum';
  if (short.includes('Raw (Baseline)')) return 'Raw';
  if (short.length > 12) return short.substring(0, 10) + '...';
  return short;
};

// Bars animate in when a chart first appears, then animation is switched off:
// otherwise every resize (browser zoom, window size) replays it and the bars
// lag behind the axes for the length of the animation.
function useEntryAnimation(ms = 1200) {
  const [active, setActive] = useState(true);
  useEffect(() => {
    const timer = setTimeout(() => setActive(false), ms);
    return () => clearTimeout(timer);
  }, [ms]);
  return active;
}

function ChartWrapper({
  title, children, data, isNist = false, expanded, setExpanded, selectedMethod
}: {
  title: string, children: React.ReactNode, data: ChartData[], isNist?: boolean,
  expanded?: boolean, setExpanded?: (v: boolean) => void, selectedMethod?: string
}) {
  const [localExpanded, setLocalExpanded] = useState(false);
  const isExpanded = expanded !== undefined ? expanded : localExpanded;
  const handleExpand = (v: boolean) => setExpanded ? setExpanded(v) : setLocalExpanded(v);
  const lenis = useLenis();
  const detailListRef = useRef<HTMLDivElement>(null);
  const bodyRef = useRef<HTMLDivElement>(null);

  // While the modal is open the page behind must not move: pause the smooth
  // scroller (it turns every wheel event into page scroll) and lock the body.
  useEffect(() => {
    if (!isExpanded) return;
    lenis?.stop();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') handleExpand(false);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = previousOverflow;
      lenis?.start();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isExpanded, lenis]);

  // Bring the clicked method into view by scrolling the list itself;
  // scrollIntoView would also scroll the page behind the modal.
  useEffect(() => {
    if (!isExpanded || !selectedMethod) return;
    const timer = setTimeout(() => {
      const el = document.getElementById(`nist-detail-${selectedMethod}`);
      const list = detailListRef.current;
      if (!el || !list) return;
      // Side by side the list scrolls; stacked, the modal body does.
      const scroller = list.scrollHeight > list.clientHeight ? list : bodyRef.current;
      if (!scroller) return;
      const top = el.getBoundingClientRect().top - scroller.getBoundingClientRect().top + scroller.scrollTop;
      scroller.scrollTo({ top: top - 8, behavior: 'smooth' });
    }, 100);
    return () => clearTimeout(timer);
  }, [isExpanded, selectedMethod]);

  return (
    <>
      <TerminalCard title={title} className="h-96 relative group">
        <div
          onClick={() => handleExpand(true)}
          className="relative w-full h-full cursor-pointer overflow-x-auto overflow-y-hidden [&_.recharts-wrapper]:!outline-none [&_.recharts-surface]:!outline-none [&_*]:focus:!outline-none"
          title="Click to expand chart"
        >
          <div className="absolute inset-0 min-w-[440px] pb-4">
            {children}
          </div>
        </div>
      </TerminalCard>

      {/* Portalled to <body> so no transformed/filtered ancestor can clip or
          offset the fixed overlay. Sized from the viewport, so it follows any
          browser zoom level; the chart fills whatever space is left. */}
      {isExpanded && createPortal(
        <div
          data-lenis-prevent
          onClick={() => handleExpand(false)}
          className="fixed inset-0 z-[100] flex items-center justify-center p-[3vmin] bg-quantum-navy/80 backdrop-blur-sm animate-in fade-in duration-200"
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label={title}
            onClick={(e) => e.stopPropagation()}
            className="bg-white w-[94vw] h-[88dvh] max-w-full max-h-full rounded-xl shadow-2xl flex flex-col border border-quantum-light overflow-hidden animate-in zoom-in-95 duration-200"
          >
            <div className="flex-shrink-0 flex justify-between items-center gap-4 px-4 py-3 sm:px-6 border-b border-quantum-light bg-quantum-light/10">
              <h2 className="text-lg sm:text-xl font-bold text-quantum-navy truncate">{title}</h2>
              <button
                onClick={() => handleExpand(false)}
                aria-label="Close"
                className="flex-shrink-0 p-2 text-quantum-navy/60 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Wide viewports: chart and details side by side, the details list
                scrolls on its own. Narrow or short viewports (e.g. zoomed in):
                they stack and this body becomes the single scroll area, so the
                chart never shrinks below a legible size. */}
            <div ref={bodyRef} className="flex-1 min-h-0 overflow-auto overscroll-contain p-3 sm:p-6">
              <div className="flex flex-col lg:flex-row gap-4 lg:gap-6 min-h-full lg:h-full lg:min-h-[300px]">
                <div className={`relative min-w-0 overflow-x-auto overflow-y-hidden ${isNist ? 'flex-shrink-0 h-[max(300px,42dvh)] lg:h-auto lg:flex-1 lg:flex-shrink' : 'flex-1 min-h-[300px]'}`}>
                  <div className="absolute inset-0 min-w-[440px]">
                    {children}
                  </div>
                </div>

              {isNist && data.length > 0 && (
                <div className="lg:w-80 xl:w-96 lg:flex-shrink-0 lg:min-h-0 flex flex-col gap-3">
                  <h3 className="flex-shrink-0 font-bold text-quantum-navy border-b border-quantum-light pb-2">Detailed NIST Results</h3>
                  <div
                    ref={detailListRef}
                    className="lg:flex-1 lg:min-h-0 lg:overflow-y-auto overscroll-contain lg:pr-2 space-y-4"
                  >
                    {data.map((d, i) => (
                      <div id={`nist-detail-${d.method}`} key={i} className={`p-3 rounded-lg border transition-colors duration-500 ${selectedMethod === d.method ? 'bg-quantum-blue/10 border-quantum-blue shadow-sm' : 'bg-quantum-light/5 border-quantum-light'}`}>
                        <p className="font-bold text-sm text-quantum-blue mb-2">{d.method}</p>
                        <div className="space-y-1.5">
                          {d.details && d.details.length > 0 ? d.details.map((test, j) => (
                              <div key={j} className="flex flex-col py-1 border-b border-quantum-light/30 last:border-0">
                                <div className="flex justify-between text-xs items-center gap-2">
                                  <span className="text-quantum-navy/80 truncate font-medium">{test.name}</span>
                                  <span className={`flex-shrink-0 font-bold px-1.5 py-0.5 rounded text-[10px] uppercase ${
                                    test.status === 'pass' ? 'bg-[#27ae60]/10 text-[#27ae60]' :
                                    test.status === 'fail' ? 'bg-[#c0392b]/10 text-[#c0392b]' :
                                    'bg-[#95a5a6]/10 text-[#95a5a6]'
                                  }`}>
                                    {test.status === 'invalid' ? 'Insufficient data' : test.status}
                                  </span>
                                </div>
                                {typeof test.pValue === 'number' && !Number.isNaN(test.pValue) && test.status !== 'invalid' && (
                                  <div className="text-[10px] text-quantum-navy/60 font-mono mt-0.5 pl-1">
                                    p-value: {test.pValue < 0.0001 ? '< 0.0001' : test.pValue.toFixed(4)}
                                  </div>
                                )}
                              </div>
                          )) : (
                            <p className="text-xs text-quantum-navy/50 italic">No details available</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  );
}

export function EntropyChart({ data }: ChartProps) {
  const animate = useEntryAnimation();
  return (
    <ChartWrapper title="Entropy Comparison" data={data}>
      <ResponsiveContainer width="99%" height="100%">
        <BarChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 45 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#90E0EF" vertical={false} opacity={0.5} />
          <XAxis dataKey="method" stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 10, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} interval={0} angle={-45} textAnchor="end" height={45} tickFormatter={formatShortName} />
          <YAxis stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 12, fontFamily: 'var(--font-sans)', fontWeight: 600 }} domain={[0, 1.1]} axisLine={false} tickLine={false} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: '#CAF0F8', opacity: 0.5 }} />
          <Legend wrapperStyle={{ fontSize: 13, paddingTop: '10px', fontWeight: 600, color: '#03045E' }} iconType="circle" />
          <ReferenceLine y={1.0} stroke="#03045E" strokeDasharray="4 4" label={{ position: 'top', value: 'Ideal (1.0)', fill: '#03045E', fontSize: 12, fontWeight: 'bold' }} />
          <Bar isAnimationActive={animate} dataKey="shannonEntropy" name="Shannon Entropy" fill="#00B4D8" radius={[4, 4, 0, 0]} animationBegin={0} animationDuration={800} />
          <Bar isAnimationActive={animate} dataKey="minEntropy" name="Min-Entropy" fill="#0077B6" radius={[4, 4, 0, 0]} animationBegin={200} animationDuration={800} />
        </BarChart>
      </ResponsiveContainer>
    </ChartWrapper>
  );
}

const RAW_METHOD = 'Raw (Baseline)';

export function BitRateChart({ data }: ChartProps) {
  const animate = useEntryAnimation();
  const extracted = data.filter(d => d.method !== RAW_METHOD).map(d => ({ ...d, mbps: (d.bitRate || 0) / 1e6 }));
  return (
    <ChartWrapper title="Throughput (Megabits Per Second)" data={extracted}>
      <ResponsiveContainer width="99%" height="100%">
        <BarChart data={extracted} margin={{ top: 20, right: 30, left: 10, bottom: 45 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#90E0EF" vertical={false} opacity={0.5} />
          <XAxis dataKey="method" stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 10, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} interval={0} angle={-45} textAnchor="end" height={45} tickFormatter={formatShortName} />
          <YAxis stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 12, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} tickFormatter={(val) => Number(val).toLocaleString(undefined, { maximumFractionDigits: 1 })} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: '#CAF0F8', opacity: 0.5 }} />
          <Bar isAnimationActive={animate} dataKey="mbps" name="Throughput (Mbps)" fill="#00B4D8"radius={[4, 4, 0, 0]} animationBegin={0} animationDuration={800} />
        </BarChart>
      </ResponsiveContainer>
    </ChartWrapper>
  );
}

export function BiasChart({ data }: ChartProps) {
  const animate = useEntryAnimation();
  const getColor = (value: number) => {
    if (value < 0.05) return '#0077B6'; 
    if (value < 0.1) return '#00B4D8'; 
    return '#03045E'; 
  };

  return (
    <ChartWrapper title="Bias Level" data={data}>
      <ResponsiveContainer width="99%" height="100%">
        <BarChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 45 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#90E0EF" vertical={false} opacity={0.5} />
          <XAxis dataKey="method" stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 10, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} interval={0} angle={-45} textAnchor="end" height={45} tickFormatter={formatShortName} />
          <YAxis stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 12, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: '#CAF0F8', opacity: 0.5 }} />
          <Bar isAnimationActive={animate} dataKey="bias" name="Bias (Lower is better)" radius={[4, 4, 0, 0]} animationBegin={0} animationDuration={800}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getColor(entry.bias || 0)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartWrapper>
  );
}

export function NistComplianceChart({ data }: ChartProps) {
  const animate = useEntryAnimation();
  const [expanded, setExpanded] = useState(false);
  const [selectedMethod, setSelectedMethod] = useState<string | undefined>();

  const handleBarClick = (barData: any) => {
    if (barData && barData.method) {
      setSelectedMethod(barData.method);
      setExpanded(true);
    }
  };

  return (
    <ChartWrapper 
      title="NIST SP 800-22 Pass Rate" 
      data={data} 
      isNist={true}
      expanded={expanded}
      setExpanded={setExpanded}
      selectedMethod={selectedMethod}
    >
      <ResponsiveContainer width="99%" height="100%">
        <BarChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 45 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#90E0EF" vertical={false} opacity={0.5} />
          <XAxis dataKey="method" stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 10, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} interval={0} angle={-45} textAnchor="end" height={45} tickFormatter={formatShortName} />
          <YAxis stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 12, fontFamily: 'var(--font-sans)', fontWeight: 600 }} domain={[0, 16]} axisLine={false} tickLine={false} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: '#CAF0F8', opacity: 0.5 }} />
          <Legend wrapperStyle={{ fontSize: 13, paddingTop: '10px', fontWeight: 600, color: '#03045E' }} iconType="circle" />
          <Bar isAnimationActive={animate} onClick={handleBarClick} dataKey="passCount" name="Pass" stackId="a" fill="#0077B6" radius={[0, 0, 4, 4]} animationBegin={0} animationDuration={800} cursor="pointer" />
          <Bar isAnimationActive={animate} onClick={handleBarClick} dataKey="failCount" name="Fail" stackId="a" fill="#c0392b" animationBegin={0} animationDuration={800} cursor="pointer" />
          <Bar isAnimationActive={animate} onClick={handleBarClick} dataKey="invalidCount" name="Insufficient data" stackId="a" fill="#95a5a6" radius={[4, 4, 0, 0]} animationBegin={0} animationDuration={800} cursor="pointer" />
        </BarChart>
      </ResponsiveContainer>
    </ChartWrapper>
  );
}

export function EfficiencyChart({ data }: ChartProps) {
  const animate = useEntryAnimation();
  const processedData = data.filter(d => d.method !== RAW_METHOD).map(d => ({
    ...d,
    executionTime: Math.max(d.executionTime || 0.1, 0.1)
  }));
  const sortedData = [...processedData].sort((a, b) => a.executionTime - b.executionTime);

  return (
    <ChartWrapper title="Computational Efficiency (ms)" data={sortedData}>
      <ResponsiveContainer width="99%" height="100%">
        <BarChart data={sortedData} margin={{ top: 20, right: 30, left: 10, bottom: 45 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#90E0EF" vertical={false} opacity={0.5} />
          <XAxis dataKey="method" stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 10, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} interval={0} angle={-45} textAnchor="end" height={45} tickFormatter={formatShortName} />
          <YAxis stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 12, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} tickFormatter={(val) => (val < 1 ? val.toFixed(1) : Math.round(val)) + 'ms'} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: '#CAF0F8', opacity: 0.5 }} />
          <Bar isAnimationActive={animate} dataKey="executionTime" name="Execution Time (Lower is Better)" fill="#9b59b6" radius={[4, 4, 0, 0]} animationBegin={0} animationDuration={800} />
        </BarChart>
      </ResponsiveContainer>
    </ChartWrapper>
  );
}

export function CompressionChart({ data }: ChartProps) {
  const animate = useEntryAnimation();
  const processedData = data.map(d => {
    const isInvalid = d.compression?.invalid || (d.compression?.pass_count === 0 && d.compression?.overall_status === 'FAIL' && !d.compression?.algorithms?.length);
    return {
      method: d.method,
      pass: isInvalid ? 0 : d.compression?.pass_count || 0,
      fail: isInvalid ? 0 : 4 - (d.compression?.pass_count || 0),
      invalid: isInvalid ? 4 : 0
    };
  });
  const sortedData = [...processedData].sort((a, b) => {
    if (a.invalid !== b.invalid) return a.invalid - b.invalid;
    return a.pass - b.pass;
  });

  return (
    <ChartWrapper title="Compression Tests (4 Algorithms)" data={sortedData as any}>
      <ResponsiveContainer width="99%" height="100%">
        <BarChart data={sortedData} margin={{ top: 20, right: 30, left: 0, bottom: 45 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#90E0EF" vertical={false} opacity={0.5} />
          <XAxis dataKey="method" stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 10, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} interval={0} angle={-45} textAnchor="end" height={45} tickFormatter={formatShortName} />
          <YAxis stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 12, fontFamily: 'var(--font-sans)', fontWeight: 600 }} domain={[0, 4]} axisLine={false} tickLine={false} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: '#CAF0F8', opacity: 0.5 }} />
          <Legend wrapperStyle={{ fontSize: 13, paddingTop: '10px', fontWeight: 600, color: '#03045E' }} iconType="circle" />
          <Bar isAnimationActive={animate} dataKey="pass" name="Pass (>= 0.999 ratio)" stackId="a" fill="#0077B6" radius={[0, 0, 4, 4]} animationBegin={0} animationDuration={800} />
          <Bar isAnimationActive={animate} dataKey="fail" name="Fail" stackId="a" fill="#c0392b" radius={[4, 4, 0, 0]} animationBegin={0} animationDuration={800} />
          <Bar isAnimationActive={animate} dataKey="invalid" name="Insufficient Data" stackId="a" fill="#95a5a6" radius={[4, 4, 0, 0]} animationBegin={0} animationDuration={800} />
        </BarChart>
      </ResponsiveContainer>
    </ChartWrapper>
  );
}

export function TestU01Chart({ data }: ChartProps) {
  const animate = useEntryAnimation();
  // Placeholder bar height for inputs with no result: the largest real test count.
  const maxTotal = Math.max(1, ...data.map(d => (d.testu01?.error ? 0 : d.testu01?.total || 0)));
  const processedData = data.map(d => {
    const isInvalid = d.testu01?.error || !d.testu01?.total;
    return {
      method: d.method,
      pass: isInvalid ? 0 : d.testu01?.pass || 0,
      weak: isInvalid ? 0 : d.testu01?.weak || 0,
      fail: isInvalid ? 0 : d.testu01?.fail || 0,
      invalid: isInvalid ? maxTotal : 0,
      total: isInvalid ? maxTotal : d.testu01?.total
    };
  });
  const sortedData = [...processedData].sort((a, b) => {
    if (a.invalid !== b.invalid) return a.invalid - b.invalid;
    return a.pass - b.pass;
  });

  return (
    <ChartWrapper title="TestU01 (Alphabit + Rabbit)" data={sortedData as any}>
      <ResponsiveContainer width="99%" height="100%">
        <BarChart data={sortedData} margin={{ top: 20, right: 30, left: 0, bottom: 45 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#90E0EF" vertical={false} opacity={0.5} />
          <XAxis dataKey="method" stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 10, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} interval={0} angle={-45} textAnchor="end" height={45} tickFormatter={formatShortName} />
          <YAxis stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 12, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: '#CAF0F8', opacity: 0.5 }} />
          <Legend wrapperStyle={{ fontSize: 13, paddingTop: '10px', fontWeight: 600, color: '#03045E' }} iconType="circle" />
          <Bar isAnimationActive={animate} dataKey="pass" name="Pass" stackId="a" fill="#0077B6" radius={[0, 0, 4, 4]} animationBegin={0} animationDuration={800} />
          <Bar isAnimationActive={animate} dataKey="weak" name="Suspect" stackId="a" fill="#F39C12" radius={[0, 0, 0, 0]} animationBegin={0} animationDuration={800} />
          <Bar isAnimationActive={animate} dataKey="fail" name="Fail" stackId="a" fill="#c0392b" radius={[4, 4, 0, 0]} animationBegin={0} animationDuration={800} />
          <Bar isAnimationActive={animate} dataKey="invalid" name="Insufficient Data / Unavailable" stackId="a" fill="#95a5a6" radius={[4, 4, 0, 0]} animationBegin={0} animationDuration={800} />
        </BarChart>
      </ResponsiveContainer>
    </ChartWrapper>
  );
}

export function DieharderChart({ data }: ChartProps) {
  const animate = useEntryAnimation();
  // Tests Dieharder could not run without reusing (rewinding) the input count as insufficient.
  const processedData = data.map(d => {
    const dh = d.dieharder || {};
    const skipped = dh.insufficient_tests?.length || 0;
    const hasResults = !dh.error && !!dh.total;
    return {
      method: d.method,
      pass: hasResults ? dh.pass || 0 : 0,
      weak: hasResults ? dh.weak || 0 : 0,
      fail: hasResults ? dh.fail || 0 : 0,
      invalid: hasResults ? skipped : Math.max(skipped, 1),
      total: (hasResults ? dh.total : 0) + skipped
    };
  });
  const sortedData = [...processedData].sort((a, b) => {
    if (a.invalid !== b.invalid) return a.invalid - b.invalid;
    return a.pass - b.pass;
  });

  return (
    <ChartWrapper title="Dieharder Suite" data={sortedData as any}>
      <ResponsiveContainer width="99%" height="100%">
        <BarChart data={sortedData} margin={{ top: 20, right: 30, left: 0, bottom: 45 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#90E0EF" vertical={false} opacity={0.5} />
          <XAxis dataKey="method" stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 10, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} interval={0} angle={-45} textAnchor="end" height={45} tickFormatter={formatShortName} />
          <YAxis stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 12, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: '#CAF0F8', opacity: 0.5 }} />
          <Legend wrapperStyle={{ fontSize: 13, paddingTop: '10px', fontWeight: 600, color: '#03045E' }} iconType="circle" />
          <Bar isAnimationActive={animate} dataKey="pass" name="Pass" stackId="a" fill="#0077B6" radius={[0, 0, 0, 0]} animationBegin={0} animationDuration={800} />
          <Bar isAnimationActive={animate} dataKey="weak" name="Weak" stackId="a" fill="#F39C12" radius={[0, 0, 0, 0]} animationBegin={0} animationDuration={800} />
          <Bar isAnimationActive={animate} dataKey="fail" name="Fail" stackId="a" fill="#c0392b" radius={[0, 0, 0, 0]} animationBegin={0} animationDuration={800} />
          <Bar isAnimationActive={animate} dataKey="invalid" name="Insufficient Data / Unavailable" stackId="a" fill="#95a5a6" radius={[4, 4, 0, 0]} animationBegin={0} animationDuration={800} />
        </BarChart>
      </ResponsiveContainer>
    </ChartWrapper>
  );
}
