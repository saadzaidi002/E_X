"use client";
import React, { useEffect, useState } from 'react';

export function CustomCursor() {
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isPointer, setIsPointer] = useState(false);

  useEffect(() => {
    const updatePosition = (e: MouseEvent) => {
      // Don't show custom cursor on touch devices
      if (window.matchMedia("(hover: none) and (pointer: coarse)").matches) return;

      setPosition({ x: e.clientX, y: e.clientY });
      
      const target = e.target as HTMLElement;
      setIsPointer(
        window.getComputedStyle(target).cursor === 'pointer' ||
        target.tagName.toLowerCase() === 'button' ||
        target.tagName.toLowerCase() === 'a' ||
        target.closest('button') !== null ||
        target.closest('a') !== null
      );
    };

    window.addEventListener('mousemove', updatePosition);
    return () => window.removeEventListener('mousemove', updatePosition);
  }, []);

  return (
    <>
      <div 
        className="fixed top-0 left-0 w-8 h-8 rounded-full border-2 border-quantum-blue pointer-events-none z-[9999] transition-transform duration-100 ease-out"
        style={{ 
          transform: `translate(${position.x - 16}px, ${position.y - 16}px) scale(${isPointer ? 1.5 : 1})`,
          backgroundColor: isPointer ? 'rgba(0, 119, 182, 0.1)' : 'transparent'
        }}
      />
      <div 
        className="fixed top-0 left-0 w-2 h-2 rounded-full bg-quantum-navy pointer-events-none z-[9999]"
        style={{ 
          transform: `translate(${position.x - 4}px, ${position.y - 4}px)`
        }}
      />
    </>
  );
}
