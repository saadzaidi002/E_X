"use client";
import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export function Navbar() {
  const pathname = usePathname();

  const links = [
    { href: '/', label: 'Overview' },
    { href: '/analyze', label: 'Analyze' },
    { href: '/guide', label: 'Documentation' },
    { href: '/about', label: 'About' },
  ];

  return (
    <nav className="bg-white/80 backdrop-blur-md sticky top-0 z-40 border-b border-quantum-light shadow-sm">
      <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 min-w-max md:min-w-0">
          <Link href="/" className="flex items-center gap-3 group flex-shrink-0">
            <img src="/logo.png" alt="RNG Extractors Logo" className="h-8 sm:h-9 w-auto object-contain transition-transform group-hover:scale-105" />
            <span className="font-sans text-lg text-quantum-navy font-bold tracking-tight whitespace-nowrap hidden sm:block">
              RNG Extractors
            </span>
          </Link>
          <div className="flex items-center space-x-1 sm:space-x-2 overflow-x-auto no-scrollbar flex-shrink-0 ml-4">
            {links.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`font-sans text-sm font-semibold px-3 py-2 rounded-md transition-all duration-200 whitespace-nowrap ${
                    isActive
                      ? 'text-quantum-navy bg-quantum-light/30 shadow-sm'
                      : 'text-quantum-blue hover:text-quantum-navy hover:bg-quantum-light/20'
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
}
