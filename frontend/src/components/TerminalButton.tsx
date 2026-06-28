"use client";
import React from 'react';
import { LucideIcon } from 'lucide-react';
import { motion, HTMLMotionProps } from 'framer-motion';

interface TerminalButtonProps extends HTMLMotionProps<"button"> {
  variant?: 'primary' | 'secondary' | 'danger';
  icon?: LucideIcon;
  fullWidth?: boolean;
  children?: React.ReactNode;
}

export function TerminalButton({ 
  children, 
  variant = 'primary', 
  icon: Icon,
  fullWidth = false,
  className = '',
  disabled,
  ...props 
}: TerminalButtonProps) {
  
  const baseStyles = "relative font-sans text-sm font-bold tracking-wide transition-colors duration-200 flex items-center justify-center rounded-lg shadow-sm";
  
  const variants = {
    primary: "bg-quantum-navy text-white hover:bg-quantum-blue hover:shadow-md border border-transparent",
    secondary: "bg-white border border-quantum-cyan text-quantum-navy hover:bg-quantum-light/20 hover:text-quantum-navy",
    danger: "bg-red-50 border border-red-200 text-red-600 hover:bg-red-100 hover:text-red-700",
  };

  const disabledStyles = "opacity-50 cursor-not-allowed hover:bg-transparent pointer-events-none shadow-none";

  return (
    <motion.button 
      whileHover={{ y: -2 }}
      whileTap={{ scale: 0.97 }}
      transition={{ type: "spring", stiffness: 400, damping: 17 }}
      className={`
        ${baseStyles} 
        ${variants[variant]} 
        ${fullWidth ? 'w-full' : 'px-6'} 
        ${disabled ? disabledStyles : ''}
        py-3 
        ${className}
      `}
      disabled={disabled}
      {...props}
    >
      {Icon && <Icon className="w-4 h-4 mr-2 opacity-90" />}
      <span>{children}</span>
    </motion.button>
  );
}
