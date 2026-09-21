/**
 * AI SRE Console — Tier 1: Feature & Aesthetic Conformance Test Suite
 * Validates monochrome design discipline, typography hierarchy, 1px structural grid,
 * hero full-bleed layout, hover-reveal image bindings, and backend Express proxy routes.
 */

import fs from 'fs';
import path from 'path';
import { TestRunner, expect, readConsoleFile, scanSourceFiles, CONSOLE_ROOT } from './test_helpers';

export async function runTier1Tests(runner: TestRunner) {
  runner.suite('Tier 1: Feature Coverage & Palomino Aesthetic Conformance');

  // Test 1.1: Strict Monochrome Color Tokens in index.css
  await runner.test('T1.1: Strict monochrome color tokens and CSS variable discipline', () => {
    const cssContent = readConsoleFile('src/index.css');

    // Verify root & theme monochrome variables defined
    expect(cssContent).toContain('--color-mono-black: #000000;');
    expect(cssContent).toContain('--color-mono-dark: #050505;');
    expect(cssContent).toContain('--color-mono-white: #ffffff;');
    expect(cssContent).toContain('--bg-dark: #050505;');
    expect(cssContent).toContain('--text-primary: #ffffff;');
    expect(cssContent).toContain('--rule-light: #262626;');

    // Verify zero radius token enforcement
    expect(cssContent).toContain('--radius-xl: 0px;');
    expect(cssContent).toContain('--radius-2xl: 0px;');
    expect(cssContent).toContain('--radius-3xl: 0px;');
    expect(cssContent).toContain('border-radius: 0px !important;');

    // Verify monochrome button classes
    expect(cssContent).toContain('.btn-sre-mono');
    expect(cssContent).toContain('.btn-sre-outline-mono');
    expect(cssContent).toContain('background: #ffffff;');
    expect(cssContent).toContain('color: #000000;');
  });

  // Test 1.2: 1px Structural Grid Lines & 0px Border Radius
  await runner.test('T1.2: 1px structural grid border rules and layout geometry', () => {
    const appContent = readConsoleFile('src/App.tsx');
    const heroContent = readConsoleFile('src/components/sections/HeroSection.tsx');
    const safetyContent = readConsoleFile('src/components/sections/SafetyControl.tsx');
    const auditContent = readConsoleFile('src/components/sections/AuditTimeline.tsx');

    // Asserts 1px borders used between sections instead of shadow cards
    expect(heroContent).toContain('border-b border-[#E5E5E5]');
    expect(safetyContent).toContain('border-b border-[#E5E5E5]');
    expect(auditContent).toContain('border-b border-[#E5E5E5]');

    // Asserts main container uses monochrome background
    expect(appContent).toContain('bg-[#FFFFFF]');
    expect(appContent).toContain('text-[#050505]');
  });

  // Test 1.3: Typography Hierarchy & Font Imports
  await runner.test('T1.3: Bundled font imports and typography utility classes', () => {
    const htmlContent = readConsoleFile('index.html');
    const cssContent = readConsoleFile('src/index.css');

    // Active typography must not require a third-party network request.
    const entryContent = readConsoleFile('src/main.tsx');
    expect(entryContent).toContain('@fontsource-variable/inter-tight');
    expect(entryContent).toContain('@fontsource/inter');
    expect(entryContent).toContain('@fontsource/ibm-plex-mono');
    expect(htmlContent.includes('fonts.googleapis.com')).toBe(false);

    // Verify Typography utility classes
    expect(cssContent).toContain('.font-display');
    expect(cssContent).toContain('.font-mono');
    expect(cssContent).toContain('.label-caps');
    expect(cssContent).toContain('.prose-editorial');

    // Verify font weight and capitalization rules
    expect(cssContent).toContain("font-family: var(--font-display);");
    expect(cssContent).toContain("text-transform: uppercase;");
  });

  // Test 1.4: Cinematic Hero & Full-Bleed Infrastructure Imagery
  await runner.test('T1.4: Hero section full-bleed image references and asset directory inventory', () => {
    const heroContent = readConsoleFile('src/components/sections/HeroSection.tsx');
    
    // Verify hero image import and headline
    expect(heroContent).toContain("import heroImg from '../../assets/images/1_corridor.jpg';");
    expect(heroContent).toContain("INCIDENTS");
    expect(heroContent).toContain("DON'T WAIT");

    // Check all 8 image assets exist and are non-empty
    const imagesDir = path.join(CONSOLE_ROOT, 'src', 'assets', 'images');
    const expectedImages = [
      '1_corridor.jpg',
      '2_rack_leds.jpg',
      '3_cables.jpg',
      '4_engineer.jpg',
      '5_control_room.jpg',
      '6_hardware.jpg',
      '7_switch.jpg',
      '8_team.jpg',
    ];

    for (const imgName of expectedImages) {
      const fullImgPath = path.join(imagesDir, imgName);
      expect(fs.existsSync(fullImgPath)).toBe(true);
      const stat = fs.statSync(fullImgPath);
      expect(stat.size).toBeGreaterThan(100000); // Verify high resolution (>100KB)
    }
  });

  // Test 1.5: Hover-Reveal Image Interaction Bindings
  await runner.test('T1.5: Cursor-follow hover-reveal image previews in IncidentMarquee and SystemWorkflow', () => {
    const marqueeContent = readConsoleFile('src/components/sections/IncidentMarquee.tsx');
    const workflowContent = readConsoleFile('src/components/sections/SystemWorkflow.tsx');

    // Marquee hover reveal state and mouse tracking
    expect(marqueeContent).toContain('setHoverImage');
    expect(marqueeContent).toContain('cursorPos');
    expect(marqueeContent).toContain('onMouseMove={handleMouseMove}');
    expect(marqueeContent).toContain('onMouseLeave={() => setHoverImage(null)}');
    expect(marqueeContent).toContain('fixed pointer-events-none');
    expect(marqueeContent).toContain('6_hardware.jpg');

    // SystemWorkflow multi-stage GSAP scroll pinning
    expect(workflowContent).toContain('ScrollTrigger');
    expect(workflowContent).toContain('STAGES');
    expect(workflowContent).toContain('5_control_room.jpg');
    expect(workflowContent).toContain('3_cables.jpg');
    expect(workflowContent).toContain('7_switch.jpg');
  });

  // Test 1.6: Express Backend Proxy Routing
  await runner.test('T1.6: Express proxy server endpoint mappings in server.ts and typed api.ts client', () => {
    const serverContent = readConsoleFile('server.ts');
    const apiContent = readConsoleFile('src/services/api.ts');

    // Verify proxy routes in server.ts
    expect(serverContent).toContain("app.get('/api/health'");
    expect(serverContent).toContain("app.post('/api/rag/retrieve'");
    expect(serverContent).toContain("app.post('/api/tools/action'");
    expect(serverContent).toContain("app.get('/api/events/list'");
    expect(serverContent).toContain("app.post('/api/pipeline/run'");
    expect(serverContent).toContain("app.post('/api/ai/diagnose'");

    // Verify API client methods in services/api.ts
    expect(apiContent).toContain('getHealth()');
    expect(apiContent).toContain('retrieve(query: string, k: number');
    expect(apiContent).toContain('executeAction(action_type: string, params:');
    expect(apiContent).toContain('listEvents()');
    expect(apiContent).toContain('clearEvents()');
    expect(apiContent).toContain('getAuditLogs()');
    expect(apiContent).toContain('runPipeline(service: string, severity: string, symptom: string');
  });
}

// Standalone execution support
if (process.argv[1]?.endsWith('tier1_feature_coverage.test.ts')) {
  const runner = new TestRunner();
  runTier1Tests(runner).then(() => runner.printSummary());
}
