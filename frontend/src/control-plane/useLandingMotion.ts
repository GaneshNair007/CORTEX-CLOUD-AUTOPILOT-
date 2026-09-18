import { useEffect, type RefObject } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";

gsap.registerPlugin(ScrollTrigger);

/** Each landing mount owns its scroll effects; none survive entry into the console. */
export function useLandingMotion(
  root: RefObject<HTMLDivElement | null>,
  enabled: boolean,
  onPhase: (phase: number) => void,
  manualPhase: RefObject<boolean>,
) {
  useEffect(() => {
    const page = root.current;
    if (!page) return;
    const nav = page.querySelector<HTMLElement>(".br-nav")!;
    const stage = page.querySelector<HTMLElement>(".br-stage")!;
    const process = page.querySelector<HTMLElement>(".br-process")!;
    const updateNav = () => {
      nav.dataset.condensed = String(window.scrollY > 50);
      nav.dataset.dark = String(
        [stage, process].some((section) => {
          const box = section.getBoundingClientRect();
          return box.top < 80 && box.bottom > 80;
        }),
      );
    };
    window.addEventListener("scroll", updateNav, { passive: true });
    updateNav();
    if (!enabled) {
      stage.dataset.motionProgress = "1";
      return () => window.removeEventListener("scroll", updateNav);
    }

    let disposed = false;
    const lenis = new Lenis({
      autoRaf: true,
      lerp: 0.1,
      smoothWheel: true,
      syncTouch: false,
    });
    lenis.on("scroll", ScrollTrigger.update);
    const releaseManual = () => {
      manualPhase.current = false;
    };
    const releaseOnKey = (event: KeyboardEvent) => {
      if (
        ["PageDown", "PageUp", "Home", "End", "ArrowDown", "ArrowUp"].includes(
          event.key,
        )
      )
        releaseManual();
    };
    window.addEventListener("wheel", releaseManual, { passive: true });
    window.addEventListener("touchstart", releaseManual, { passive: true });
    window.addEventListener("keydown", releaseOnKey);
    const media = gsap.matchMedia();
    const context = gsap.context(() => {
      gsap.fromTo(
        ".br-hero-line > span",
        { yPercent: 110, rotate: 3 },
        {
          yPercent: 0,
          rotate: 0,
          duration: 1.1,
          stagger: 0.12,
          ease: "power3.out",
          clearProps: "transform",
        },
      );
      gsap.fromTo(
        ".br-hero-bottom",
        { opacity: 0, y: 20 },
        {
          opacity: 1,
          y: 0,
          duration: 0.8,
          delay: 0.3,
          ease: "power2.out",
          clearProps: "all",
        },
      );
      page.querySelectorAll<HTMLElement>("[data-reveal]").forEach((element) => {
        gsap.fromTo(
          element,
          { opacity: 0, y: 28 },
          {
            opacity: 1,
            y: 0,
            duration: 0.8,
            ease: "power2.out",
            clearProps: "transform,opacity",
            scrollTrigger: { trigger: element, start: "top 92%", once: true },
          },
        );
      });
      const story = gsap.timeline({
        scrollTrigger: {
          trigger: stage,
          start: "top top",
          end: "bottom bottom",
          scrub: 0.8,
          onUpdate: ({ progress }) => {
            stage.dataset.motionProgress = progress.toFixed(3);
          },
        },
      });
      story.fromTo(
        ".br-metal-left",
        { xPercent: 85, rotateY: -25, rotateZ: -20, scale: 1.25 },
        { xPercent: -24, rotateY: 20, rotateZ: 25, scale: 0.75, duration: 1.4 },
        0,
      );
      story.fromTo(
        ".br-metal-right",
        { xPercent: -85, rotateY: 25, rotateZ: 20, scale: 1.25 },
        {
          xPercent: 24,
          rotateY: -20,
          rotateZ: -25,
          scale: 0.75,
          duration: 1.4,
        },
        0,
      );
      story.fromTo(
        ".br-stage-wordmark",
        { opacity: 1, scale: 1 },
        { opacity: 0, scale: 0.84, duration: 0.35 },
        0,
      );
      story.fromTo(
        ".br-story",
        { opacity: 0, y: 40 },
        { opacity: 1, y: 0, duration: 0.35 },
        0.25,
      );
      story.fromTo(
        ".br-story-word",
        { opacity: 0.3 },
        { opacity: 1, duration: 0.16, stagger: 0.025 },
        0.35,
      );
      gsap.fromTo(
        ".br-stage-background",
        { scaleX: 1 },
        {
          scaleX: 0.975,
          borderRadius: "0 0 20px 20px",
          ease: "none",
          scrollTrigger: {
            trigger: stage,
            start: "bottom 80%",
            end: "bottom top",
            scrub: 0.8,
          },
        },
      );
      media.add("(min-width: 900px) and (min-height: 680px)", () => {
        page
          .querySelectorAll<HTMLElement>(".br-service-card")
          .forEach((card, index) => {
            gsap.to(card, {
              scale: 0.9 + index * 0.018,
              ease: "none",
              scrollTrigger: {
                trigger: card,
                start: `top ${160 + index * 20}px`,
                end: `top ${90 + index * 20}px`,
                scrub: true,
              },
            });
          });
        ScrollTrigger.create({
          trigger: process,
          start: "top top",
          end: "bottom bottom",
          onUpdate: ({ progress }) => {
            process.style.setProperty("--process-progress", String(progress));
            if (!manualPhase.current)
              onPhase(Math.min(3, Math.floor(progress * 4)));
          },
        });
      });
      gsap.fromTo(
        ".br-footer-wordmark",
        { yPercent: 20 },
        {
          yPercent: 0,
          ease: "none",
          scrollTrigger: {
            trigger: ".br-footer",
            start: "top bottom",
            end: "bottom bottom",
            scrub: 0.8,
          },
        },
      );
    }, page);
    void document.fonts.ready.then(() => {
      if (!disposed) ScrollTrigger.refresh();
    });
    return () => {
      disposed = true;
      lenis.destroy();
      media.revert();
      context.revert();
      window.removeEventListener("scroll", updateNav);
      window.removeEventListener("wheel", releaseManual);
      window.removeEventListener("touchstart", releaseManual);
      window.removeEventListener("keydown", releaseOnKey);
    };
  }, [enabled, root, onPhase, manualPhase]);
}
