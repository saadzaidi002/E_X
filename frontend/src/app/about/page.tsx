import React from 'react';
import { TerminalCard } from '@/components/TerminalCard';
import { Building2, GraduationCap, Users } from 'lucide-react';

export default function AboutPage() {
  return (
    <div className="max-w-4xl mx-auto animate-in fade-in duration-500 pb-12">
      <div className="mb-8 border-b border-quantum-light pb-6">
        <h1 className="text-3xl font-sans font-bold text-quantum-navy">About the Project</h1>
        <p className="text-quantum-blue font-semibold mt-2">Academic research background and team information.</p>
      </div>

      <div className="space-y-8">
        <TerminalCard delay={0.2} title="Project Abstract">
          <p className="text-quantum-navy/80 font-medium leading-relaxed text-base">
            RNG Extractors is an academic research platform developed to evaluate and enhance the quality of random number generators from any source. By applying 20 distinct software extraction algorithms, the platform standardizes the process of removing bias and improving the min-entropy of raw bitstreams. The extracted outputs are rigorously evaluated against the industry-standard NIST SP 800-22 statistical test suite to verify their cryptographic viability. High-quality, unbiased random numbers are foundational to modern cryptography, ensuring the generation of secure cryptographic keys, robust digital signatures, and resilient encryption protocols that are strictly protected against predictive attacks.
          </p>
        </TerminalCard>

        <div className="flex flex-col items-center justify-center p-8 bg-white border border-quantum-light shadow-sm rounded-xl text-center">
          <img src="/ned-logo.png" alt="NED University Logo" className="w-24 h-24 object-contain mb-4" />
          <h2 className="text-xl font-bold text-quantum-navy">NED University of Engineering and Technology</h2>
          <p className="text-quantum-navy/70 font-semibold mt-2">Department of Physics &amp; Centre for Quantum Technologies (CQT)</p>
        </div>

        <div>
          <div className="flex items-center gap-2 mb-4 px-1">
            <Users className="w-5 h-5 text-quantum-blue" />
            <h2 className="text-lg font-bold text-quantum-navy">Research Team</h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="border border-quantum-light bg-white p-6 rounded-lg shadow-sm hover:border-quantum-blue hover:shadow-md transition-all">
              <h3 className="font-bold text-quantum-navy text-lg">Dr. Roohi Zafar</h3>
              <p className="text-quantum-blue font-semibold text-sm mt-1">Supervisor</p>
              <div className="mt-4 flex items-center gap-2 text-sm text-quantum-navy/70 font-semibold">
                <GraduationCap className="w-4 h-4 text-quantum-cyan" /> Department of Physics
              </div>
            </div>

            <div className="border border-quantum-light bg-white p-6 rounded-lg shadow-sm hover:border-quantum-blue hover:shadow-md transition-all">
              <h3 className="font-bold text-quantum-navy text-lg">Dr. Muhammad Kamran</h3>
              <p className="text-quantum-blue font-semibold text-sm mt-1">Co-Supervisor &amp; Co-PI, CQT</p>
              <div className="mt-4 flex items-center gap-2 text-sm text-quantum-navy/70 font-semibold">
                <GraduationCap className="w-4 h-4 text-quantum-cyan" /> Department of CS&amp;IT
              </div>
            </div>

            <div className="border border-quantum-light bg-white p-6 rounded-lg shadow-sm hover:border-quantum-blue hover:shadow-md transition-all">
              <h3 className="font-bold text-quantum-navy text-lg">Dr. Tahir Malik</h3>
              <p className="text-quantum-blue font-semibold text-sm mt-1">Co-Supervisor &amp; Co-PI, CQT</p>
              <div className="mt-4 flex items-center gap-2 text-sm text-quantum-navy/70 font-semibold">
                <GraduationCap className="w-4 h-4 text-quantum-cyan" /> Department of Telecommunications Engineering
              </div>
            </div>

            {/* Removed the persistent highlight state, now just hovers like the rest */}
            <div className="border border-quantum-light bg-white p-6 rounded-lg shadow-sm hover:border-quantum-blue hover:shadow-md transition-all group relative overflow-hidden">
              <div className="absolute top-0 left-0 w-1 h-full bg-quantum-blue opacity-0 group-hover:opacity-100 transition-opacity"></div>
              <h3 className="font-bold text-quantum-navy text-lg">Syed Muhammad Saad Hussain Zaidi</h3>
              <p className="text-quantum-blue font-semibold text-sm mt-1">Researcher &amp; Core Developer</p>
              <div className="mt-4 flex items-center gap-2 text-sm text-quantum-navy/70 font-semibold">
                <GraduationCap className="w-4 h-4 text-quantum-cyan" /> Department of Physics (Batch 2022)
              </div>
            </div>
          </div>
        </div>

        <div className="mt-8 border-t border-quantum-light pt-8">
          <div className="flex flex-col items-center justify-center text-center">
            <h3 className="text-base font-bold text-quantum-navy mb-4">Acknowledgements</h3>
            <img src="/cqt-logo.png" alt="CQT Logo" className="w-16 h-16 object-contain mb-3 opacity-80" />
            <p className="text-quantum-navy/80 text-sm max-w-2xl">
              <span className="font-semibold">Dr. Muhammad Mubashir Khan</span> — Chairman &amp; Director, Centre for Quantum Technologies (CQT),<br />
              NED University of Engineering &amp; Technology.
            </p>
            <p className="text-quantum-navy/70 text-xs mt-2 italic">
              "We acknowledge the institutional support of the Centre for Quantum Technologies (CQT) under the chairmanship of Dr. Muhammad Mubashir Khan."
            </p>
          </div>
        </div>
        
        <div className="text-center pt-10">
          <p className="text-sm font-bold text-quantum-navy/50">
            A research collaboration between the Department of Physics, NED University of Engineering & Technology, and the Centre for Quantum Technologies (CQT).
          </p>
        </div>
      </div>
    </div>
  );
}
