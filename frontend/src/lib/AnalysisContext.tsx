"use client";

import React, { createContext, useContext, useState, ReactNode } from 'react';
import { Method, Limits, AnalysisResult } from './api';

interface AnalysisContextType {
  file: File | null;
  setFile: (file: File | null) => void;
  limits: Limits | null;
  setLimits: (limits: Limits | null) => void;
  methods: Method[];
  setMethods: (methods: Method[]) => void;
  selectedMethods: Set<string>;
  setSelectedMethods: React.Dispatch<React.SetStateAction<Set<string>>>;
  status: 'idle' | 'analyzing' | 'complete' | 'error';
  setStatus: (status: 'idle' | 'analyzing' | 'complete' | 'error') => void;
  errorMsg: string;
  setErrorMsg: (msg: string) => void;
  analysisLogs: { time: string; msg: string }[];
  setAnalysisLogs: React.Dispatch<React.SetStateAction<{ time: string; msg: string }[]>>;
  result: AnalysisResult | null;
  setResult: (result: AnalysisResult | null) => void;
  resetSession: () => void;
}

const AnalysisContext = createContext<AnalysisContextType | undefined>(undefined);

export function AnalysisProvider({ children }: { children: ReactNode }) {
  const [file, setFile] = useState<File | null>(null);
  const [limits, setLimits] = useState<Limits | null>(null);
  const [methods, setMethods] = useState<Method[]>([]);
  const [selectedMethods, setSelectedMethods] = useState<Set<string>>(new Set());
  const [status, setStatus] = useState<'idle' | 'analyzing' | 'complete' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const [analysisLogs, setAnalysisLogs] = useState<{ time: string; msg: string }[]>([]);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  const resetSession = () => {
    setFile(null);
    setSelectedMethods(new Set());
    setStatus('idle');
    setErrorMsg('');
    setAnalysisLogs([]);
    setResult(null);
  };

  return (
    <AnalysisContext.Provider
      value={{
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
      }}
    >
      {children}
    </AnalysisContext.Provider>
  );
}

export function useAnalysis() {
  const context = useContext(AnalysisContext);
  if (context === undefined) {
    throw new Error('useAnalysis must be used within an AnalysisProvider');
  }
  return context;
}
