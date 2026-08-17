"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { TerminalCard } from '@/components/TerminalCard';
import { TerminalButton } from '@/components/TerminalButton';
import { getMethods, getLimits, analyzeFile, downloadBitsZip, downloadPdfReport, Method, Limits, AnalysisResult } from '@/lib/api';
import { EntropyChart, BitRateChart, BiasChart, NistComplianceChart, EfficiencyChart, CompressionChart, TestU01Chart, DieharderChart } from '@/components/charts/ComparisonCharts';
import { Upload, Play, Download, FileText, Check, AlertTriangle, Loader2, Binary, CheckCircle2 } from 'lucide-react';
import { useAnalysis } from '@/lib/AnalysisContext';

function formatBytes(bytes: number) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

const TEST_SUITES_CONFIG = [
  { id: 'nist', name: 'NIST SP 800-22', desc: '15 Statistical Tests', isSlow: false, minBytes: 125000, warning: 'Requires at least 125 KB / 1,000,000 bits (Current: {current_size}) for Linear Complexity & Universal tests.' },
  { id: 'testu01', name: 'TestU01 Suite', desc: 'SmallCrush (15 Tests)', isSlow: true, minBytes: 2000000, warning: 'Requires at least 2 MB (Current: {current_size}) for 32-bit word sample completeness.' },
  { id: 'dieharder', name: 'Dieharder', desc: 'Advanced Test Battery', isSlow: true, minBytes: 13107200, warning: 'Requires at least 13 MB (Current: {current_size}) to run Marsaglia tests without data recycling/rewind.' },
  { id: 'compression', name: 'Compression Tests', desc: 'Gzip, LZMA, Bzip2, Deflate', isSlow: false, minBytes: 64000, warning: 'Requires at least 64 KB (Current: {current_size}) to avoid archive header bias.' },
  { id: 'performance', name: 'Performance Metrics', desc: 'Shannon Entropy • Min Entropy • Bias', isSlow: false, minBytes: 2048, warning: 'Requires at least 2 KB (Current: {current_size}) for entropy & bias convergence.' }
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
  const [showConfirmation, setShowConfirmation] = useState(false);

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

  const isInputLarge = file && limits && file.size > limits.fastTierThreshold;

  const handleToggleMethod = (id: string, isFast: boolean) => {

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

    const hasSlowMethods = Array.from(selectedMethods).some(id => {
      const m = methods.find(method => method.id === id);
      return m && !m.isFast;
    });

    if (isInputLarge && hasSlowMethods) {
      setShowConfirmation(true);
    } else {
      executeAnalysis();
    }
  };

  const executeAnalysis = async () => {
    if (!file) return;
    setShowConfirmation(false);
    setStatus('analyzing');
    setErrorMsg('');
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
        }
      );
      setResult(res);
      setStatus('complete');
    } catch (err: any) {
      setStatus('error');
      setErrorMsg(err.message || 'An unknown error occurred during analysis.');
    }
  };

  const handleDownloadZip = async () => {
    if (!result || !file) return;
    setDownloadingZip(true);
    try {
      await downloadBitsZip(file, Array.from(selectedMethods));
      showToast('Extracted bitstreams downloaded successfully.');
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

      {showConfirmation && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-lg p-6 max-w-md w-full shadow-2xl border border-orange-200">
            <h2 className="text-xl font-bold text-quantum-navy mb-4 flex items-center gap-2">
              <AlertTriangle className="text-orange-600" />
              Performance Warning
            </h2>
            <div className="text-sm text-quantum-navy/80 mb-6 space-y-3">
              <p>You have selected the following slow methods on a large input file:</p>
              <ul className="list-disc ml-5 font-bold text-quantum-navy">
                {Array.from(selectedMethods)
                  .filter(id => !methods.find(m => m.id === id)?.isFast)
                  .map(id => <li key={id}>{methods.find(m => m.id === id)?.name}</li>)}
              </ul>
              <p>
                These methods scale poorly on larger inputs. Processing time could be <strong>significantly longer</strong> than the other methods (this may take several minutes or longer, and in extreme cases could time out).
              </p>
            </div>
            <div className="flex justify-end gap-3">
              <TerminalButton onClick={() => setShowConfirmation(false)} variant="secondary" className="px-4 py-2 text-sm">
                Go Back
              </TerminalButton>
              <button 
                onClick={executeAnalysis} 
                className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded font-bold text-sm transition-colors flex items-center gap-2"
              >
                Proceed Anyway
              </button>
            </div>
          </div>
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
              <span className="font-bold text-sm">Processing batch...</span>
            </div>
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
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm border-collapse font-sans font-medium whitespace-nowrap">
                    <thead>
                      <tr className="text-quantum-navy border-b border-quantum-light">
                        <th className="py-3 px-4 font-bold">Rank</th>
                        <th className="py-3 px-4 font-bold">Method</th>
                        <th className="py-3 px-4 font-bold">Score</th>
                        {selectedTests.has('nist') && <th className="py-3 px-4 font-bold">NIST</th>}
                        {selectedTests.has('compression') && <th className="py-3 px-4 font-bold">Compress</th>}
                        {selectedTests.has('testu01') && <th className="py-3 px-4 font-bold">TestU01</th>}
                        {selectedTests.has('dieharder') && <th className="py-3 px-4 font-bold">Dieharder</th>}
                        {selectedTests.has('performance') && (
                          <>
                            <th className="py-3 px-4 font-bold">Shannon</th>
                            <th className="py-3 px-4 font-bold">Min Ent</th>
                            <th className="py-3 px-4 font-bold">Bias</th>
                            <th className="py-3 px-4 font-bold text-right">Throughput</th>
                          </>
                        )}
                      </tr>
                    </thead>
                    <tbody className="text-quantum-navy/80">
                      {result.rankedMethods.map((m, i) => (
                        <tr key={m.method} className={`border-b border-quantum-light/50 hover:bg-quantum-light/10 transition-colors ${i === 0 ? 'bg-quantum-blue/5' : ''}`}>
                          <td className="py-3 px-4 text-xs font-bold">{i + 1}</td>
                          <td className={`py-3 px-4 font-bold ${i === 0 ? 'text-quantum-blue' : 'text-quantum-navy'}`}>{m.method.replace(/^\d+\.\s+/, '')}</td>
                          <td className="py-3 px-4 text-xs font-bold">{m.score.toFixed(1)}</td>
                          {selectedTests.has('nist') && <td className="py-3 px-4 text-xs font-bold">{m.nistPass}/15</td>}
                          {selectedTests.has('compression') && <td className="py-3 px-4 text-xs font-bold">{m.compressionPass ?? 0}/4</td>}
                          {selectedTests.has('testu01') && <td className="py-3 px-4 text-xs font-bold">{m.testu01Pass ?? 0}/15</td>}
                          {selectedTests.has('dieharder') && <td className="py-3 px-4 text-xs font-bold">{m.dieharderPass ?? 0}/100</td>}
                          {selectedTests.has('performance') && (
                            <>
                              <td className="py-3 px-4 text-xs font-bold">{m.shannon.toFixed(4)}</td>
                              <td className="py-3 px-4 text-xs font-bold">{m.minEntropy.toFixed(4)}</td>
                              <td className="py-3 px-4 text-xs font-bold">{m.bias.toFixed(4)}</td>
                              <td className="py-3 px-4 text-xs font-bold text-right">{Math.round(m.bitRate).toLocaleString()} bps</td>
                            </>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
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
              {isInputLarge && (
                <div className="mb-5 p-4 bg-orange-50 border border-orange-200 rounded-lg text-orange-800 text-sm flex items-start shadow-sm font-medium">
                  <AlertTriangle className="w-5 h-5 mr-3 flex-shrink-0 text-orange-600" />
                  <span className="leading-relaxed">
                    Input size exceeds fast-tier limit ({limits?.fastTierThreshold! >= 1024 * 1024 ? (limits?.fastTierThreshold! / 1024 / 1024).toFixed(1) + 'MB' : (limits?.fastTierThreshold! / 1024).toFixed(1) + 'KB'}). Quadratic-time methods will take significantly longer to process and may time out.
                  </span>
                </div>
              )}
              
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
                  const isSlowWarning = isInputLarge && !m.isFast;
                  const isSelected = selectedMethods.has(m.id);
                  return (
                    <div 
                      key={m.id}
                      onClick={() => handleToggleMethod(m.id, m.isFast)}
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
                      {isSlowWarning && (
                        <div className="flex items-center gap-1.5 text-[10px] uppercase font-bold text-orange-700 bg-orange-100/80 backdrop-blur-sm px-2 py-1 rounded-full shadow-sm ml-2 flex-shrink-0" title="This method scales poorly on large inputs">
                          <AlertTriangle className="w-3.5 h-3.5" />
                          <span>Slow</span>
                        </div>
                      )}
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
                            {t.isSlow && isInputLarge && (
                              <div className="flex items-center gap-1.5 text-[10px] uppercase font-bold text-orange-700 bg-orange-100/80 backdrop-blur-sm px-2 py-1 rounded-full shadow-sm ml-2 flex-shrink-0" title="This test scales poorly on large inputs">
                                <AlertTriangle className="w-3.5 h-3.5" />
                                <span>Slow</span>
                              </div>
                            )}
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
              </TerminalCard>
            </div>
          </div>
        </div>
      )}
    </div>
    </>
  );
}
