"use client";
import React, { useEffect, useState } from 'react';
import { TerminalCard } from '@/components/TerminalCard';
import { getLimits, Limits } from '@/lib/api';
import { Binary, FileText } from 'lucide-react';

const formatSize = (val: number, isBits: boolean) => {
  const bytes = isBits ? val / 8 : val;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
};

export default function GuidePage() {
  const [limits, setLimits] = useState<Limits | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    getLimits()
      .then(setLimits)
      .catch((err) => {
        console.error(err);
        setError(true);
      });
  }, []);

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-0 animate-in fade-in duration-500 pb-12">
      <div className="mb-8 border-b border-quantum-light pb-6">
        <h1 className="text-3xl font-sans font-bold text-quantum-navy">Documentation</h1>
        <p className="text-quantum-blue font-semibold mt-2">System requirements, input specifications, and operating limits.</p>
      </div>

      <div className="space-y-8">
        <TerminalCard delay={0.2} title="Supported Input Formats">
          <div className="space-y-6">
            <p className="text-quantum-navy/80 font-medium leading-relaxed">
              The extractor pipeline accepts raw random bits in two formats. We highly recommend using packed binary files for performance reasons.
            </p>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border border-quantum-light bg-white shadow-sm p-5 rounded-lg">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 bg-quantum-blue/10 rounded text-quantum-blue">
                    <Binary className="w-5 h-5" />
                  </div>
                  <h3 className="font-bold text-quantum-navy">Packed Binary (.bin)</h3>
                </div>
                <p className="text-sm text-quantum-navy/70 font-medium">Every 1 byte represents 8 bits. This format is 8x smaller, meaning faster uploads and significantly shorter analysis times. <strong className="text-quantum-navy">Recommended.</strong></p>
              </div>

              <div className="border border-quantum-light bg-white shadow-sm p-5 rounded-lg">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 bg-quantum-light/30 rounded text-quantum-navy/60">
                    <FileText className="w-5 h-5" />
                  </div>
                  <h3 className="font-bold text-quantum-navy">Plain Text (.txt)</h3>
                </div>
                <p className="text-sm text-quantum-navy/70 font-medium">Literal '0' and '1' characters separated by whitespace or newlines. Slower to parse and consume more memory. Supported for legacy compatibility.</p>
              </div>
            </div>
          </div>
        </TerminalCard>

        <TerminalCard delay={0.4} title="System Performance Tiers">
          {error ? (
            <div className="flex items-center justify-center py-12 text-red-500 font-bold text-sm bg-red-50 rounded-lg border border-red-200">
              Failed to load system limits. Please ensure the backend server is running.
            </div>
          ) : limits ? (
            <div className="space-y-6">
              <div className="space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 sm:p-5 border border-quantum-light/50 rounded-xl bg-white shadow-sm hover:shadow-md hover:border-quantum-cyan/50 transition-all duration-300">
                  <div className="mb-3 sm:mb-0">
                    <h3 className="font-bold text-quantum-navy text-lg">Tier 1: Core Analysis</h3>
                    <p className="text-sm text-quantum-navy/70 font-medium mt-1">Input size &ge; 125 KB (1,000,000 bits)</p>
                    <p className="text-xs text-quantum-navy/60 font-medium mt-1">Entropy, bias, NIST SP 800-22 and compression tests for every extractor, measured on the first {formatSize(limits.exportBinaryBytes ?? 8 * 1024 * 1024, false)} of the file.</p>
                  </div>
                  <div className="sm:text-right flex sm:block items-center justify-between flex-shrink-0 sm:ml-4">
                    <span className="inline-block px-4 py-1.5 bg-quantum-blue/10 text-quantum-blue text-xs font-bold rounded-full sm:mb-1.5">All Files</span>
                    <p className="text-xs text-quantum-navy/60 font-semibold">Est. Wait: about 1 min</p>
                  </div>
                </div>
                
                <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 sm:p-5 border border-quantum-light/50 rounded-xl bg-white shadow-sm hover:shadow-md hover:border-orange-300/50 transition-all duration-300">
                  <div className="mb-3 sm:mb-0">
                    <h3 className="font-bold text-quantum-navy text-lg">Tier 2: TestU01 Batteries</h3>
                    <p className="text-sm text-quantum-navy/70 font-medium mt-1">Input size &ge; 2 MB</p>
                    <p className="text-xs text-quantum-navy/60 font-medium mt-1">Adds TestU01 Alphabit and Rabbit. Each extractor&apos;s output must reach 2<sup>20</sup> bits; smaller inputs leave low-yield extractors marked insufficient.</p>
                  </div>
                  <div className="sm:text-right flex sm:block items-center justify-between flex-shrink-0 sm:ml-4">
                    <span className="inline-block px-4 py-1.5 bg-orange-100 text-orange-600 text-xs font-bold rounded-full sm:mb-1.5">Deep Tests</span>
                    <p className="text-xs text-quantum-navy/60 font-semibold">Est. Wait: a few mins</p>
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 sm:p-5 border border-purple-200 rounded-xl bg-purple-50/50 shadow-sm hover:shadow-md hover:border-purple-300 transition-all duration-300">
                  <div className="mb-3 sm:mb-0">
                    <h3 className="font-bold text-purple-800 text-lg">Tier 3: Dieharder</h3>
                    <p className="text-sm text-purple-700 font-medium mt-1">42 MB &le; Input &le; {formatSize(limits.maxFileSize, false)}</p>
                    <p className="text-xs text-purple-600/80 font-medium mt-1">Adds Dieharder, run on the whole file for every extractor. The first tests need 42 MB; around 500 MB covers most of them. Tests that would have to reuse data are reported as insufficient.</p>
                  </div>
                  <div className="sm:text-right flex sm:block items-center justify-between flex-shrink-0 sm:ml-4">
                    <span className="inline-block px-4 py-1.5 bg-purple-100 text-purple-700 text-xs font-bold rounded-full sm:mb-1.5">Heavy Load</span>
                    <p className="text-xs text-purple-600/70 font-semibold">Est. Wait: 10&ndash;30 mins at 500 MB</p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center py-12">
              <div className="w-6 h-6 border-4 border-quantum-blue border-t-transparent rounded-full animate-spin"></div>
            </div>
          )}
        </TerminalCard>

        <TerminalCard delay={0.6} title="Advanced Randomness Testing">
          <div className="space-y-6">
            <p className="text-quantum-navy/80 font-medium leading-relaxed">
              In addition to the standard NIST SP 800-22 tests, this system evaluates extractors using three advanced methods:
            </p>
            <ul className="list-disc ml-5 space-y-3 text-quantum-navy/80 text-sm">
              <li>
                <strong className="text-quantum-navy">Compression Tests:</strong> Genuinely random data cannot be efficiently compressed. This evaluates the output using Zlib, LZMA, Bzip2, and Gzip. A passing ratio is ≥ 0.999.
              </li>
              <li>
                <strong className="text-quantum-navy">TestU01:</strong> The official TestU01 1.2.3 C library. The Alphabit (17 tests) and Rabbit (40 tests) batteries, designed for fixed-length bit files, run on up to 2<sup>25</sup> bits. SmallCrush (15 tests) reads about 908 MB, so it only runs on inputs large enough that no data is reused.
              </li>
              <li>
                <strong className="text-quantum-navy">Dieharder:</strong> The 25 tests Dieharder itself rates &quot;Good&quot; (excluding rgb_minimum_distance, which fails even Dieharder&apos;s built-in AES generator when run alone), at standard settings. Most tests read hundreds of MB; when an input is too short, Dieharder would silently rewind and retest the same data, so those tests are reported as insufficient instead of counted. Runs natively on Linux and through WSL on Windows.
              </li>
            </ul>
          </div>
        </TerminalCard>
      </div>
    </div>
  );
}
