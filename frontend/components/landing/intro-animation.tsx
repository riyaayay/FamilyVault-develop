"use client";

import React, { useState, useEffect, useRef } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  motion,
  useTransform,
  useSpring,
  useMotionValue,
  useScroll,
  type MotionValue,
} from "framer-motion";

export type AnimationPhase = "scatter" | "line" | "circle" | "bottom-strip";

interface FlipCardProps {
  src: string;
  objectPosition?: string;
  label: string;
  tag: string;
  target: {
    x: number;
    y: number;
    rotation: number;
    scale: number;
    opacity: number;
  };
}

const IMG_WIDTH = 60;
const IMG_HEIGHT = 85;

function FlipCard({
  src,
  objectPosition,
  label,
  tag,
  target,
}: FlipCardProps) {
  const [flipped, setFlipped] = useState(false);

  return (
    <motion.div
      animate={{
        x: target.x,
        y: target.y,
        rotate: target.rotation,
        scale: target.scale,
        opacity: target.opacity,
      }}
      transition={{
        type: "spring",
        stiffness: 40,
        damping: 15,
      }}
      style={{
        position: "absolute",
        width: IMG_WIDTH,
        height: IMG_HEIGHT,
        transformStyle: "preserve-3d",
        perspective: "1000px",
      }}
      className="cursor-pointer group"
      onClick={() => setFlipped((f) => !f)}
    >
      <motion.div
        className="relative h-full w-full"
        style={{ transformStyle: "preserve-3d" }}
        animate={{ rotateY: flipped ? 180 : 0 }}
        whileHover={{ rotateY: 180 }}
        transition={{ duration: 0.6, type: "spring", stiffness: 260, damping: 20 }}
      >
        <div
          className="absolute inset-0 h-full w-full overflow-hidden rounded-xl shadow-lg bg-neutral-200"
          style={{ backfaceVisibility: "hidden" }}
        >
          <Image
            src={src}
            alt={`${label} — FamilyVault`}
            fill
            // Card box is 60 px, but during the bottom-strip arc
            // Framer Motion scales it up to 1.8× (1.4× on mobile),
            // so the on-screen footprint reaches ~108 px CSS / 216 px
            // physical on a retina display. Asking the optimizer for
            // a 256-wide source covers DPR 3 at peak scale.
            sizes="256px"
            loading="lazy"
            className="h-full w-full object-cover"
            style={{ objectPosition: objectPosition ?? "center" }}
          />
          <div className="absolute inset-0 bg-black/10 transition-colors group-hover:bg-transparent" />
        </div>
        <div
          className="absolute inset-0 h-full w-full overflow-hidden rounded-xl shadow-lg bg-neutral-900 flex flex-col items-center justify-center p-2 border border-neutral-700"
          style={{ backfaceVisibility: "hidden", transform: "rotateY(180deg)" }}
        >
          <div className="text-center">
            <p className="text-[8px] font-bold text-white/60 uppercase tracking-widest mb-1">
              {tag}
            </p>
            <p className="text-xs font-medium text-white leading-tight">
              {label}
            </p>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

const TOTAL_IMAGES = 20;

const FEATURES: {
  src: string;
  objectPosition: string;
  tag: string;
  label: string;
}[] = [
  { src: "/intro/01.jpg", objectPosition: "50% 32%", tag: "Vault", label: "Family Vault" },
  { src: "/intro/02.jpg", objectPosition: "50% 35%", tag: "Biometrics", label: "Face Match" },
  { src: "/intro/03.jpg", objectPosition: "50% 38%", tag: "Memories", label: "Timeline" },
  { src: "/intro/04.jpg", objectPosition: "50% 30%", tag: "Relations", label: "Kinship Graph" },
  { src: "/intro/05.jpg", objectPosition: "50% 34%", tag: "Governance", label: "Clan Trust" },
  { src: "/intro/06.jpg", objectPosition: "50% 36%", tag: "Triage", label: "Smart Inbox" },
  { src: "/intro/07.jpg", objectPosition: "50% 32%", tag: "Household", label: "Nuclear Family" },
  { src: "/intro/08.jpg", objectPosition: "50% 35%", tag: "Security", label: "Protected Records" },
  { src: "/intro/09.jpg", objectPosition: "50% 30%", tag: "Trustees", label: "Emergency Access" },
  { src: "/intro/10.jpg", objectPosition: "50% 33%", tag: "Legacy", label: "Heritage Archive" },
  { src: "/intro/11.jpg", objectPosition: "50% 36%", tag: "Media", label: "Shared Albums" },
  { src: "/intro/12.jpg", objectPosition: "50% 34%", tag: "Profiles", label: "Verified Identity" },
  { src: "/intro/13.jpg", objectPosition: "50% 32%", tag: "Access", label: "Roles & Permissions" },
  { src: "/intro/14.jpg", objectPosition: "50% 36%", tag: "Milestones", label: "Life Events" },
  { src: "/intro/15.jpg", objectPosition: "50% 34%", tag: "Consent", label: "Family Approvals" },
  { src: "/intro/16.jpg", objectPosition: "50% 32%", tag: "Backup", label: "Encrypted Storage" },
  { src: "/intro/17.jpg", objectPosition: "50% 36%", tag: "Lineage", label: "Ancestor Map" },
  { src: "/intro/18.jpg", objectPosition: "50% 32%", tag: "Search", label: "Instant Recall" },
  { src: "/intro/19.jpg", objectPosition: "50% 34%", tag: "Sync", label: "Auto Publish" },
  { src: "/intro/20.jpg", objectPosition: "50% 36%", tag: "Invites", label: "Family Onboarding" },
];

const IMAGES = FEATURES;

const lerp = (start: number, end: number, t: number) => start * (1 - t) + end * t;

// Deterministic per-index randomness so the scatter is stable across renders.
function scatterRand(index: number, salt: number): number {
  let a = ((index + 1) * 2654435761 + (salt + 1) * 40503) | 0;
  a = (a + 0x6d2b79f5) | 0;
  let t = Math.imul(a ^ (a >>> 15), 1 | a);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}

const SCATTER_POSITIONS = IMAGES.map((_, i) => ({
  x: (scatterRand(i, 1) - 0.5) * 1500,
  y: (scatterRand(i, 2) - 0.5) * 1000,
  rotation: (scatterRand(i, 3) - 0.5) * 180,
  scale: 0.6,
  opacity: 0,
}));

interface IntroAnimationProps {
  scrollProgress?: MotionValue<number>;
  maxScroll?: number;
}

export default function IntroAnimation({
  scrollProgress,
  maxScroll = 3000,
}: IntroAnimationProps = {}) {
  const [introPhase, setIntroPhase] = useState<AnimationPhase>("scatter");
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const handleResize = (entries: ResizeObserverEntry[]) => {
      for (const entry of entries) {
        setContainerSize({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    };

    const observer = new ResizeObserver(handleResize);
    observer.observe(containerRef.current);

    return () => observer.disconnect();
  }, []);

  const virtualScroll = useMotionValue(0);
  const scrollRef = useRef(0);

  useEffect(() => {
    if (!scrollProgress) return;
    const unsub = scrollProgress.on("change", (v) => {
      const clamped = Math.min(Math.max(v, 0), 1);
      scrollRef.current = clamped * maxScroll;
      virtualScroll.set(scrollRef.current);
    });
    return () => unsub();
  }, [scrollProgress, virtualScroll, maxScroll]);

  useEffect(() => {
    if (scrollProgress) return;
    const container = containerRef.current;
    if (!container) return;

    const handleWheel = (e: WheelEvent) => {
      const atStart = scrollRef.current <= 0 && e.deltaY < 0;
      const atEnd = scrollRef.current >= maxScroll && e.deltaY > 0;
      if (atStart || atEnd) return;

      e.preventDefault();
      const newScroll = Math.min(
        Math.max(scrollRef.current + e.deltaY, 0),
        maxScroll,
      );
      scrollRef.current = newScroll;
      virtualScroll.set(newScroll);
    };

    let touchStartY = 0;
    const handleTouchStart = (e: TouchEvent) => {
      touchStartY = e.touches[0].clientY;
    };
    const handleTouchMove = (e: TouchEvent) => {
      const touchY = e.touches[0].clientY;
      const deltaY = touchStartY - touchY;
      touchStartY = touchY;

      const newScroll = Math.min(
        Math.max(scrollRef.current + deltaY, 0),
        maxScroll,
      );
      scrollRef.current = newScroll;
      virtualScroll.set(newScroll);
    };

    container.addEventListener("wheel", handleWheel, { passive: false });
    container.addEventListener("touchstart", handleTouchStart, { passive: false });
    container.addEventListener("touchmove", handleTouchMove, { passive: false });

    return () => {
      container.removeEventListener("wheel", handleWheel);
      container.removeEventListener("touchstart", handleTouchStart);
      container.removeEventListener("touchmove", handleTouchMove);
    };
  }, [virtualScroll, scrollProgress, maxScroll]);

  const morphProgress = useTransform(virtualScroll, [0, 600], [0, 1]);
  const smoothMorph = useSpring(morphProgress, { stiffness: 40, damping: 20 });

  const scrollRotate = useTransform(
    virtualScroll,
    [600, maxScroll],
    [0, 360],
  );
  const smoothScrollRotate = useSpring(scrollRotate, {
    stiffness: 40,
    damping: 20,
  });

  const mouseX = useMotionValue(0);
  const smoothMouseX = useSpring(mouseX, { stiffness: 30, damping: 20 });

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      const relativeX = e.clientX - rect.left;

      const normalizedX = (relativeX / rect.width) * 2 - 1;
      mouseX.set(normalizedX * 100);
    };
    container.addEventListener("mousemove", handleMouseMove);
    return () => container.removeEventListener("mousemove", handleMouseMove);
  }, [mouseX]);

  useEffect(() => {
    const timer1 = setTimeout(() => setIntroPhase("line"), 500);
    const timer2 = setTimeout(() => setIntroPhase("circle"), 2500);
    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
    };
  }, []);

  const [morphValue, setMorphValue] = useState(0);
  const [rotateValue, setRotateValue] = useState(0);
  const [parallaxValue, setParallaxValue] = useState(0);
  const [autoRotate, setAutoRotate] = useState(0);
  const morphValueRef = useRef(0);
  const autoRotateRef = useRef(0);
  const isPausedRef = useRef(false);

  useEffect(() => {
    morphValueRef.current = morphValue;
  }, [morphValue]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const onEnter = () => {
      isPausedRef.current = true;
    };
    const onLeave = () => {
      isPausedRef.current = false;
    };
    container.addEventListener("mouseenter", onEnter);
    container.addEventListener("mouseleave", onLeave);
    return () => {
      container.removeEventListener("mouseenter", onEnter);
      container.removeEventListener("mouseleave", onLeave);
    };
  }, []);

  useEffect(() => {
    let rafId = 0;
    let lastTime = performance.now();
    const tick = (time: number) => {
      const dt = time - lastTime;
      lastTime = time;
      if (morphValueRef.current >= 0.95 && !isPausedRef.current) {
        autoRotateRef.current += dt * 0.004;
        setAutoRotate(autoRotateRef.current);
      }
      rafId = requestAnimationFrame(tick);
    };
    rafId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafId);
  }, []);

  useEffect(() => {
    const unsubscribeMorph = smoothMorph.on("change", setMorphValue);
    const unsubscribeRotate = smoothScrollRotate.on("change", setRotateValue);
    const unsubscribeParallax = smoothMouseX.on("change", setParallaxValue);
    return () => {
      unsubscribeMorph();
      unsubscribeRotate();
      unsubscribeParallax();
    };
  }, [smoothMorph, smoothScrollRotate, smoothMouseX]);

  const contentOpacity = useTransform(smoothMorph, [0.8, 1], [0, 1]);
  const contentY = useTransform(smoothMorph, [0.8, 1], [20, 0]);

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full bg-background overflow-hidden"
    >
      <div className="flex h-full w-full flex-col items-center justify-center perspective-[1000px]">
        <div className="absolute z-0 flex flex-col items-center justify-center text-center pointer-events-none top-1/2 -translate-y-1/2 px-4">
          <motion.h1
            initial={{ opacity: 0, y: 20, filter: "blur(10px)" }}
            animate={
              introPhase === "circle" && morphValue < 0.5
                ? { opacity: 1 - morphValue * 2, y: 0, filter: "blur(0px)" }
                : { opacity: 0, filter: "blur(10px)" }
            }
            transition={{ duration: 1 }}
            className="text-2xl font-medium tracking-tight text-foreground md:text-4xl"
          >
            Every generation has a story.
          </motion.h1>
          <motion.p
            initial={{ opacity: 0 }}
            animate={
              introPhase === "circle" && morphValue < 0.5
                ? { opacity: 0.5 - morphValue }
                : { opacity: 0 }
            }
            transition={{ duration: 1, delay: 0.2 }}
            className="mt-4 text-xs font-bold tracking-[0.2em] text-muted-foreground"
          >
            SCROLL TO EXPLORE
          </motion.p>
        </div>

        <motion.div
          style={{ opacity: contentOpacity, y: contentY }}
          className="absolute top-[8%] z-10 flex flex-col items-center justify-center text-center px-4"
        >
          <h2
            className="text-3xl md:text-5xl font-semibold text-foreground"
            style={{ letterSpacing: "0.08em", marginBottom: "16px" }}
          >
            Explore FamilyVault
          </h2>
          <p className="text-sm md:text-base text-muted-foreground max-w-lg leading-relaxed">
            Face recognition, kinship mapping, encrypted records and clan
            consensus.{" "}
            <br className="hidden md:block" />
            Scroll through the pieces that hold a family together.
          </p>
          <Link
            href="/sign-up"
            className="mt-6 inline-flex items-center rounded-full bg-foreground px-5 py-2.5 text-sm font-medium text-background transition-opacity hover:opacity-85"
          >
            Create your family vault
          </Link>
        </motion.div>

        <div className="relative flex items-center justify-center w-full h-full">
          {IMAGES.map((image, i) => {
            let target = { x: 0, y: 0, rotation: 0, scale: 1, opacity: 1 };

            if (introPhase === "scatter") {
              target = SCATTER_POSITIONS[i];
            } else if (introPhase === "line") {
              const lineSpacing = 70;
              const lineTotalWidth = TOTAL_IMAGES * lineSpacing;
              const lineX = i * lineSpacing - lineTotalWidth / 2;
              target = { x: lineX, y: 0, rotation: 0, scale: 1, opacity: 1 };
            } else {
              const isMobile = containerSize.width < 768;
              const minDimension = Math.min(
                containerSize.width,
                containerSize.height,
              );

              const circleRadius = Math.min(minDimension * 0.35, 350);

              const circleAngle = (i / TOTAL_IMAGES) * 360;
              const circleRad = (circleAngle * Math.PI) / 180;
              const circlePos = {
                x: Math.cos(circleRad) * circleRadius,
                y: Math.sin(circleRad) * circleRadius,
                rotation: circleAngle + 90,
              };

              const baseRadius = Math.min(
                containerSize.width,
                containerSize.height * 1.5,
              );
              const arcRadius = baseRadius * (isMobile ? 1.4 : 1.1);

              const arcApexY = containerSize.height * (isMobile ? 0.35 : 0.25);
              const arcCenterY = arcApexY + arcRadius;

              const spreadAngle = isMobile ? 100 : 130;
              const startAngle = -90 - spreadAngle / 2;
              const step = spreadAngle / (TOTAL_IMAGES - 1);

              const progress = Math.min(Math.max(rotateValue / 360, 0), 1);

              const maxRotation = spreadAngle * 0.8;
              const totalShift = -(progress * maxRotation) - autoRotate;

              const baseAngle = i * step;
              const wrappedPos =
                (((baseAngle + totalShift) % spreadAngle) + spreadAngle) %
                spreadAngle;
              const currentArcAngle = startAngle + wrappedPos;
              const arcRad = (currentArcAngle * Math.PI) / 180;

              const fadeRange = 10;
              let edgeOpacity = 1;
              if (wrappedPos < fadeRange) {
                edgeOpacity = wrappedPos / fadeRange;
              } else if (wrappedPos > spreadAngle - fadeRange) {
                edgeOpacity = (spreadAngle - wrappedPos) / fadeRange;
              }

              const arcPos = {
                x: Math.cos(arcRad) * arcRadius + parallaxValue,
                y: Math.sin(arcRad) * arcRadius + arcCenterY,
                rotation: currentArcAngle + 90,
                scale: isMobile ? 1.4 : 1.8,
              };

              target = {
                x: lerp(circlePos.x, arcPos.x, morphValue),
                y: lerp(circlePos.y, arcPos.y, morphValue),
                rotation: lerp(circlePos.rotation, arcPos.rotation, morphValue),
                scale: lerp(1, arcPos.scale, morphValue),
                opacity: lerp(1, edgeOpacity, morphValue),
              };
            }

            return (
              <FlipCard
                key={i}
                src={image.src}
                objectPosition={image.objectPosition}
                tag={image.tag}
                label={image.label}
                target={target}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}

export function LandingIntro() {
  const sectionRef = useRef<HTMLElement | null>(null);
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start start", "end end"],
  });

  return (
    <section
      ref={sectionRef}
      id="explore"
      className="relative h-[450vh] w-full"
    >
      <div className="sticky top-0 h-svh w-full overflow-hidden">
        <IntroAnimation scrollProgress={scrollYProgress} />
      </div>
    </section>
  );
}
