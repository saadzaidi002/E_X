"use client";
import React from 'react';
import { motion } from 'framer-motion';
import { Database, ArrowDown, Activity, CheckCircle2, FileText, Download, Shield, Cpu, Binary, Fingerprint, Network, Rocket, BarChart2 } from 'lucide-react';

export function PipelineDiagram() {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.15,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { type: "spring" as const, stiffness: 300, damping: 24 },
    },
  };

  const categories = [
    {
      title: "Debiasing",
      icon: <Fingerprint className="w-5 h-5 mb-2" />,
      color: "bg-emerald-600 text-white shadow-emerald-500/20",
      itemColor: "bg-emerald-100/80 text-emerald-800 border-emerald-200",
      items: ["Von Neumann", "Peres", "Elias"]
    },
    {
      title: "Hash-Based",
      icon: <Shield className="w-5 h-5 mb-2" />,
      color: "bg-orange-500 text-white shadow-orange-500/20",
      itemColor: "bg-orange-100/80 text-orange-800 border-orange-200",
      items: ["SHA-256", "SHA-3", "BLAKE2"]
    },
    {
      title: "Matrix/Algebra",
      icon: <Network className="w-5 h-5 mb-2" />,
      color: "bg-fuchsia-600 text-white shadow-fuchsia-500/20",
      itemColor: "bg-fuchsia-100/80 text-fuchsia-800 border-fuchsia-200",
      items: ["Toeplitz", "Hadamard", "Polynomial"]
    },
    {
      title: "Mixing Methods",
      icon: <Activity className="w-5 h-5 mb-2" />,
      color: "bg-cyan-500 text-white shadow-cyan-500/20",
      itemColor: "bg-cyan-100/80 text-cyan-800 border-cyan-200",
      items: ["XOR", "Bit Shifting", "LFSR"]
    },
    {
      title: "Advanced Extractors",
      icon: <Rocket className="w-5 h-5 mb-2" />,
      color: "bg-indigo-600 text-white shadow-indigo-500/20",
      itemColor: "bg-indigo-100/80 text-indigo-800 border-indigo-200",
      items: ["Trevisan", "Quantum-Proof", "Goldreich-Levin", "Chor-Goldreich"]
    }
  ];

  return (
    <div className="w-full max-w-6xl mx-auto py-16 px-4">
      <div className="text-center mb-12">
        <h2 className="text-3xl md:text-4xl font-extrabold text-quantum-navy mb-4">Complete Architecture Pipeline</h2>
        <p className="text-quantum-blue font-medium max-w-2xl mx-auto">
          An end-to-end visualization of how raw bit streams are processed, extracted, and evaluated.
        </p>
      </div>

      <motion.div
        variants={containerVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-100px" }}
        className="flex flex-col items-center relative"
      >
        {/* Step 1: Input */}
        <motion.div variants={itemVariants} className="flex flex-col items-center relative z-10">
          <div className="bg-quantum-navy text-white px-8 py-4 rounded-xl shadow-lg border border-quantum-cyan/30 flex items-center gap-3">
            <Database className="w-6 h-6 text-quantum-cyan" />
            <span className="font-bold text-lg">Raw Bit Streams Input</span>
          </div>
          <div className="w-0.5 h-10 bg-quantum-light mt-2 relative">
            <ArrowDown className="absolute -bottom-3 -left-2.5 text-quantum-light w-5 h-5" />
          </div>
        </motion.div>

        {/* Step 2: Post-Processing Heading */}
        <motion.div variants={itemVariants} className="mt-8 mb-6 w-full text-center relative z-10">
          <div className="inline-block bg-white border border-quantum-light text-quantum-navy px-10 py-4 rounded-xl shadow-sm text-xl font-extrabold">
            Post-Processing Techniques
          </div>
        </motion.div>

        {/* Connection Line from Post-Processing to Columns */}
        <motion.div variants={itemVariants} className="w-full hidden md:block max-w-5xl relative z-0 h-10 -mt-10 mb-4 border-t-2 border-l-2 border-r-2 border-quantum-light rounded-t-xl opacity-50" />

        {/* Step 3: The 5 Categories */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 md:gap-3 w-full max-w-6xl relative z-10">
          {categories.map((cat, i) => (
            <motion.div key={i} variants={itemVariants} className="flex flex-col items-center">
              <div className={`w-full ${cat.color} rounded-xl p-4 flex flex-col items-center justify-center text-center shadow-lg transition-transform hover:-translate-y-1`}>
                {cat.icon}
                <span className="font-bold text-sm tracking-wide">{cat.title}</span>
              </div>
              
              <div className="w-0.5 h-6 bg-quantum-light my-1" />
              
              <div className="w-full flex flex-col gap-2">
                {cat.items.map((item, j) => (
                  <div key={j} className={`w-full text-center py-2.5 px-2 rounded-lg border ${cat.itemColor} text-sm font-semibold shadow-sm hover:shadow-md transition-shadow`}>
                    {item}
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Connection Line from Columns to Evaluation */}
        <motion.div variants={itemVariants} className="w-full hidden md:flex justify-center relative z-0 mt-6">
          <div className="w-full max-w-5xl h-10 border-b-2 border-l-2 border-r-2 border-quantum-light rounded-b-xl opacity-50 flex justify-center items-end relative">
            <div className="w-0.5 h-full bg-quantum-light absolute bottom-0 left-1/2 transform -translate-x-1/2 -mb-2" />
          </div>
        </motion.div>
        
        {/* Mobile connection to Evaluation */}
        <motion.div variants={itemVariants} className="w-0.5 h-12 bg-quantum-light mt-6 md:mt-2 relative block md:hidden">
            <ArrowDown className="absolute -bottom-3 -left-2.5 text-quantum-light w-5 h-5" />
        </motion.div>

        {/* Step 4: Evaluation & Metrics */}
        <motion.div variants={itemVariants} className="flex flex-col items-center relative z-10 md:mt-10 w-full max-w-6xl px-2">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6 w-full justify-center items-stretch">
            
            {/* NIST */}
            <div className="bg-white border-2 border-quantum-navy/20 px-6 py-5 rounded-xl shadow-lg flex items-center gap-4 group hover:border-quantum-navy/50 transition-colors">
              <div className="p-3 bg-quantum-light/30 rounded-lg text-quantum-navy flex-shrink-0">
                <CheckCircle2 className="w-7 h-7" />
              </div>
              <div>
                <div className="font-extrabold text-xl text-quantum-navy">NIST SP 800-22</div>
                <div className="text-quantum-blue text-sm font-bold">15 Statistical Tests</div>
              </div>
            </div>

            {/* TestU01 */}
            <div className="bg-white border-2 border-indigo-200 px-6 py-5 rounded-xl shadow-lg flex items-center gap-4 group hover:border-indigo-400 transition-colors">
              <div className="p-3 bg-indigo-50 rounded-lg text-indigo-600 flex-shrink-0">
                <Activity className="w-7 h-7" />
              </div>
              <div>
                <div className="font-extrabold text-xl text-quantum-navy">TestU01 Suite</div>
                <div className="text-quantum-blue text-sm font-bold">SmallCrush (15 Tests)</div>
              </div>
            </div>

            {/* Dieharder */}
            <div className="bg-white border-2 border-orange-200 px-6 py-5 rounded-xl shadow-lg flex items-center gap-4 group hover:border-orange-400 transition-colors">
              <div className="p-3 bg-orange-50 rounded-lg text-orange-600 flex-shrink-0">
                <Shield className="w-7 h-7" />
              </div>
              <div>
                <div className="font-extrabold text-xl text-quantum-navy">Dieharder</div>
                <div className="text-quantum-blue text-sm font-bold">Advanced Test Battery</div>
              </div>
            </div>

            {/* Compression */}
            <div className="bg-white border-2 border-emerald-200 px-6 py-5 rounded-xl shadow-lg flex items-center gap-4 group hover:border-emerald-400 transition-colors">
              <div className="p-3 bg-emerald-50 rounded-lg text-emerald-600 flex-shrink-0">
                <Network className="w-7 h-7" />
              </div>
              <div>
                <div className="font-extrabold text-xl text-quantum-navy">Compression Tests</div>
                <div className="text-quantum-blue text-sm font-bold">Gzip, LZMA, Bzip2, Deflate</div>
              </div>
            </div>

            {/* Performance Metrics */}
            <div className="bg-white border-2 border-quantum-cyan/30 px-6 py-5 rounded-xl shadow-lg flex items-center gap-4 group hover:border-quantum-cyan/70 transition-colors md:col-span-2 lg:col-span-2">
              <div className="p-3 bg-cyan-50 rounded-lg text-quantum-cyan flex-shrink-0">
                <BarChart2 className="w-7 h-7" />
              </div>
              <div>
                <div className="font-extrabold text-xl text-quantum-navy">Performance Metrics</div>
                <div className="text-quantum-blue text-xs font-semibold mt-1 leading-relaxed">
                  Shannon Entropy &bull; Min Entropy &bull; Efficiency &bull; Throughput &bull; Bit Rate &bull; Bias
                </div>
              </div>
            </div>
            
          </div>
          <div className="w-0.5 h-10 bg-quantum-light mt-4 relative">
            <ArrowDown className="absolute -bottom-3 -left-2.5 text-quantum-light w-5 h-5" />
          </div>
        </motion.div>

        {/* Step 5: Export */}
        <motion.div variants={itemVariants} className="flex gap-4 md:gap-8 relative z-10 mt-6 flex-col sm:flex-row w-full sm:w-auto justify-center">
          <div className="bg-white border border-quantum-light px-6 py-4 rounded-xl shadow-md flex items-center justify-center gap-3 hover:shadow-lg transition-shadow w-full sm:w-72">
            <Binary className="w-6 h-6 text-quantum-blue flex-shrink-0" />
            <span className="font-bold text-quantum-navy">Extracted Bit Streams</span>
          </div>
          
          <div className="bg-white border border-quantum-light px-6 py-4 rounded-xl shadow-md flex items-center justify-center gap-3 hover:shadow-lg transition-shadow w-full sm:w-72">
            <FileText className="w-6 h-6 text-red-500 flex-shrink-0" />
            <span className="font-bold text-quantum-navy">PDF Report</span>
          </div>
        </motion.div>

      </motion.div>
    </div>
  );
}
