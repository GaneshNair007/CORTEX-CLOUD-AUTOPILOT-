import React, { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { MotionPathPlugin } from 'gsap/MotionPathPlugin';
import img1 from '../../assets/images/1_corridor.jpg';
import img2 from '../../assets/images/4_engineer.jpg';
import img3 from '../../assets/images/6_hardware.jpg';
import img4 from '../../assets/images/2_rack_leds.jpg';
import img5 from '../../assets/images/7_switch.jpg';
import img6 from '../../assets/images/5_control_room.jpg';
import img7 from '../../assets/images/8_team.jpg';

gsap.registerPlugin(ScrollTrigger, MotionPathPlugin);

const NODES = [
  { id: 'incident', title: 'INCIDENT', desc: 'Symptom payload, service target & severity tier ingested.', img: img1 },
  { id: 'embeddings', title: 'EMBEDDINGS', desc: 'all-MiniLM-L6-v2 encodes symptom to dense vector.', img: img2 },
  { id: 'chromadb', title: 'CHROMADB', desc: 'Vector store queried against 35 operational documents.', img: img3 },
  { id: 'retrieval', title: 'RETRIEVAL', desc: 'Cosine similarity ranking returns top 5 runbooks.', img: img4 },
  { id: 'action', title: 'CONTROLLED ACTION', desc: 'Agent strictly selects from 8 predefined safe functions.', img: img5 },
  { id: 'eventbus', title: 'EVENT BUS', desc: 'Timeline payload emitted to system event listeners.', img: img6 },
  { id: 'audit', title: 'AUDIT', desc: 'Immutable JSONL append for absolute accountability.', img: img7 },
];

export const ArchitectureStory: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const pathRef = useRef<SVGPathElement>(null);
  const signalRef = useRef<SVGRectElement>(null);
  const detailRefs = useRef<(HTMLDivElement | null)[]>([]);
  const imageRefs = useRef<(HTMLImageElement | null)[]>([]);

  useEffect(() => {
    const ctx = gsap.context(() => {
      if (!containerRef.current || !pathRef.current || !signalRef.current) return;

      const pathLength = pathRef.current.getTotalLength();
      gsap.set(pathRef.current, { strokeDasharray: pathLength, strokeDashoffset: pathLength });
      gsap.set(detailRefs.current, { opacity: 0.1, y: 10 });
      gsap.set(imageRefs.current, { opacity: 0, scale: 1.05 });
      
      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: containerRef.current,
          start: 'top top',
          end: 'bottom bottom',
          pin: stageRef.current,
          scrub: 1,
        }
      });

      // 1. Draw the path
      tl.to(pathRef.current, {
        strokeDashoffset: 0,
        ease: 'none',
        duration: 1
      }, 0);

      // 2. Move the signal box along the path
      tl.to(signalRef.current, {
        motionPath: {
          path: pathRef.current,
          align: pathRef.current,
          alignOrigin: [0.5, 0.5],
        },
        ease: 'none',
        duration: 1
      }, 0);

      // 3. Trigger detail & image highlights as signal passes them
      // There are 7 nodes, evenly spaced along the path.
      NODES.forEach((_, i) => {
        const triggerPoint = i / (NODES.length - 1);
        
        // Highlight details
        tl.to(detailRefs.current[i], { opacity: 1, y: 0, duration: 0.1 }, triggerPoint - 0.05);
        if (i < NODES.length - 1) {
          tl.to(detailRefs.current[i], { opacity: 0.1, y: 10, duration: 0.1 }, triggerPoint + 0.1);
        }

        // Crossfade image fragment
        tl.to(imageRefs.current[i], { opacity: 1, duration: 0.1 }, triggerPoint - 0.05);
        if (i < NODES.length - 1) {
          tl.to(imageRefs.current[i], { opacity: 0, duration: 0.1 }, triggerPoint + 0.1);
        }
      });

    }, containerRef);

    return () => ctx.revert();
  }, []);

  return (
    <section id="architecture" ref={containerRef} className="relative w-full h-[400vh] bg-[#050505] text-[#F1F1F1]">
      <div ref={stageRef} className="w-full h-screen overflow-hidden flex flex-col justify-center px-6 md:px-12 lg:px-24">
        
        <div className="absolute top-12 left-12 label-caps text-[#8E8E8E]">// SYSTEM ARCHITECTURE PIPELINE</div>

        {/* Dynamic Image Fragment Area (Background) */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[70vw] h-[60vh] opacity-30 pointer-events-none">
           {NODES.map((n, i) => (
             <img 
                key={n.id}
                ref={el => { imageRefs.current[i] = el; }}
                src={n.img} 
                alt={n.title}
                className="absolute inset-0 w-full h-full object-cover shadow-2xl mix-blend-luminosity"
             />
           ))}
        </div>

        {/* SVG Path Layer */}
        <div className="absolute inset-0 pointer-events-none z-10 flex items-center justify-center mt-20">
          <svg className="w-full h-[60vh]" viewBox="0 0 1400 400" preserveAspectRatio="none">
            {/* Background thin track */}
            <path 
              d="M 50 50 L 300 50 L 350 200 L 600 200 L 650 350 L 900 350 L 950 200 L 1200 200 L 1250 50 L 1350 50" 
              fill="none" 
              stroke="#202020" 
              strokeWidth="2" 
            />
            {/* Animated drawing path */}
            <path 
              ref={pathRef}
              d="M 50 50 L 300 50 L 350 200 L 600 200 L 650 350 L 900 350 L 950 200 L 1200 200 L 1250 50 L 1350 50" 
              fill="none" 
              stroke="#F1F1F1" 
              strokeWidth="4" 
            />
            {/* The traveling signal block */}
            <rect 
              ref={signalRef}
              width="24" height="24" fill="#FFFFFF" x="-12" y="-12"
            />
          </svg>
        </div>

        {/* Text Nodes Overlay */}
        <div className="absolute inset-0 pointer-events-none z-20 flex items-center justify-center mt-20">
          <div className="relative w-full max-w-[1400px] h-[60vh]">
            {/* We position the text strictly based on the SVG path coordinates (scaled conceptually to percentages) */}
            {/* Node 1: 50,50 */}
            <div ref={el => { detailRefs.current[0] = el; }} className="absolute left-[3.5%] top-[5%] -translate-y-full pb-4">
              <h3 className="font-display text-4xl font-extrabold text-[#FFFFFF]">{NODES[0].title}</h3>
              <p className="font-mono text-sm text-[#C8C8C8] max-w-[200px]">{NODES[0].desc}</p>
            </div>
            {/* Node 2: 300,50 */}
            <div ref={el => { detailRefs.current[1] = el; }} className="absolute left-[21.4%] top-[5%] -translate-y-full pb-4">
              <h3 className="font-display text-4xl font-extrabold text-[#FFFFFF]">{NODES[1].title}</h3>
              <p className="font-mono text-sm text-[#C8C8C8] max-w-[200px]">{NODES[1].desc}</p>
            </div>
            {/* Node 3: 475,200 (Midpoint of 350->600 segment) */}
            <div ref={el => { detailRefs.current[2] = el; }} className="absolute left-[34%] top-[50%] -translate-y-full pb-4">
              <h3 className="font-display text-4xl font-extrabold text-[#FFFFFF]">{NODES[2].title}</h3>
              <p className="font-mono text-sm text-[#C8C8C8] max-w-[200px]">{NODES[2].desc}</p>
            </div>
            {/* Node 4: 650,350 */}
            <div ref={el => { detailRefs.current[3] = el; }} className="absolute left-[46.4%] top-[87.5%] pt-4">
              <h3 className="font-display text-4xl font-extrabold text-[#FFFFFF]">{NODES[3].title}</h3>
              <p className="font-mono text-sm text-[#C8C8C8] max-w-[200px]">{NODES[3].desc}</p>
            </div>
            {/* Node 5: 900,350 */}
            <div ref={el => { detailRefs.current[4] = el; }} className="absolute left-[64.2%] top-[87.5%] pt-4">
              <h3 className="font-display text-4xl font-extrabold text-[#FFFFFF]">{NODES[4].title}</h3>
              <p className="font-mono text-sm text-[#C8C8C8] max-w-[200px]">{NODES[4].desc}</p>
            </div>
            {/* Node 6: 1075,200 (Midpoint of 950->1200) */}
            <div ref={el => { detailRefs.current[5] = el; }} className="absolute left-[77%] top-[50%] pt-4">
              <h3 className="font-display text-4xl font-extrabold text-[#FFFFFF]">{NODES[5].title}</h3>
              <p className="font-mono text-sm text-[#C8C8C8] max-w-[200px]">{NODES[5].desc}</p>
            </div>
            {/* Node 7: 1250,50 */}
            <div ref={el => { detailRefs.current[6] = el; }} className="absolute left-[89%] top-[5%] -translate-y-full pb-4">
              <h3 className="font-display text-4xl font-extrabold text-[#FFFFFF]">{NODES[6].title}</h3>
              <p className="font-mono text-sm text-[#C8C8C8] max-w-[200px]">{NODES[6].desc}</p>
            </div>
          </div>
        </div>

      </div>
    </section>
  );
};

