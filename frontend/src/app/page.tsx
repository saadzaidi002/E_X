"use client";
import React from 'react';
import { useRouter } from 'next/navigation';
import { TerminalButton } from '@/components/TerminalButton';
import { TerminalCard } from '@/components/TerminalCard';
import { Shield, Activity, BarChart2, Cpu } from 'lucide-react';
import { motion } from 'framer-motion';
import { PipelineDiagram } from '@/components/PipelineDiagram';

export default function Home() {
  const router = useRouter();

  return (
    <div className="flex flex-col gap-24 w-full">
      <div className="flex flex-col lg:flex-row items-center justify-between min-h-[80vh] gap-12 lg:gap-8 w-full">
        {/* Left Column: Text & CTA */}
      <motion.div 
        initial={{ opacity: 0, x: -30 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ type: "spring", stiffness: 200, damping: 20, delay: 0.1 }}
        className="flex-1 space-y-8 max-w-2xl pt-10 lg:pt-0"
      >
        <h1 className="text-5xl sm:text-6xl lg:text-7xl font-sans font-extrabold text-quantum-navy tracking-tight leading-tight">
          Randomness <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-quantum-blue to-quantum-cyan">
            Extraction & Analysis
          </span>
        </h1>
        
        <p className="text-quantum-blue leading-relaxed font-sans text-lg sm:text-xl">
          Process raw bit streams from random number generators through 20 specialized extraction algorithms, evaluated strictly against the NIST SP 800-22 cryptographic test suite.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 pt-4">
          <TerminalButton 
            onClick={() => router.push('/analyze')}
            icon={Activity}
            className="px-8 py-4 text-base"
          >
            Start Analysis
          </TerminalButton>
          <TerminalButton 
            onClick={() => router.push('/guide')}
            variant="secondary"
            className="px-8 py-4 text-base"
          >
            Read Documentation
          </TerminalButton>
        </div>
      </motion.div>

      {/* Right Column: Staggered Visuals */}
      <div className="flex-1 relative w-full max-w-lg hidden md:block mt-12 lg:mt-0 h-[500px]">
        {/* Card 1 */}
        <motion.div 
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 24, delay: 0.2 }}
          className="absolute top-0 right-0 w-64 z-30"
        >
          <TerminalCard className="flex flex-col p-6 shadow-lg border-quantum-cyan/50">
            <div className="p-3 bg-quantum-light/30 rounded-lg mb-4 w-fit text-quantum-navy">
              <Cpu className="w-6 h-6" />
            </div>
            <div className="text-4xl font-sans font-extrabold text-quantum-navy mb-1">20</div>
            <div className="text-sm text-quantum-blue font-bold">Extraction Methods</div>
          </TerminalCard>
        </motion.div>

        {/* Card 2 */}
        <motion.div 
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 24, delay: 0.35 }}
          className="absolute top-32 left-0 w-64 z-20"
        >
          <TerminalCard className="flex flex-col p-6 shadow-lg border-quantum-blue/30 bg-white/95 backdrop-blur-md transform -translate-y-4">
            <div className="p-3 bg-quantum-light/30 rounded-lg mb-4 w-fit text-quantum-navy">
              <Shield className="w-6 h-6" />
            </div>
            <div className="text-4xl font-sans font-extrabold text-quantum-navy mb-1">4</div>
            <div className="text-sm text-quantum-blue font-bold">Validation Suites</div>
            <div className="text-[11px] text-quantum-navy/70 font-semibold mt-1">NIST, TestU01, Dieharder, Compression</div>
          </TerminalCard>
        </motion.div>

        {/* Card 3 */}
        <motion.div 
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 24, delay: 0.5 }}
          className="absolute top-64 right-10 w-64 z-10"
        >
          <TerminalCard className="flex flex-col p-6 shadow-lg border-quantum-light/50 bg-white/90 backdrop-blur-md">
            <div className="p-3 bg-quantum-light/30 rounded-lg mb-4 w-fit text-quantum-navy">
              <BarChart2 className="w-6 h-6" />
            </div>
            <div className="text-4xl font-sans font-extrabold text-quantum-navy mb-1">Live</div>
            <div className="text-sm text-quantum-blue font-bold">Comparative Reports</div>
          </TerminalCard>
        </motion.div>
      </div>
      
      {/* Mobile view for cards */}
      <div className="md:hidden grid grid-cols-1 gap-6 w-full mt-8">
        <TerminalCard delay={0.2} className="flex flex-col p-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-quantum-light/30 rounded-lg text-quantum-navy">
              <Cpu className="w-6 h-6" />
            </div>
            <div>
              <div className="text-2xl font-sans font-extrabold text-quantum-navy">20</div>
              <div className="text-sm text-quantum-blue font-bold">Extraction Methods</div>
            </div>
          </div>
        </TerminalCard>
        <TerminalCard delay={0.3} className="flex flex-col p-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-quantum-light/30 rounded-lg text-quantum-navy">
              <Shield className="w-6 h-6" />
            </div>
            <div>
              <div className="text-2xl font-sans font-extrabold text-quantum-navy">4</div>
              <div className="text-sm text-quantum-blue font-bold">Validation Suites</div>
              <div className="text-[11px] text-quantum-navy/70 font-semibold mt-0.5">NIST, TestU01, Dieharder, Compression</div>
            </div>
          </div>
        </TerminalCard>
      </div>
      </div>
      
      {/* Pipeline Diagram */}
      <PipelineDiagram />
    </div>
  );
}
