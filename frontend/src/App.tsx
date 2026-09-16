import React, { useState, useEffect } from 'react';
import Lenis from 'lenis';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { EntryLoader } from './components/sections/EntryLoader';
import { Navbar } from './components/layout/Navbar';
import { HeroSection } from './components/sections/HeroSection';
import { IncidentMarquee } from './components/sections/IncidentMarquee';
import { SystemWorkflow } from './components/sections/SystemWorkflow';
import { IncidentSimulator } from './components/sections/IncidentSimulator';
import { EvidenceRetrieval } from './components/sections/EvidenceRetrieval';
import { SafetyControl } from './components/sections/SafetyControl';
import { AuditTimeline } from './components/sections/AuditTimeline';
import { ClosingSection } from './components/sections/ClosingSection';
import { CortexSidebar, ActiveRoute } from './components/layout/CortexSidebar';
import { CortexHeader } from './components/layout/CortexHeader';
import { CommandPalette } from './components/layout/CommandPalette';
import { ServiceInspectorDrawer } from './components/modals/ServiceInspectorDrawer';
import { IncidentDetailDrawer } from './components/modals/IncidentDetailDrawer';
import { CommandCenterView } from './components/console/CommandCenterView';
import { IncidentsView } from './components/views/IncidentsView';
import { TopologyView } from './components/views/TopologyView';
import { PredictionsView } from './components/views/PredictionsView';
import { OptimizerView } from './components/views/OptimizerView';
import { IncidentMemoryView } from './components/views/IncidentMemoryView';
import { CortexGuardView } from './components/views/CortexGuardView';
import { DigitalTwinView } from './components/views/DigitalTwinView';
import { ApprovalsView } from './components/views/ApprovalsView';
import { PoliciesView } from './components/views/PoliciesView';
import { ChaosLabView } from './components/views/ChaosLabView';
import { ReliabilityView } from './components/views/ReliabilityView';
import { CostView } from './components/views/CostView';
import { SustainabilityView } from './components/views/SustainabilityView';
import { AuditLedgerView } from './components/views/AuditLedgerView';
import { EvaluationView } from './components/views/EvaluationView';
import { CloudProvidersView } from './components/views/CloudProvidersView';
import { DemoView } from './components/views/DemoView';
import { api } from './services/api';
import { ServiceHealthItem } from './types';
import { AlertTriangle } from 'lucide-react';

gsap.registerPlugin(ScrollTrigger);

export function App() {
  const [isLoaderComplete, setIsLoaderComplete] = useState<boolean>(false);
  const [isBackendOnline, setIsBackendOnline] = useState<boolean>(true);

  // Router State
  const parseRoute = (): ActiveRoute => {
    const hash = window.location.hash.replace(/^#\/?/, '');
    const validRoutes: ActiveRoute[] = [
      'landing', 'console', 'incidents', 'topology', 'predictions',
      'optimizer', 'memory', 'cortex', 'simulator', 'approvals',
      'policies', 'chaos', 'reliability', 'cost', 'sustainability',
      'audit', 'evaluation', 'providers', 'demo'
    ];
    return validRoutes.includes(hash as ActiveRoute) ? (hash as ActiveRoute) : 'landing';
  };

  const [currentRoute, setCurrentRoute] = useState<ActiveRoute>(parseRoute());
  const [autonomyLevel, setAutonomyLevel] = useState<number>(2); // L2 GUARDED
  const [killSwitchEngaged, setKillSwitchEngaged] = useState<boolean>(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState<boolean>(false);
  const [selectedService, setSelectedService] = useState<ServiceHealthItem | null>(null);
  const [selectedIncident, setSelectedIncident] = useState<any | null>(null);

  // Sync hash changes
  useEffect(() => {
    const handleHashChange = () => {
      setCurrentRoute(parseRoute());
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const handleRouteChange = (newRoute: ActiveRoute) => {
    setCurrentRoute(newRoute);
    window.location.hash = newRoute === 'landing' ? '#/' : `#/${newRoute}`;
    window.scrollTo({ top: 0, behavior: 'instant' });
  };

  // Keyboard shortcut Cmd/Ctrl + K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Initialize Lenis smooth scroll for landing page
  useEffect(() => {
    if (currentRoute !== 'landing') return;

    const lenis = new Lenis({
      duration: 1.2,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
    });

    lenis.on('scroll', ScrollTrigger.update);

    const updateLenis = (time: number) => {
      lenis.raf(time * 1000);
    };

    gsap.ticker.add(updateLenis);
    gsap.ticker.lagSmoothing(0);

    return () => {
      lenis.destroy();
      gsap.ticker.remove(updateLenis);
    };
  }, [currentRoute]);

  // Poll FastAPI backend health
  useEffect(() => {
    const checkHealth = async () => {
      try {
        await api.getHealth();
        setIsBackendOnline(true);
      } catch (e) {
        setIsBackendOnline(false);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleOpenIncident = (incidentId: string) => {
    setSelectedIncident({
      id: incidentId,
      service: 'payment-api',
      severity: 'HIGH',
      symptom: 'p95 latency spike 840ms with 4.8% 504 Gateway Timeouts',
      rootCause: 'Database connection pool starvation triggered by v4.6 unindexed schema query',
      confidence: 0.94,
      decision: 'CONSTRAIN_AND_SCALE',
      action: 'scale_replicas (6 → 9)',
      timeline: [
        { time: '14:12:00', event: 'Anomaly flagged by Prometheus probe' },
        { time: '14:12:15', event: 'RAG retrieved Runbook RB-001 (0.94 score)' },
        { time: '14:12:28', event: 'Counterfactual Digital Twin confirmed recovery' },
        { time: '14:12:35', event: 'CORTEX Guard approved action under L2' }
      ]
    });
  };

  return (
    <div className="min-h-screen bg-[#09090b] text-[#fafafa] font-sans antialiased flex flex-col selection:bg-[#27272a] selection:text-[#fafafa]">
      {/* Global Command Palette */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onNavigate={handleRouteChange}
      />

      {/* Global Service Inspector Drawer */}
      <ServiceInspectorDrawer
        isOpen={Boolean(selectedService)}
        onClose={() => setSelectedService(null)}
        service={selectedService}
        onSimulateAction={(act, p) => handleRouteChange('simulator')}
      />

      {/* Global Incident Drawer */}
      <IncidentDetailDrawer
        isOpen={Boolean(selectedIncident)}
        onClose={() => setSelectedIncident(null)}
        incident={selectedIncident}
      />

      {/* LAYER 1: PUBLIC PRODUCT STORY (LANDING PAGE) */}
      {currentRoute === 'landing' ? (
        <div className="w-full bg-[#FFFFFF] text-[#050505] selection:bg-[#050505] selection:text-[#FFFFFF]">
          {/* Boot Loader Sequence */}
          {!isLoaderComplete && (
            <EntryLoader onComplete={() => {
              setIsLoaderComplete(true);
              setTimeout(() => ScrollTrigger.refresh(), 50);
            }} />
          )}

          {/* Navigation Header with Autopilot Console Switch */}
          <Navbar
            isBackendOnline={isBackendOnline}
            onLaunchConsole={() => handleRouteChange('console')}
          />

          {/* Backend Offline Warning Banner */}
          {!isBackendOnline && (
            <div className="fixed top-[96px] left-0 right-0 bg-[#050505] text-[#FFFFFF] px-6 py-2.5 flex items-center justify-between font-mono text-sm z-40 border-b border-[#333333]">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-[#FFFFFF]" />
                <span>BACKEND OFFLINE — START <code className="bg-[#141414] px-1.5 py-0.5 border border-white/30">python api_server.py</code> TO RUN PIPELINE & RAG RETRIEVAL</span>
              </div>
              <div className="text-[12px] uppercase text-[#999999] hidden md:block">
                FASTAPI SERVER PORT 8000
              </div>
            </div>
          )}

          {/* Main Single-Page Narrative Experience */}
          <main className="w-full flex-1">
            <HeroSection />
            <IncidentMarquee />
            <SystemWorkflow />
            <IncidentSimulator />
            <EvidenceRetrieval />
            <SafetyControl />
            <AuditTimeline />
            <ClosingSection />
          </main>
        </div>
      ) : (
        /* LAYER 2 & LAYER 3: OPERATIONS COCKPIT & DEEP ANALYSIS SUITES */
        <div className="flex h-screen w-full overflow-hidden bg-[#09090b]">
          {/* Enterprise Sidebar Navigation */}
          <CortexSidebar
            currentRoute={currentRoute}
            onRouteChange={handleRouteChange}
            pendingApprovalsCount={2}
            activeIncidentsCount={1}
          />

          {/* Main Operations Work Area */}
          <div className="flex-1 flex flex-col h-full overflow-hidden">
            {/* Top Control Plane Header */}
            <CortexHeader
              currentRoute={currentRoute}
              onRouteChange={handleRouteChange}
              onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
              autonomyLevel={autonomyLevel}
              onAutonomyChange={setAutonomyLevel}
              killSwitchEngaged={killSwitchEngaged}
              onKillSwitchToggle={setKillSwitchEngaged}
            />

            {/* Dynamic View Router */}
            <div className="flex-1 overflow-hidden flex flex-col">
              {currentRoute === 'console' && (
                <CommandCenterView
                  onSelectService={setSelectedService}
                  onSelectIncident={handleOpenIncident}
                  onNavigateRoute={handleRouteChange}
                  autonomyLevel={autonomyLevel}
                  killSwitchEngaged={killSwitchEngaged}
                />
              )}
              {currentRoute === 'incidents' && (
                <IncidentsView onSelectIncident={handleOpenIncident} />
              )}
              {currentRoute === 'topology' && (
                <TopologyView onSelectService={setSelectedService} />
              )}
              {currentRoute === 'predictions' && <PredictionsView />}
              {currentRoute === 'optimizer' && <OptimizerView />}
              {currentRoute === 'memory' && <IncidentMemoryView />}
              {currentRoute === 'cortex' && (
                <CortexGuardView
                  autonomyLevel={autonomyLevel}
                  onAutonomyChange={setAutonomyLevel}
                  killSwitchEngaged={killSwitchEngaged}
                  onKillSwitchToggle={setKillSwitchEngaged}
                />
              )}
              {currentRoute === 'simulator' && <DigitalTwinView />}
              {currentRoute === 'approvals' && <ApprovalsView />}
              {currentRoute === 'policies' && <PoliciesView />}
              {currentRoute === 'chaos' && <ChaosLabView />}
              {currentRoute === 'reliability' && <ReliabilityView />}
              {currentRoute === 'cost' && <CostView />}
              {currentRoute === 'sustainability' && <SustainabilityView />}
              {currentRoute === 'audit' && <AuditLedgerView />}
              {currentRoute === 'evaluation' && <EvaluationView />}
              {currentRoute === 'providers' && <CloudProvidersView />}
              {currentRoute === 'demo' && <DemoView />}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
