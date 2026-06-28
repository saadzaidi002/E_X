"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { TerminalCard } from '@/components/TerminalCard';
import { TerminalButton } from '@/components/TerminalButton';
import { getMethods, getLimits, analyzeFile, downloadBitsZip, downloadPdfReport, Method, Limits, AnalysisResult } from '@/lib/api';
import { EntropyChart, BitRateChart, BiasChart, NistComplianceChart, EfficiencyChart } from '@/components/charts/ComparisonCharts';
import { Upload, Play, Download, FileText, Check, AlertTriangle, Loader2, Binary, CheckCircle2 } from 'lucide-react';
import { useAnalysis } from '@/lib/AnalysisContext';

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

  const [downloadingZip, setDownloadingZip] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [toast, setToast] = useState('');

  useEffect(() => {
    async function init() {
      try {
        const [l, m] = await Promise.all([getLimits(), getMethods()]);
        setLimits(l);
        setMethods(m);
      } catch (err) {
        console.error(err);
        setErrorMsg('Failed to initialize API. Backend may be unreachable.');
      }
    }
    // Only initialize API endpoints if they haven't been loaded yet to preserve session errors / status
    if (methods.length === 0 || !limits) {
      init();
    }
  }, [methods.length, limits, setLimits, setMethods, setErrorMsg]);

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
    if (isInputLarge && !isFast) return; // Disabled

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
      if (!(isInputLarge && !m.isFast)) {
        next.add(m.id);
      }
    });
    setSelectedMethods(next);
  };

  const deselectAll = () => setSelectedMethods(new Set());

  const handleAnalyze = async () => {
    if (!file) return;
    if (selectedMethods.size === 0) {
      setErrorMsg('Please select at least one extraction method.');
      return;
    }

    setStatus('analyzing');
    setErrorMsg('');
    const getTime = () => new Date().toISOString().split('T')[1].substring(0, 8);
    setAnalysisLogs([
      { time: getTime(), msg: `Loaded ${file.name} ( ${(file.size / 1024).toFixed(1)} KB )` },
      { time: getTime(), msg: 'Initializing extraction pipeline...' },
    ]);

    try {
      setTimeout(() => setAnalysisLogs(prev => [...prev, { time: getTime(), msg: 'Running selected extractor modules...' }]), 800);
      setTimeout(() => setAnalysisLogs(prev => [...prev, { time: getTime(), msg: 'Executing NIST SP 800-22 statistical battery...' }]), 1600);
      setTimeout(() => setAnalysisLogs(prev => [...prev, { time: getTime(), msg: 'Compiling comparative analytics report...' }]), 2400);

      const res = await analyzeFile(file, Array.from(selectedMethods));
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
      await downloadPdfReport(file, Array.from(selectedMethods));
      showToast('PDF Report generated and downloaded.');
    } finally {
      setDownloadingPdf(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500 pb-12">
      <div className="border-b border-quantum-light pb-6">
        <h1 className="text-3xl font-sans font-bold text-quantum-navy">Analysis Pipeline</h1>
        <p className="text-quantum-blue font-semibold mt-2">Upload raw data, select extraction methods, and evaluate randomness.</p>
      </div>

      {toast && (
        <div className="fixed bottom-6 right-6 bg-white border border-quantum-cyan px-6 py-4 rounded-lg shadow-xl text-quantum-navy font-bold flex items-center gap-3 z-50 animate-in slide-in-from-bottom-4">
          <CheckCircle2 className="w-5 h-5 text-quantum-blue" />
          {toast}
        </div>
      )}

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

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="lg:col-span-2">
              <EfficiencyChart data={result.chartData} />
            </div>
            <EntropyChart data={result.chartData} />
            <NistComplianceChart data={result.chartData} />
            <BitRateChart data={result.chartData} />
            <BiasChart data={result.chartData} />
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
                  <table className="w-full text-left text-sm border-collapse font-sans font-medium">
                    <thead>
                      <tr className="text-quantum-navy border-b border-quantum-light">
                        <th className="py-3 px-4 font-bold">Rank</th>
                        <th className="py-3 px-4 font-bold">Method</th>
                        <th className="py-3 px-4 font-bold">Score</th>
                        <th className="py-3 px-4 font-bold">NIST Pass</th>
                        <th className="py-3 px-4 font-bold">Shannon</th>
                        <th className="py-3 px-4 font-bold">Min Entropy</th>
                        <th className="py-3 px-4 font-bold">Bias</th>
                        <th className="py-3 px-4 font-bold text-right">Throughput</th>
                      </tr>
                    </thead>
                    <tbody className="text-quantum-navy/80">
                      {result.rankedMethods.map((m, i) => (
                        <tr key={m.method} className={`border-b border-quantum-light/50 hover:bg-quantum-light/10 transition-colors ${i === 0 ? 'bg-quantum-blue/5' : ''}`}>
                          <td className="py-3 px-4 text-xs font-bold">{i + 1}</td>
                          <td className={`py-3 px-4 font-bold ${i === 0 ? 'text-quantum-blue' : 'text-quantum-navy'}`}>{m.method.replace(/^\d+\.\s+/, '')}</td>
                          <td className="py-3 px-4 text-xs font-bold">{m.score.toFixed(1)}</td>
                          <td className="py-3 px-4 text-xs font-bold">{m.nistPass}/15</td>
                          <td className="py-3 px-4 text-xs font-bold">{m.shannon.toFixed(4)}</td>
                          <td className="py-3 px-4 text-xs font-bold">{m.minEntropy.toFixed(4)}</td>
                          <td className="py-3 px-4 text-xs font-bold">{m.bias.toFixed(4)}</td>
                          <td className="py-3 px-4 text-xs font-bold text-right">{Math.round(m.bitRate).toLocaleString()} bps</td>
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
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
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
                onClick={handleAnalyze} 
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
                    Input size exceeds fast-tier limit ({(limits?.fastTierThreshold! / 1024 / 1024).toFixed(1)}MB). Quadratic-time methods have been automatically disabled to prevent system lockup.
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
                {methods.map(m => {
                  const disabled = isInputLarge && !m.isFast;
                  const isSelected = selectedMethods.has(m.id);
                  return (
                    <div 
                      key={m.id}
                      onClick={() => handleToggleMethod(m.id, m.isFast)}
                      className={`flex items-center p-3 rounded-lg border-2 ${isSelected ? 'border-quantum-blue bg-quantum-blue/5 shadow-sm' : 'border-transparent hover:bg-quantum-light/20'} ${disabled ? 'opacity-40 hover:bg-transparent' : ''} transition-all`}
                    >
                      <div className={`flex items-center justify-center w-5 h-5 rounded border mr-3 ${isSelected ? 'bg-quantum-blue border-quantum-blue' : 'border-quantum-light bg-white'}`}>
                        {isSelected && <Check className="w-3.5 h-3.5 text-white" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm truncate ${isSelected ? 'text-quantum-navy font-bold' : 'text-quantum-navy/80 font-semibold'}`}>
                          {m.name}
                        </p>
                      </div>
                      {disabled && <span className="text-[10px] uppercase font-bold text-orange-600 bg-orange-100 px-1.5 py-0.5 rounded ml-2">Slow</span>}
                    </div>
                  );
                })}
              </div>
            </TerminalCard>
          </div>
        </div>
      )}
    </div>
  );
}
