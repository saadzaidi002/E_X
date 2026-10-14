"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { TerminalCard } from '@/components/TerminalCard';
import { TerminalButton } from '@/components/TerminalButton';
import { getMethods, getLimits, analyzeFile, downloadBitsZip, downloadPdfReport, Method, Limits, AnalysisResult, UploadProgress, RankedMethod } from '@/lib/api';
import { EntropyChart, BitRateChart, BiasChart, NistComplianceChart, EfficiencyChart, CompressionChart, TestU01Chart, DieharderChart } from '@/components/charts/ComparisonCharts';
import { Upload, Play, Download, FileText, Check, AlertTriangle, Loader2, Binary, CheckCircle2 } from 'lucide-react';
import { useAnalysis } from '@/lib/AnalysisContext';

function formatDuration(seconds: number) {
  if (!Number.isFinite(seconds) || seconds < 0) return '';
  if (seconds < 60) return `${Math.max(1, Math.round(seconds))} s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return s ? `${m} min ${s} s` : `${m} min`;
}

// Baseline first (not ranked), then ranked methods, then methods excluded for
// producing too little output to be tested like the others.
function rankingRows(result: AnalysisResult) {
  const rows: { m: RankedMethod; rank: number; kind: 'baseline' | 'ranked' | 'excluded' }[] = [];
  if (result.baseline) rows.push({ m: result.baseline, rank: 0, kind: 'baseline' });
  let rank = 0;
  for (const m of result.rankedMethods) {
    if (m.excluded) rows.push({ m, rank: 0, kind: 'excluded' });
    else rows.push({ m, rank: ++rank, kind: 'ranked' });
  }
  return rows;
}

type RowKind = 'baseline' | 'ranked' | 'excluded';
type RankingColumn = {
  key: string;
  label: string;
  weight: number; // share of the table width
  align?: 'left' | 'right';
  cell: (m: RankedMethod, kind: RowKind) => React.ReactNode;
};

const muted = (text: string) => <span className="font-semibold text-quantum-navy/50">{text}</span>;

function rankingColumns(selectedTests: Set<string>): RankingColumn[] {
  const notTested = muted('not tested');
  const cols: RankingColumn[] = [];
  if (selectedTests.has('nist')) cols.push({
    key: 'nist', label: 'NIST', weight: 8,
    cell: m => <>{m.nistPass}/{m.nistTotal ?? 16}{!!m.nistNa && <span className="block">{muted(`${m.nistNa} n/a`)}</span>}</>,
  });
  if (selectedTests.has('compression')) cols.push({ key: 'comp', label: 'Compress', weight: 7, cell: m => `${m.compressionPass ?? 0}/4` });
  if (selectedTests.has('testu01')) cols.push({
    key: 'u01', label: 'TestU01', weight: 7,
    cell: m => m.excluded ? notTested : m.testu01Total ? `${m.testu01Pass ?? 0}/${m.testu01Total}` : 'n/a',
  });
  if (selectedTests.has('dieharder')) cols.push({
    key: 'die', label: 'Dieharder', weight: 11,
    cell: m => m.excluded ? notTested : m.dieharderTotal ? (
      <>
        {m.dieharderPass ?? 0}/{m.dieharderTotal}
        <span className="block">
          {muted([m.dieharderWeak ? `${m.dieharderWeak} weak` : '', m.dieharderFail ? `${m.dieharderFail} fail` : '', `${m.dieharderSkipped ?? 0} skipped`].filter(Boolean).join(', '))}
        </span>
      </>
    ) : 'n/a',
  });
  if (selectedTests.has('performance')) cols.push(
    { key: 'shannon', label: 'Shannon', weight: 7, cell: m => m.shannon.toFixed(4) },
    { key: 'minent', label: 'Min Ent', weight: 7, cell: m => m.minEntropy.toFixed(4) },
    { key: 'bias', label: 'Bias', weight: 7, cell: m => m.bias.toFixed(4) },
    { key: 'thr', label: 'Throughput', weight: 9, align: 'right', cell: (m, kind) => kind === 'baseline'
      ? <span title="The raw input is not run through an extractor, so there is no extraction time to measure.">{muted('n/a (not extracted)')}</span>
      : `${(m.bitRate / 1e6).toFixed(1)} Mbps` },
  );
  return cols;
}

// Rankings that always fit their card: a fixed-layout table whose text scales with
// the card's width (container query units), and below the width where 11 columns
// stop being readable, one compact card per method instead. Nothing scrolls sideways.
function RankingTable({ result, selectedTests }: { result: AnalysisResult; selectedTests: Set<string> }) {
  const rows = rankingRows(result);
  const cols = rankingColumns(selectedTests);
  const fixed = [
    { key: 'rank', label: 'Rank', weight: 5 },
    { key: 'method', label: 'Method', weight: 20 },
    { key: 'score', label: 'Score', weight: 6 },
  ];
  const totalWeight = [...fixed, ...cols].reduce((sum, c) => sum + c.weight, 0);
  const pct = (w: number) => `${(100 * w / totalWeight).toFixed(2)}%`;
  const name = (m: RankedMethod, kind: RowKind) => kind === 'baseline' ? 'Raw input (baseline, not ranked)' : m.method.replace(/^\d+\.\s+/, '');
  const rowTone = (kind: RowKind, top: boolean) =>
    `${top ? 'bg-quantum-blue/5' : ''} ${kind === 'baseline' ? 'bg-quantum-light/10' : ''}`;
  const nameTone = (kind: RowKind, top: boolean) =>
    top ? 'text-quantum-blue' : kind !== 'ranked' ? 'text-quantum-navy/60' : 'text-quantum-navy';

  return (
    <div className="@container">
      {/* Wide: table. Font and padding scale with the card width (cqw), clamped to stay readable. */}
      <table
        className="hidden @[46rem]:table w-full table-fixed border-collapse text-left font-sans font-medium"
        style={{ fontSize: 'clamp(0.66rem, 1.08cqw, 0.92rem)' }}
      >
        <colgroup>
          {[...fixed, ...cols].map(c => <col key={c.key} style={{ width: pct(c.weight) }} />)}
        </colgroup>
        <thead>
          <tr className="text-quantum-navy border-b border-quantum-light">
            {[...fixed, ...cols].map(c => (
              <th key={c.key} className={`py-[0.9em] px-[0.6em] font-bold leading-tight ${'align' in c && c.align === 'right' ? 'text-right' : ''}`}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody className="text-quantum-navy/80">
          {rows.map(({ m, rank, kind }) => {
            const top = kind === 'ranked' && rank === 1;
            return (
              <tr key={m.method} className={`border-b border-quantum-light/50 hover:bg-quantum-light/10 transition-colors align-top ${rowTone(kind, top)}`}>
                <td className="py-[0.9em] px-[0.6em] font-bold">{kind === 'ranked' ? rank : '\u2014'}</td>
                <td className={`py-[0.9em] px-[0.6em] font-bold leading-snug break-words ${nameTone(kind, top)}`}>
                  {name(m, kind)}
                  {kind === 'excluded' && <span className="block mt-0.5 text-[0.85em] font-semibold text-orange-700">Not ranked: {m.excludedReason}</span>}
                </td>
                <td className="py-[0.9em] px-[0.6em] font-bold">{kind === 'ranked' ? m.score.toFixed(1) : '\u2014'}</td>
                {cols.map(c => (
                  <td key={c.key} className={`py-[0.9em] px-[0.6em] font-bold leading-snug break-words ${c.align === 'right' ? 'text-right' : ''}`}>{c.cell(m, kind)}</td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Narrow: one card per method, values in a grid that reflows with the width. */}
      <ol className="@[46rem]:hidden space-y-3">
        {rows.map(({ m, rank, kind }) => {
          const top = kind === 'ranked' && rank === 1;
          return (
            <li key={m.method} className={`rounded-lg border border-quantum-light/70 p-3 ${rowTone(kind, top)}`}>
              <div className="flex items-start gap-3">
                <span className="flex-shrink-0 min-w-[2rem] rounded-md bg-quantum-light/30 px-2 py-0.5 text-center text-xs font-bold text-quantum-navy">
                  {kind === 'ranked' ? `#${rank}` : '\u2014'}
                </span>
                <div className="min-w-0 flex-1">
                  <p className={`text-sm font-bold leading-snug break-words ${nameTone(kind, top)}`}>{name(m, kind)}</p>
                  {kind === 'excluded' && <p className="mt-0.5 text-xs font-semibold text-orange-700 break-words">Not ranked: {m.excludedReason}</p>}
                </div>
                <span className="flex-shrink-0 text-sm font-bold text-quantum-navy">{kind === 'ranked' ? m.score.toFixed(1) : '\u2014'}</span>
              </div>
              {cols.length > 0 && (
                <dl className="mt-2.5 grid grid-cols-2 @[24rem]:grid-cols-3 @[34rem]:grid-cols-4 gap-x-3 gap-y-2 text-xs">
                  {cols.map(c => (
                    <div key={c.key} className="min-w-0">
                      <dt className="font-semibold text-quantum-navy/55">{c.label}</dt>
                      <dd className="font-bold text-quantum-navy/85 break-words">{c.cell(m, kind)}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function formatBytes(bytes: number) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

const TEST_SUITES_CONFIG = [
  { id: 'nist', name: 'NIST SP 800-22', desc: '15 Statistical Tests', minBytes: 125000, warning: 'Requires at least 125 KB / 1,000,000 bits (Current: {current_size}) for Linear Complexity & Universal tests.' },
  { id: 'testu01', name: 'TestU01 Suite', desc: 'Alphabit + Rabbit Batteries', minBytes: 131072, warning: 'Requires at least 128 KB (Current: {current_size}). SmallCrush also runs on inputs over ~910 MB.' },
  { id: 'dieharder', name: 'Dieharder', desc: 'Full dieharder -a set: 114 tests', minBytes: 8388608, warning: 'Dieharder needs hundreds of MB for most tests (Current: {current_size}). Tests that would reuse data are reported as insufficient.' },
  { id: 'compression', name: 'Compression Tests', desc: 'Gzip, LZMA, Bzip2, Deflate', minBytes: 64000, warning: 'Requires at least 64 KB (Current: {current_size}) to avoid archive header bias.' },
  { id: 'performance', name: 'Performance Metrics', desc: 'Shannon Entropy • Min Entropy • Bias', minBytes: 2048, warning: 'Requires at least 2 KB (Current: {current_size}) for entropy & bias convergence.' }
];

export default function AnalyzePage() {
  const {
    file,
    setFile,
    limits,
    setLimits,
    methods,
    setMethods,
    selectedMethods,
    setSelectedMethods,
    selectedTests,
    setSelectedTests,
    status,
    setStatus,
    errorMsg,
    setErrorMsg,
    analysisLogs,
    setAnalysisLogs,
    result,
    setResult,
    resetSession,
  } = useAnalysis();

  const [activeTab, setActiveTab] = useState<string>('Overview');
  const [downloadingZip, setDownloadingZip] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [toast, setToast] = useState('');
  // Output length every method is deep-tested on (TestU01 / Dieharder).
  const [deepBytes, setDeepBytes] = useState(100 * 1024 * 1024);
  const [upload, setUpload] = useState<(UploadProgress & { speed: number }) | null>(null);

  const [isFetching, setIsFetching] = useState(false);
  const [hasFetched, setHasFetched] = useState(false);

  useEffect(() => {
    if (!file && !result) {
      setSelectedTests(new Set([]));
    }
  }, []);

  useEffect(() => {
    async function init() {
      if (hasFetched || isFetching) return;
      setIsFetching(true);
      try {
        const [l, m] = await Promise.all([getLimits(), getMethods()]);
        setLimits(l);
        setMethods(m);
      } catch (err) {
        console.error('Failed to init API:', err);
        setErrorMsg('Failed to initialize API. Backend may be unreachable.');
      } finally {
        setIsFetching(false);
        setHasFetched(true);
      }
    }
    
    if (methods.length === 0 && !hasFetched) {
      init();
    }
  }, [methods.length, hasFetched, isFetching, setLimits, setMethods, setErrorMsg]);

  useEffect(() => {
    if (file) {
      const fileSize = file.size;
      setSelectedTests(prev => {
        const next = new Set(prev);
        let changed = false;
        TEST_SUITES_CONFIG.forEach(t => {
          if (fileSize < t.minBytes && next.has(t.id)) {
            next.delete(t.id);
            changed = true;
          }
        });
        return changed ? next : prev;
      });
    }
  }, [file, setSelectedTests]);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(''), 3000);
  };

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
      setStatus('idle');
      setResult(null);
    }
  }, [setFile, setStatus, setResult]);
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({ 
    onDrop,
    accept: { 'application/octet-stream': ['.bin'], 'text/plain': ['.txt'] },
    maxFiles: 1
  });

  const handleToggleMethod = (id: string) => {
    setSelectedMethods(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    const next = new Set<string>();
    methods.forEach(m => {
      next.add(m.id);
    });
    setSelectedMethods(next);
  };

  const deselectAll = () => setSelectedMethods(new Set());

  const handleAnalyzeClick = () => {
    if (!file) return;
    if (selectedMethods.size === 0) {
      setErrorMsg('Please select at least one extraction method.');
      return;
    }

    executeAnalysis();
  };

  const executeAnalysis = async () => {
    if (!file) return;
    setStatus('analyzing');
    setErrorMsg('');
    const uploadStartedAt = Date.now();
    setUpload({ loaded: 0, total: file.size, speed: 0 });
    const getTime = () => new Date().toISOString().split('T')[1].substring(0, 8);
    setAnalysisLogs([
      { time: getTime(), msg: `Loaded ${file.name} ( ${(file.size / 1024).toFixed(1)} KB )` },
      { time: getTime(), msg: 'Initializing extraction pipeline...' },
    ]);

    try {
      let logIndex = 0;
      const res = await analyzeFile(
        file, 
        Array.from(selectedMethods),
        Array.from(selectedTests),
        (logs) => {
          if (logs && logs.length > logIndex) {
            const newLogs = logs.slice(logIndex).map(msg => ({
              time: getTime(),
              msg
            }));
            setAnalysisLogs(prev => [...prev, ...newLogs]);
            logIndex = logs.length;
          }
        },
        (p: UploadProgress) => {
          const elapsed = (Date.now() - uploadStartedAt) / 1000;
          setUpload({ loaded: p.loaded, total: p.total, speed: elapsed > 0.5 ? p.loaded / elapsed : 0 });
        },
        deepBytes
      );
      setResult(res);
      setStatus('complete');
    } catch (err: any) {
      setStatus('error');
      setErrorMsg(err.message || 'An unknown error occurred during analysis.');
    } finally {
      setUpload(null);
    }
  };

  const uploading = !!upload && upload.loaded < upload.total;
  const uploadPercent = upload && upload.total > 0 ? Math.min(100, Math.floor((upload.loaded / upload.total) * 100)) : 0;
  const uploadSpeed = upload?.speed ?? 0;

  const handleDownloadZip = async () => {
    if (!result || !file) return;
    setDownloadingZip(true);
    try {
      await downloadBitsZip(file, Array.from(selectedMethods));
      showToast('Extracted bitstreams downloaded successfully.');
    } catch (err: any) {
      console.error(err);
      alert('Error exporting bitstreams: ' + (err.message || 'Check browser console or mixed-content settings.'));
    } finally {
      setDownloadingZip(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!result || !file) return;
    setDownloadingPdf(true);
    try {
      await downloadPdfReport(result, selectedTests);
      showToast('PDF Report generated and downloaded.');
    } catch (err: any) {
      console.error(err);
      alert('Error downloading PDF: ' + (err.message || 'Check browser console or mixed-content settings.'));
    } finally {
      setDownloadingPdf(false);
    }
  };

  return (
    <>
      {toast && (
        <div className="fixed bottom-6 right-6 bg-white border border-quantum-cyan px-6 py-4 rounded-lg shadow-xl text-quantum-navy font-bold flex items-center gap-3 z-50 animate-in slide-in-from-bottom-4">
          <CheckCircle2 className="w-5 h-5 text-quantum-blue" />
          {toast}
        </div>
      )}

<div className="space-y-8 animate-in fade-in duration-500 pb-12">
        <div className="border-b border-quantum-light pb-6">
          <h1 className="text-3xl font-sans font-bold text-quantum-navy">Analysis Pipeline</h1>
          <p className="text-quantum-blue font-semibold mt-2">Upload raw data, select extraction methods, and evaluate randomness.</p>
        </div>

      {status === 'error' && (
        <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800 font-medium shadow-sm">
          <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5 text-red-600" />
          <div>
            <p className="font-bold text-red-900">Analysis Terminated</p>
            <p className="mt-1">{errorMsg}</p>
          </div>
        </div>
      )}

      {status === 'analyzing' ? (
        <TerminalCard title="Execution Log" className="border-quantum-light bg-white/90 backdrop-blur-md">
          <div className="space-y-4 min-h-[200px] flex flex-col">
            <div className="flex items-center gap-3 text-quantum-blue mb-2">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span className="font-bold text-sm">{uploading ? 'Uploading file...' : 'Processing batch...'}</span>
            </div>
            {/* The server only starts logging once the whole file has arrived, so
                without this the page looks frozen for the length of the upload. */}
            {upload && upload.total > 0 && (uploading || analysisLogs.length <= 2) && (
              <div className="rounded-lg border border-quantum-light bg-quantum-light/10 p-3 sm:p-4">
                <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-sm font-semibold text-quantum-navy">
                  <span>{uploading ? 'Uploading to server' : 'Upload complete'}</span>
                  <span className="tabular-nums">
                    {formatBytes(upload.loaded)} / {formatBytes(upload.total)} ({uploadPercent}%)
                  </span>
                </div>
                <div
                  className="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-quantum-light/40"
                  role="progressbar"
                  aria-label="File upload progress"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={uploadPercent}
                >
                  <div
                    className="h-full rounded-full bg-quantum-blue transition-[width] duration-300 ease-out"
                    style={{ width: `${uploadPercent}%` }}
                  />
                </div>
                <p className="mt-2 text-xs font-semibold text-quantum-navy/60 tabular-nums">
                  {uploading
                    ? (uploadSpeed > 0
                        ? `${formatBytes(uploadSpeed)}/s, about ${formatDuration((upload.total - upload.loaded) / uploadSpeed)} left`
                        : 'Starting upload...')
                    : 'Waiting for the server to start the analysis...'}
                </p>
              </div>
            )}
            {analysisLogs.map((log, i) => (
              <p key={i} className={`text-sm font-sans font-semibold ${i === analysisLogs.length - 1 ? 'text-quantum-navy' : 'text-quantum-blue/70'}`}>
                <span className="text-quantum-light font-bold mr-2">{log.time}</span>
                {log.msg}
              </p>
            ))}
          </div>
        </TerminalCard>
      ) : status === 'complete' && result ? (
        <div className="space-y-8 animate-in slide-in-from-bottom-4 duration-700">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white p-5 rounded-lg border border-quantum-light shadow-sm gap-4">
            <div>
              <div className="flex items-center gap-2 text-quantum-blue font-bold mb-1">
                <CheckCircle2 className="w-5 h-5" />
                Analysis Complete
              </div>
              <p className="text-sm text-quantum-navy/70 font-sans font-semibold">Session ID: {result.id}</p>
            </div>
            <div className="flex flex-wrap gap-3">
              <TerminalButton onClick={handleDownloadZip} disabled={downloadingZip} icon={Download} variant="secondary">
                {downloadingZip ? 'Archiving...' : 'Export Bitstreams'}
              </TerminalButton>
              <TerminalButton onClick={handleDownloadPdf} disabled={downloadingPdf} icon={FileText} variant="primary">
                {downloadingPdf ? 'Compiling...' : 'Generate PDF'}
              </TerminalButton>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            {selectedTests.has('performance') && (
              <>
                <div className="lg:col-span-2">
                  <h2 className="text-2xl font-bold text-quantum-navy mb-4 border-b border-quantum-light pb-2">Overview Metrics</h2>
                </div>
                
                <div className="lg:col-span-2">
                  <EfficiencyChart data={result.chartData} />
                </div>
                <EntropyChart data={result.chartData} />
                <BitRateChart data={result.chartData} />
                <div className="lg:col-span-2">
                  <BiasChart data={result.chartData} />
                </div>
              </>
            )}

            {(selectedTests.has('nist') || selectedTests.has('compression') || selectedTests.has('testu01') || selectedTests.has('dieharder')) && (
              <div className="lg:col-span-2 mt-6">
                <h2 className="text-2xl font-bold text-quantum-navy mb-4 border-b border-quantum-light pb-2">Statistical Test Batteries</h2>
              </div>
            )}

            {selectedTests.has('nist') && (
              <div className="lg:col-span-2">
                <NistComplianceChart data={result.chartData} />
              </div>
            )}
            {selectedTests.has('compression') && (
              <div className="lg:col-span-2">
                <CompressionChart data={result.chartData} />
              </div>
            )}
            {selectedTests.has('testu01') && (
              <div className="lg:col-span-2">
                <TestU01Chart data={result.chartData} />
              </div>
            )}
            {selectedTests.has('dieharder') && (
              <div className="lg:col-span-2">
                <DieharderChart data={result.chartData} />
              </div>
            )}
          </div>

          {result.rankedMethods.length > 0 && (
            <div className="space-y-6">
              <div className="bg-white border border-quantum-cyan rounded-lg p-6 shadow-sm">
                <div className="flex items-center gap-3 mb-3">
                  <span className="flex h-8 w-8 items-center justify-center rounded-md bg-quantum-blue/10 text-quantum-blue">
                    ★
                  </span>
                  <h3 className="text-xl font-bold text-quantum-navy">Optimal Method: {result.bestMethod}</h3>
                </div>
                <p className="text-quantum-blue text-sm leading-relaxed font-medium">{result.bestMethodExplanation}</p>
              </div>

              <TerminalCard title="Performance Rankings">
                <RankingTable result={result} selectedTests={selectedTests} />
                <p className="mt-4 text-xs text-quantum-navy/60 font-medium leading-relaxed">
                  Scores count every TestU01 and Dieharder test, with skipped tests counting as not passed. NIST is scored on the tests that apply to the sample: NIST defines a not-applicable test (n/a) as neither a pass nor a fail.
                  {result.deepOutputBytes ? ` TestU01 and Dieharder ran on the same ${formatBytes(result.deepOutputBytes)} of output for every method; methods that could not produce that much are listed but not ranked.` : ''}
                  {result.deepOutputBytes === 0 ? ' TestU01 and Dieharder ran on the full output of each method over the whole file, so the amount of data differs between methods: methods that keep less of their input have more tests skipped.' : ''}
                  {selectedTests.has('dieharder') ? ' Dieharder is scored out of all 114 tests of dieharder -a for every method; tests that would need more data than the tested output are skipped and count as not passed, rather than being run on reused data.' : ''}
                </p>
              </TerminalCard>
            </div>
          )}
          
          <div className="pt-6">
            <TerminalButton variant="secondary" onClick={resetSession} fullWidth>
              Start New Analysis Session
            </TerminalButton>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
          <div className="lg:col-span-1 space-y-6">
            <TerminalCard title="Input Source">
              <div 
                {...getRootProps()} 
                className={`border-2 border-dashed ${isDragActive ? 'border-quantum-blue bg-quantum-blue/5' : 'border-quantum-light hover:border-quantum-cyan hover:bg-quantum-light/10'} rounded-lg p-8 text-center transition-all duration-200 bg-white/50 backdrop-blur-sm`}
              >
                <input {...getInputProps()} />
                {file ? (
                  <div className="space-y-3">
                    <Binary className="w-10 h-10 mx-auto text-quantum-blue" />
                    <div>
                      <p className="text-quantum-navy font-bold truncate text-sm px-2">{file.name}</p>
                      <p className="text-xs text-quantum-navy/70 mt-1 font-semibold">{(file.size / 1024).toFixed(1)} KB</p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <Upload className={`w-10 h-10 mx-auto ${isDragActive ? 'text-quantum-blue' : 'text-quantum-light'}`} />
                    <div>
                      <p className="text-quantum-navy text-sm font-bold">Upload raw bits</p>
                      <p className="text-xs text-quantum-navy/70 mt-1 font-semibold">Drag & drop .bin or .txt</p>
                    </div>
                  </div>
                )}
              </div>
            </TerminalCard>
            
            <div>
              <TerminalButton 
                onClick={handleAnalyzeClick} 
                disabled={!file || selectedMethods.size === 0} 
                icon={Play}
                fullWidth
                className="py-4 text-base"
              >
                Execute Pipeline
              </TerminalButton>
              {errorMsg && <p className="text-red-600 font-bold text-xs mt-3 text-center">{errorMsg}</p>}
            </div>
          </div>

          <div className="lg:col-span-2">
            <TerminalCard title="Extraction Algorithms">
<div className="flex gap-4 mb-4 pb-4 border-b border-quantum-light">
                <button onClick={selectAll} className="text-xs font-bold text-quantum-blue hover:text-quantum-navy transition-colors">
                  Select All
                </button>
                <button onClick={deselectAll} className="text-xs font-bold text-quantum-navy/50 hover:text-quantum-navy transition-colors">
                  Clear All
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {methods.length === 0 && isFetching && (
                  <div className="col-span-1 sm:col-span-2 text-center text-quantum-navy/60 text-sm py-8 font-semibold">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-quantum-blue" />
                    Loading algorithms...
                  </div>
                )}
                {methods.length === 0 && !isFetching && !errorMsg && (
                  <div className="col-span-1 sm:col-span-2 text-center text-quantum-navy/60 text-sm py-8 font-semibold">
                    No extraction algorithms available. Check backend connection.
                  </div>
                )}
                {methods.map(m => {
const isSelected = selectedMethods.has(m.id);
                  return (
                    <div 
                      key={m.id}
                      onClick={() => handleToggleMethod(m.id)}
                      className={`group flex items-center justify-between p-3.5 sm:p-4 rounded-xl border-2 cursor-pointer transition-all duration-300 ease-out ${isSelected ? 'border-quantum-blue bg-gradient-to-r from-quantum-blue/10 to-transparent shadow-md shadow-quantum-blue/10 transform scale-[1.02]' : 'border-quantum-light/40 bg-white hover:border-quantum-cyan hover:shadow-md hover:-translate-y-0.5'}`}
                    >
                      <div className="flex items-center gap-3.5 flex-1 min-w-0">
                        <div className={`flex flex-shrink-0 items-center justify-center w-6 h-6 rounded-md border-2 transition-colors duration-200 ${isSelected ? 'bg-quantum-blue border-quantum-blue' : 'border-quantum-light/80 bg-white group-hover:border-quantum-cyan'}`}>
                          {isSelected && <Check className="w-4 h-4 text-white" strokeWidth={3} />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className={`text-[15px] leading-tight truncate transition-colors duration-200 ${isSelected ? 'text-quantum-navy font-extrabold' : 'text-quantum-navy/80 font-bold group-hover:text-quantum-navy'}`}>
                            {m.name}
                          </p>
                        </div>
                      </div>
</div>
                  );
                })}
              </div>
            </TerminalCard>
            
            <div className="mt-8">
              <TerminalCard title="Statistical Test Suites">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {TEST_SUITES_CONFIG.map(t => {
                    const isDisabled = file ? file.size < t.minBytes : false;
                    const isSelected = selectedTests.has(t.id);
                    return (
                      <div key={t.id} className="flex flex-col gap-1">
                        <div 
                          onClick={() => {
                            if (isDisabled) return;
                            setSelectedTests(prev => {
                              const next = new Set(prev);
                              if (next.has(t.id)) next.delete(t.id);
                              else next.add(t.id);
                              return next;
                            });
                          }}
                          className={`group flex flex-col justify-center p-3.5 sm:p-4 rounded-xl border-2 transition-all duration-300 ease-out ${isDisabled ? 'opacity-55 cursor-not-allowed pointer-events-none border-quantum-light/40 bg-gray-50/50' : isSelected ? 'border-quantum-blue bg-gradient-to-r from-quantum-blue/10 to-transparent shadow-md shadow-quantum-blue/10 transform scale-[1.02] cursor-pointer' : 'border-quantum-light/40 bg-white hover:border-quantum-cyan hover:shadow-md hover:-translate-y-0.5 cursor-pointer'}`}
                        >
                          <div className="flex items-center gap-3.5 w-full">
                            <div className={`flex flex-shrink-0 items-center justify-center w-6 h-6 rounded-md border-2 transition-colors duration-200 ${isSelected ? 'bg-quantum-blue border-quantum-blue' : 'border-quantum-light/80 bg-white'}`}>
                              {isSelected && <Check className="w-4 h-4 text-white" strokeWidth={3} />}
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className={`text-[15px] leading-tight truncate transition-colors duration-200 ${isSelected ? 'text-quantum-navy font-extrabold' : 'text-quantum-navy/80 font-bold'}`}>
                                {t.name}
                              </p>
                              <p className="text-[11px] text-quantum-navy/60 font-semibold truncate mt-0.5">
                                {t.desc}
                              </p>
                            </div>
</div>
                        </div>
                        {isDisabled && (
                          <div className="flex items-start gap-1.5 text-[10px] sm:text-[11px] font-bold text-red-600/90 bg-red-50/80 backdrop-blur-sm px-2.5 py-1.5 rounded-md shadow-sm border border-red-100/50 mt-0.5">
                            <AlertTriangle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                            <span className="leading-tight">
                              ⚠️ Data size too small ({t.warning.replace('{current_size}', file ? formatBytes(file.size) : '0 Bytes')}) — Suite Disabled
                            </span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
                {(selectedTests.has('testu01') || selectedTests.has('dieharder')) && (
                  <div className="mt-5 pt-4 border-t border-quantum-light flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
                    <label htmlFor="deep-bytes" className="text-sm font-bold text-quantum-navy whitespace-nowrap">Output tested per method</label>
                    <select
                      id="deep-bytes"
                      value={deepBytes}
                      onChange={e => setDeepBytes(Number(e.target.value))}
                      className="rounded-lg border border-quantum-light bg-white px-3 py-2 text-sm font-semibold text-quantum-navy"
                    >
                      {(limits?.deepOutputOptions ?? [32, 64, 100, 256].map(m => m * 1024 * 1024).concat(0)).map(b => (
                        <option key={b} value={b}>{b === 0 ? 'Full output (whole file)' : formatBytes(b)}</option>
                      ))}
                    </select>
                    <p className="text-xs text-quantum-navy/60 font-medium leading-snug">
                      {deepBytes === 0
                        ? 'Each method is tested on all the output it produces from your whole file. Totals stay the same for every method, but the amount of data differs: methods that keep less of their input have more tests skipped, which count as not passed.'
                        : 'TestU01 and Dieharder test every method on exactly this much output. A method that cannot produce it from your file is listed but not ranked.'}
                      {file ? ` Your file is ${formatBytes(file.size)}.` : ''}
                    </p>
                  </div>
                )}
              </TerminalCard>
            </div>
          </div>
        </div>
      )}
    </div>
    </>
  );
}
