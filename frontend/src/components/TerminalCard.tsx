"use client";
import React, { ReactNode } from 'react';
import { motion } from 'framer-motion';

interface TerminalCardProps {
  children: ReactNode;
  title?: string;
  className?: string;
  delay?: number;
}

export function TerminalCard({ children, title, className = '', delay = 0 }: TerminalCardProps) {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 300, damping: 24, delay }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      className={`relative bg-white rounded-xl border border-quantum-light shadow-sm hover:shadow-md hover:border-quantum-cyan transition-shadow duration-300 flex flex-col overflow-hidden ${className}`}
    >
      {title && (
        <div className="border-b border-quantum-light bg-quantum-bg/30 px-6 py-4 flex items-center justify-between flex-shrink-0">
          <h3 className="font-sans text-sm font-bold text-quantum-navy tracking-wide">{title}</h3>
        </div>
      )}
      <div className="p-6 text-quantum-blue text-base flex-1 min-h-0 w-full h-full relative">
        {children}
      </div>
    </motion.div>
  );
}
