"use client";
import React, { useEffect, useState } from 'react';

export function CustomCursor() {
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isPointer, setIsPointer] = useState(false);
  // Browsers send no mousemove events while a native scrollbar is being
  // dragged, so the custom cursor would freeze where the drag began (and the
  // real one is hidden). For the length of the drag, fall back to the native cursor.
  const [nativeFallback, setNativeFallback] = useState(false);

  useEffect(() => {
    const setNativeCursor = (on: boolean) => {
      document.documentElement.classList.toggle('native-cursor', on);
      setNativeFallback(on);
    };

    const updatePosition = (e: MouseEvent) => {
      // Don't show custom cursor on touch devices
      if (window.matchMedia("(hover: none) and (pointer: coarse)").matches) return;

      // Mouse events are flowing again, so any scrollbar drag has ended.
      if (document.documentElement.classList.contains('native-cursor')) setNativeCursor(false);

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

    // A press that lands outside the target's content box (clientWidth/Height
    // exclude scrollbars) is a press on its scrollbar.
    const onMouseDown = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const rect = target.getBoundingClientRect();
      const onScrollbar = target === document.documentElement
        ? e.clientX >= target.clientWidth || e.clientY >= target.clientHeight
        : e.clientX >= rect.left + target.clientLeft + target.clientWidth ||
          e.clientY >= rect.top + target.clientTop + target.clientHeight;
      if (onScrollbar) setNativeCursor(true);
    };

    window.addEventListener('mousemove', updatePosition);
    window.addEventListener('mousedown', onMouseDown, true);
    return () => {
      window.removeEventListener('mousemove', updatePosition);
      window.removeEventListener('mousedown', onMouseDown, true);
      document.documentElement.classList.remove('native-cursor');
    };
  }, []);

  if (nativeFallback) return null;

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
