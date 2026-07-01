"use client";
import React, { useState } from 'react';
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
  let short = name.replace(/^\d+\.\s*/, '');
  short = short.replace(/Extractor|Extraction|Method|Hash|Matrix/ig, '').trim();
  if (short.includes('Leftover Hash Lemma')) return 'LHL';
  if (short.includes('Quantum-Proof Strong')) return 'Quantum';
  if (short.includes('Goldreich-Levin')) return 'Goldreich-L.';
  if (short.includes('Chor-Goldreich')) return 'Chor-G.';
  if (short.includes('Von Neumann')) return 'Von Neumann';
  if (short.includes('Arithmetic Coding')) return 'Arithmetic';
  if (short.includes('LFSR-Based')) return 'LFSR';
  if (short.includes('XOR-Summation')) return 'XOR-Sum';
  if (short.includes('Raw (Baseline)')) return 'Raw';
  if (short.length > 12) return short.substring(0, 10) + '...';
  return short;
};

function ChartWrapper({ 
  title, children, data, isNist = false, expanded, setExpanded, selectedMethod 
}: { 
  title: string, children: React.ReactNode, data: ChartData[], isNist?: boolean,
  expanded?: boolean, setExpanded?: (v: boolean) => void, selectedMethod?: string
}) {
  const [localExpanded, setLocalExpanded] = useState(false);
  const isExpanded = expanded !== undefined ? expanded : localExpanded;
  const handleExpand = (v: boolean) => setExpanded ? setExpanded(v) : setLocalExpanded(v);

  React.useEffect(() => {
    if (isExpanded && selectedMethod) {
      setTimeout(() => {
        const el = document.getElementById(`nist-detail-${selectedMethod}`);
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    }
  }, [isExpanded, selectedMethod]);

  return (
    <>
      <TerminalCard title={title} className="h-96 relative group">
        <div 
          onClick={() => handleExpand(true)}
          className="w-full h-full pb-4 cursor-pointer [&_.recharts-wrapper]:!outline-none [&_.recharts-surface]:!outline-none [&_*]:focus:!outline-none"
          title="Click to expand chart"
        >
          {children}
        </div>
      </TerminalCard>

      {isExpanded && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-8 bg-quantum-navy/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white w-full max-w-6xl h-[80vh] rounded-xl shadow-2xl flex flex-col border border-quantum-light overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="flex justify-between items-center p-4 border-b border-quantum-light bg-quantum-light/10">
              <h2 className="text-xl font-bold text-quantum-navy">{title}</h2>
              <button 
                onClick={() => handleExpand(false)}
                className="p-2 text-quantum-navy/60 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="flex-1 p-6 min-h-0 flex flex-col lg:flex-row gap-6 overflow-auto">
              <div className="flex-1 min-h-[400px]">
                {children}
              </div>
              
              {isNist && data.length > 0 && (
                <div className="w-full lg:w-80 flex-shrink-0 flex flex-col gap-4">
                  <h3 className="font-bold text-quantum-navy border-b border-quantum-light pb-2">Detailed NIST Results</h3>
                  <div className="overflow-y-auto pr-2 space-y-4">
                    {data.map((d, i) => (
                      <div id={`nist-detail-${d.method}`} key={i} className={`p-3 rounded-lg border transition-colors duration-500 ${selectedMethod === d.method ? 'bg-quantum-blue/10 border-quantum-blue shadow-sm' : 'bg-quantum-light/5 border-quantum-light'}`}>
                        <p className="font-bold text-sm text-quantum-blue mb-2">{d.method}</p>
                        <div className="space-y-1.5">
                          {d.details && d.details.length > 0 ? d.details.map((test, j) => (
                            <div key={j} className="flex justify-between text-xs items-center">
                              <span className="text-quantum-navy/80 truncate pr-2">{test.name}</span>
                              <span className={`font-bold px-1.5 py-0.5 rounded text-[10px] uppercase ${
                                test.status === 'pass' ? 'bg-[#27ae60]/10 text-[#27ae60]' : 
                                test.status === 'fail' ? 'bg-[#c0392b]/10 text-[#c0392b]' : 
                                'bg-[#95a5a6]/10 text-[#95a5a6]'
                              }`}>
                                {test.status === 'invalid' ? 'Insufficient data' : test.status}
                              </span>
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
      )}
    </>
  );
}

export function EntropyChart({ data }: ChartProps) {
  return (
    <ChartWrapper title="Entropy Comparison" data={data}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 45 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#90E0EF" vertical={false} opacity={0.5} />
          <XAxis dataKey="method" stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 10, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} interval={0} angle={-45} textAnchor="end" height={45} tickFormatter={formatShortName} />
          <YAxis stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 12, fontFamily: 'var(--font-sans)', fontWeight: 600 }} domain={[0, 1.1]} axisLine={false} tickLine={false} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: '#CAF0F8', opacity: 0.5 }} />
          <Legend wrapperStyle={{ fontSize: 13, paddingTop: '10px', fontWeight: 600, color: '#03045E' }} iconType="circle" />
          <ReferenceLine y={1.0} stroke="#03045E" strokeDasharray="4 4" label={{ position: 'top', value: 'Ideal (1.0)', fill: '#03045E', fontSize: 12, fontWeight: 'bold' }} />
          <Bar dataKey="shannonEntropy" name="Shannon Entropy" fill="#00B4D8" radius={[4, 4, 0, 0]} animationBegin={0} animationDuration={800} />
          <Bar dataKey="minEntropy" name="Min-Entropy" fill="#0077B6" radius={[4, 4, 0, 0]} animationBegin={200} animationDuration={800} />
        </BarChart>
      </ResponsiveContainer>
    </ChartWrapper>
  );
}

export function BitRateChart({ data }: ChartProps) {
  return (
    <ChartWrapper title="Throughput (Bits Per Second)" data={data}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 20, right: 30, left: 10, bottom: 45 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#90E0EF" vertical={false} opacity={0.5} />
          <XAxis dataKey="method" stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 10, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} interval={0} angle={-45} textAnchor="end" height={45} tickFormatter={formatShortName} />
          <YAxis stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 12, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} tickFormatter={(val) => (val/1000) + 'k'} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: '#CAF0F8', opacity: 0.5 }} />
          <Bar dataKey="bitRate" name="Bit Rate (bps)" fill="#00B4D8" radius={[4, 4, 0, 0]} animationBegin={0} animationDuration={800} />
        </BarChart>
      </ResponsiveContainer>
    </ChartWrapper>
  );
}

export function BiasChart({ data }: ChartProps) {
  const getColor = (value: number) => {
    if (value < 0.05) return '#0077B6'; 
    if (value < 0.1) return '#00B4D8'; 
    return '#03045E'; 
  };

  return (
    <ChartWrapper title="Bias Level" data={data}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 45 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#90E0EF" vertical={false} opacity={0.5} />
          <XAxis dataKey="method" stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 10, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} interval={0} angle={-45} textAnchor="end" height={45} tickFormatter={formatShortName} />
          <YAxis stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 12, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: '#CAF0F8', opacity: 0.5 }} />
          <Bar dataKey="bias" name="Bias (Lower is better)" radius={[4, 4, 0, 0]} animationBegin={0} animationDuration={800}>
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
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 45 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#90E0EF" vertical={false} opacity={0.5} />
          <XAxis dataKey="method" stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 10, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} interval={0} angle={-45} textAnchor="end" height={45} tickFormatter={formatShortName} />
          <YAxis stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 12, fontFamily: 'var(--font-sans)', fontWeight: 600 }} domain={[0, 16]} axisLine={false} tickLine={false} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: '#CAF0F8', opacity: 0.5 }} />
          <Legend wrapperStyle={{ fontSize: 13, paddingTop: '10px', fontWeight: 600, color: '#03045E' }} iconType="circle" />
          <Bar onClick={handleBarClick} dataKey="passCount" name="Pass" stackId="a" fill="#0077B6" radius={[0, 0, 4, 4]} animationBegin={0} animationDuration={800} cursor="pointer" />
          <Bar onClick={handleBarClick} dataKey="failCount" name="Fail" stackId="a" fill="#c0392b" animationBegin={0} animationDuration={800} cursor="pointer" />
          <Bar onClick={handleBarClick} dataKey="invalidCount" name="Insufficient data" stackId="a" fill="#95a5a6" radius={[4, 4, 0, 0]} animationBegin={0} animationDuration={800} cursor="pointer" />
        </BarChart>
      </ResponsiveContainer>
    </ChartWrapper>
  );
}

export function EfficiencyChart({ data }: ChartProps) {
  const processedData = data.map(d => ({
    ...d,
    executionTime: Math.max(d.executionTime || 0.1, 0.1)
  }));
  const sortedData = [...processedData].sort((a, b) => a.executionTime - b.executionTime);

  return (
    <ChartWrapper title="Computational Efficiency (ms)" data={sortedData}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={sortedData} margin={{ top: 20, right: 30, left: 10, bottom: 45 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#90E0EF" vertical={false} opacity={0.5} />
          <XAxis dataKey="method" stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 10, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} interval={0} angle={-45} textAnchor="end" height={45} tickFormatter={formatShortName} />
          <YAxis stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 12, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} tickFormatter={(val) => (val < 1 ? val.toFixed(1) : Math.round(val)) + 'ms'} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: '#CAF0F8', opacity: 0.5 }} />
          <Bar dataKey="executionTime" name="Execution Time (Lower is Better)" fill="#9b59b6" radius={[4, 4, 0, 0]} animationBegin={0} animationDuration={800} />
        </BarChart>
      </ResponsiveContainer>
    </ChartWrapper>
  );
}

export function CompressionChart({ data }: ChartProps) {
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
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={sortedData} margin={{ top: 20, right: 30, left: 0, bottom: 45 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#90E0EF" vertical={false} opacity={0.5} />
          <XAxis dataKey="method" stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 10, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} interval={0} angle={-45} textAnchor="end" height={45} tickFormatter={formatShortName} />
          <YAxis stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 12, fontFamily: 'var(--font-sans)', fontWeight: 600 }} domain={[0, 4]} axisLine={false} tickLine={false} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: '#CAF0F8', opacity: 0.5 }} />
          <Legend wrapperStyle={{ fontSize: 13, paddingTop: '10px', fontWeight: 600, color: '#03045E' }} iconType="circle" />
          <Bar dataKey="pass" name="Pass (>= 0.999 ratio)" stackId="a" fill="#0077B6" radius={[0, 0, 4, 4]} animationBegin={0} animationDuration={800} />
          <Bar dataKey="fail" name="Fail" stackId="a" fill="#c0392b" radius={[4, 4, 0, 0]} animationBegin={0} animationDuration={800} />
          <Bar dataKey="invalid" name="Insufficient Data" stackId="a" fill="#95a5a6" radius={[4, 4, 0, 0]} animationBegin={0} animationDuration={800} />
        </BarChart>
      </ResponsiveContainer>
    </ChartWrapper>
  );
}

export function TestU01Chart({ data }: ChartProps) {
  const processedData = data.map(d => {
    const isInvalid = d.testu01?.error || (!d.testu01?.pass && !d.testu01?.fail);
    return {
      method: d.method,
      pass: isInvalid ? 0 : d.testu01?.pass || 0,
      fail: isInvalid ? 0 : d.testu01?.fail || 0,
      invalid: isInvalid ? 15 : 0,
      total: 15
    };
  });
  const sortedData = [...processedData].sort((a, b) => {
    if (a.invalid !== b.invalid) return a.invalid - b.invalid;
    return a.pass - b.pass;
  });

  return (
    <ChartWrapper title="TestU01 SmallCrush" data={sortedData as any}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={sortedData} margin={{ top: 20, right: 30, left: 0, bottom: 45 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#90E0EF" vertical={false} opacity={0.5} />
          <XAxis dataKey="method" stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 10, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} interval={0} angle={-45} textAnchor="end" height={45} tickFormatter={formatShortName} />
          <YAxis stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 12, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: '#CAF0F8', opacity: 0.5 }} />
          <Legend wrapperStyle={{ fontSize: 13, paddingTop: '10px', fontWeight: 600, color: '#03045E' }} iconType="circle" />
          <Bar dataKey="pass" name="Pass" stackId="a" fill="#0077B6" radius={[0, 0, 4, 4]} animationBegin={0} animationDuration={800} />
          <Bar dataKey="fail" name="Fail" stackId="a" fill="#c0392b" radius={[4, 4, 0, 0]} animationBegin={0} animationDuration={800} />
          <Bar dataKey="invalid" name="Unavailable / Missing Lib" stackId="a" fill="#95a5a6" radius={[4, 4, 0, 0]} animationBegin={0} animationDuration={800} />
        </BarChart>
      </ResponsiveContainer>
    </ChartWrapper>
  );
}

export function DieharderChart({ data }: ChartProps) {
  const processedData = data.map(d => {
    const isInvalid = d.dieharder?.error || d.dieharder?.insufficient || (!d.dieharder?.pass && !d.dieharder?.fail && !d.dieharder?.weak);
    return {
      method: d.method,
      pass: isInvalid ? 0 : d.dieharder?.pass || 0,
      weak: isInvalid ? 0 : d.dieharder?.weak || 0,
      fail: isInvalid ? 0 : d.dieharder?.fail || 0,
      invalid: isInvalid ? 100 : 0,
      total: 100
    };
  });
  const sortedData = [...processedData].sort((a, b) => {
    if (a.invalid !== b.invalid) return a.invalid - b.invalid;
    return a.pass - b.pass;
  });

  return (
    <ChartWrapper title="Dieharder Suite" data={sortedData as any}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={sortedData} margin={{ top: 20, right: 30, left: 0, bottom: 45 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#90E0EF" vertical={false} opacity={0.5} />
          <XAxis dataKey="method" stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 10, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} interval={0} angle={-45} textAnchor="end" height={45} tickFormatter={formatShortName} />
          <YAxis stroke="#0077B6" tick={{ fill: '#0077B6', fontSize: 12, fontFamily: 'var(--font-sans)', fontWeight: 600 }} axisLine={false} tickLine={false} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: '#CAF0F8', opacity: 0.5 }} />
          <Legend wrapperStyle={{ fontSize: 13, paddingTop: '10px', fontWeight: 600, color: '#03045E' }} iconType="circle" />
          <Bar dataKey="pass" name="Pass" stackId="a" fill="#0077B6" radius={[0, 0, 0, 0]} animationBegin={0} animationDuration={800} />
          <Bar dataKey="weak" name="Weak" stackId="a" fill="#F39C12" radius={[0, 0, 0, 0]} animationBegin={0} animationDuration={800} />
          <Bar dataKey="fail" name="Fail" stackId="a" fill="#c0392b" radius={[0, 0, 0, 0]} animationBegin={0} animationDuration={800} />
          <Bar dataKey="invalid" name="Insufficient Data / Unavailable" stackId="a" fill="#95a5a6" radius={[4, 4, 0, 0]} animationBegin={0} animationDuration={800} />
        </BarChart>
      </ResponsiveContainer>
    </ChartWrapper>
  );
}
