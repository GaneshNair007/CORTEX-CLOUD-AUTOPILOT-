import React, { useState } from 'react';
import { Menu, X, Shield, Terminal } from 'lucide-react';

interface NavbarProps {
  isBackendOnline: boolean;
  onLaunchConsole?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ isBackendOnline, onLaunchConsole }) => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const scrollToSection = (id: string) => {
    setIsMobileMenuOpen(false);
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <nav className="sticky top-0 left-0 w-full bg-[#000000] text-[#FFFFFF] border-b border-[#262626] z-50 transition-all backdrop-blur-md bg-opacity-95">
      <div className="container-full h-24 md:h-28 flex items-center justify-between px-6 lg:px-12">
        {/* Brand Label */}
        <div className="flex items-center gap-6">
          <div 
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            className="cursor-pointer group flex items-center gap-4 select-none"
          >
            <span className="font-mono text-sm md:text-base font-bold text-[#888888] tracking-widest hidden sm:inline-block">
              [SRE::DEFENSE]
            </span>
            <span className="font-display text-2xl md:text-4xl font-black tracking-tight text-[#FFFFFF] group-hover:text-[#A3A3A3] transition-colors">
              AI SRE<span className="text-[#555555]">/</span>CONSOLE
            </span>
          </div>
        </div>

        {/* Desktop Navigation Links */}
        <div className="hidden lg:flex items-center gap-8 xl:gap-12 font-mono text-sm xl:text-base font-bold tracking-[0.15em] text-[#A3A3A3]">
          <button 
            onClick={() => scrollToSection('simulator')} 
            className="hover:text-[#FFFFFF] transition-colors flex items-center gap-1.5 py-2 relative after:content-[''] after:absolute after:bottom-0 after:left-0 after:w-0 after:h-[2px] after:bg-[#FFFFFF] hover:after:w-full after:transition-all"
          >
            <span className="text-[#555555]">01.</span> SIMULATOR
          </button>
          <button 
            onClick={() => scrollToSection('workflow')} 
            className="hover:text-[#FFFFFF] transition-colors flex items-center gap-1.5 py-2 relative after:content-[''] after:absolute after:bottom-0 after:left-0 after:w-0 after:h-[2px] after:bg-[#FFFFFF] hover:after:w-full after:transition-all"
          >
            <span className="text-[#555555]">02.</span> WORKFLOW
          </button>
          <button 
            onClick={() => scrollToSection('evidence')} 
            className="hover:text-[#FFFFFF] transition-colors flex items-center gap-1.5 py-2 relative after:content-[''] after:absolute after:bottom-0 after:left-0 after:w-0 after:h-[2px] after:bg-[#FFFFFF] hover:after:w-full after:transition-all"
          >
            <span className="text-[#555555]">03.</span> EVIDENCE
          </button>
          <button 
            onClick={() => scrollToSection('safety')} 
            className="hover:text-[#FFFFFF] transition-colors flex items-center gap-1.5 py-2 relative after:content-[''] after:absolute after:bottom-0 after:left-0 after:w-0 after:h-[2px] after:bg-[#FFFFFF] hover:after:w-full after:transition-all"
          >
            <span className="text-[#555555]">04.</span> SAFETY
          </button>
          <button 
            onClick={() => scrollToSection('audit')} 
            className="hover:text-[#FFFFFF] transition-colors flex items-center gap-1.5 py-2 relative after:content-[''] after:absolute after:bottom-0 after:left-0 after:w-0 after:h-[2px] after:bg-[#FFFFFF] hover:after:w-full after:transition-all"
          >
            <span className="text-[#555555]">05.</span> AUDIT
          </button>
        </div>

        {/* Right Telemetry & Status Readout & Console Launch */}
        <div className="flex items-center gap-4 lg:gap-6">
          <div className="hidden md:flex items-center gap-3 font-mono text-sm">
            <span className="text-[#737373] tracking-widest uppercase">
              STATUS:
            </span>
            <div className={`px-3 py-1.5 border transition-all duration-300 font-mono font-bold tracking-wider flex items-center gap-2 ${
              isBackendOnline 
                ? 'bg-[#FFFFFF] text-[#000000] border-[#FFFFFF]' 
                : 'bg-[#0A0A0A] text-[#888888] border-[#333333] animate-pulse'
            }`}>
              <div className={`w-2 h-2 ${isBackendOnline ? 'bg-[#000000]' : 'bg-[#888888]'}`} />
              <span>{isBackendOnline ? 'OPTIMAL' : 'OFFLINE'}</span>
            </div>
          </div>

          <button
            onClick={() => {
              if (onLaunchConsole) onLaunchConsole();
              else window.location.hash = '#/console';
            }}
            className="px-4 py-2 bg-[#fafafa] hover:bg-white text-[#09090b] font-mono font-bold text-xs tracking-wider uppercase rounded flex items-center gap-2 transition-all cursor-pointer shadow-[0_0_15px_rgba(255,255,255,0.2)]"
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>AUTOPILOT CONSOLE</span>
          </button>

          {/* Mobile Menu Button */}
          <button 
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="lg:hidden text-[#FFFFFF] p-3 border border-[#262626] hover:bg-[#121212] transition-colors"
            aria-label="Toggle Menu"
          >
            {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu Overlay */}
      {isMobileMenuOpen && (
        <div className="lg:hidden border-t border-[#262626] bg-[#050505] p-6 space-y-4 font-mono text-sm">
          <button 
            onClick={() => scrollToSection('simulator')} 
            className="block w-full text-left py-2 text-[#D4D4D4] hover:text-[#FFFFFF] border-b border-[#1A1A1A]"
          >
            01. SIMULATOR
          </button>
          <button 
            onClick={() => scrollToSection('workflow')} 
            className="block w-full text-left py-2 text-[#D4D4D4] hover:text-[#FFFFFF] border-b border-[#1A1A1A]"
          >
            02. WORKFLOW
          </button>
          <button 
            onClick={() => scrollToSection('evidence')} 
            className="block w-full text-left py-2 text-[#D4D4D4] hover:text-[#FFFFFF] border-b border-[#1A1A1A]"
          >
            03. EVIDENCE
          </button>
          <button 
            onClick={() => scrollToSection('safety')} 
            className="block w-full text-left py-2 text-[#D4D4D4] hover:text-[#FFFFFF] border-b border-[#1A1A1A]"
          >
            04. SAFETY
          </button>
          <button 
            onClick={() => scrollToSection('audit')} 
            className="block w-full text-left py-2 text-[#D4D4D4] hover:text-[#FFFFFF] border-b border-[#1A1A1A]"
          >
            05. AUDIT
          </button>
          <div className="pt-2 flex items-center justify-between text-xs text-[#737373]">
            <span>SYSTEM STATUS:</span>
            <span className={isBackendOnline ? 'text-[#FFFFFF] font-bold' : 'text-[#888888]'}>
              {isBackendOnline ? '[OPTIMAL]' : '[OFFLINE]'}
            </span>
          </div>
        </div>
      )}
    </nav>
  );
};

