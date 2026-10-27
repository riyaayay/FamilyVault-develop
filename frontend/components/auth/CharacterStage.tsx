"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { motion } from "framer-motion";

type GazeState =
  | "IDLE"
  | "TYPING_EMAIL"
  | "PASSWORD_FOCUSED"
  | "PASSWORD_TYPING"
  | "WRONG_PASSWORD"
  | "PASSWORD_REVEALED";

interface CharacterStageProps {
  emailFocused: boolean;
  passwordFocused: boolean;
  emailHovered?: boolean;
  passwordHovered?: boolean;
  passwordRevealed: boolean;
  hasError: boolean;
  passwordLength?: number;
  emailLength?: number;
  keystrokeCount?: number;
  isPasswordLiveWrong?: boolean;
  isPasswordLiveCorrect?: boolean;
}

interface Vec2 {
  x: number; // normalized [-1.0, 1.0]
  y: number; // normalized [-1.0, 1.0]
}

const LERP_FACTOR = 0.18;

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

export default function CharacterStage({
  emailFocused,
  passwordFocused,
  emailHovered = false,
  passwordHovered = false,
  passwordRevealed,
  hasError,
  passwordLength = 0,
  emailLength = 0,
  keystrokeCount = 0,
  isPasswordLiveWrong = false,
  isPasswordLiveCorrect = false,
}: CharacterStageProps) {
  const stageRef = useRef<HTMLDivElement>(null);

  const [pupil, setPupil] = useState<Vec2>({ x: 0, y: 0 });
  const renderVec = useRef<Vec2>({ x: 0, y: 0 });
  const mouseTargetRef = useRef<Vec2>({ x: 0, y: 0 });
  const lastMouseMoveTimeRef = useRef<number>(Date.now());
  const lastKeystrokeTimeRef = useRef<number>(0);
  const rafId = useRef<number | null>(null);

  const isPasswordTarget = passwordHovered || passwordFocused;
  const isEmailTarget = (emailHovered || emailFocused) && !isPasswordTarget;

  const isTypingPassword = isPasswordTarget && passwordLength > 0;
  const isFocusedPasswordEmpty = isPasswordTarget && passwordLength === 0;

  // Exact 6-state hierarchy matching youtube-video.mp4:
  // 1. WRONG_PASSWORD: Error after submit -> Z-kink, black squats low, orange/yellow frowns
  // 2. PASSWORD_REVEALED: Eye clicked -> shock! Orange :O mouth, wide eyes
  // 3. PASSWORD_FOCUSED (hover or focus with 0 chars typed): Purple banana curve arching over Black; reciprocal stare!
  // 4. PASSWORD_TYPING (>0 chars typed): Purple stands tall leaning right; gaze on dots; bounce
  // 5. TYPING_EMAIL: Characters watch email input (pointing or typing)
  // 6. IDLE: Free mouse tracking across screen, all happy & smiling
  const gazeState: GazeState = hasError
    ? "WRONG_PASSWORD"
    : passwordRevealed
    ? "PASSWORD_REVEALED"
    : isTypingPassword
    ? "PASSWORD_TYPING"
    : isFocusedPasswordEmpty
    ? "PASSWORD_FOCUSED"
    : isEmailTarget
    ? "TYPING_EMAIL"
    : "IDLE";

  const isError = gazeState === "WRONG_PASSWORD";
  const isRevealed = gazeState === "PASSWORD_REVEALED";
  const isEmail = gazeState === "TYPING_EMAIL";
  const isPasswordBanana = gazeState === "PASSWORD_FOCUSED";
  const isPasswordTyping = gazeState === "PASSWORD_TYPING";

  const [blackBlink, setBlackBlink] = useState(false);
  const prevBananaRef = useRef(isPasswordBanana);
  const [retractingFromEmail, setRetractingFromEmail] = useState(false);
  const prevEmailRef = useRef(isEmail);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
      setPrefersReducedMotion(mq.matches);
      const listener = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
      mq.addEventListener("change", listener);
      return () => mq.removeEventListener("change", listener);
    }
  }, []);

  // Seamless transition: Cancel retraction immediately if password field is hovered or focused!
  useEffect(() => {
    if (isPasswordTarget) {
      setRetractingFromEmail(false);
      prevEmailRef.current = false;
      return;
    }
    if (prevEmailRef.current && !isEmail && !isPasswordTarget) {
      setRetractingFromEmail(true);
      const timer = setTimeout(() => setRetractingFromEmail(false), 770);
      return () => clearTimeout(timer);
    }
    prevEmailRef.current = isEmail;
  }, [isEmail, isPasswordTarget]);

  // Keystroke timestamp tracking
  useEffect(() => {
    if (keystrokeCount > 0) {
      lastKeystrokeTimeRef.current = Date.now();
    }
  }, [keystrokeCount]);

  // Blink when transitioning from looking-at-each-other into typing (video F84-F86)
  useEffect(() => {
    if (prevBananaRef.current && !isPasswordBanana) {
      setBlackBlink(true);
      const timer = setTimeout(() => setBlackBlink(false), 160);
      return () => clearTimeout(timer);
    }
    prevBananaRef.current = isPasswordBanana;
  }, [isPasswordBanana]);

  // Periodic natural blink in idle
  useEffect(() => {
    const interval = setInterval(() => {
      if (!isPasswordBanana && !isError) {
        setBlackBlink(true);
        setTimeout(() => setBlackBlink(false), 140);
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [isPasswordBanana, isError]);

  // --- 1. CONTINUOUS MOUSE TRACKING (Characters NEVER lose trace of cursor) ---
  const handleMouseMove = useCallback((e: MouseEvent) => {
    lastMouseMoveTimeRef.current = Date.now();
    if (!stageRef.current) return;

    const rect = stageRef.current.getBoundingClientRect();
    const stageCenterX = rect.left + rect.width * 0.45;
    const stageCenterY = rect.top + rect.height * 0.55;

    // Responsive Cartesian normalization across viewport
    const spanX = Math.max(window.innerWidth * 0.38, 300);
    const spanY = Math.max(window.innerHeight * 0.35, 240);

    const nx = (e.clientX - stageCenterX) / spanX;
    const ny = (e.clientY - stageCenterY) / spanY;

    mouseTargetRef.current = {
      x: Math.max(-1.0, Math.min(1.0, nx)),
      y: Math.max(-1.0, Math.min(1.0, ny)),
    };
  }, []);

  useEffect(() => {
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("pointerdown", handleMouseMove);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("pointerdown", handleMouseMove);
    };
  }, [handleMouseMove]);

  // --- 2. 60 FPS RAF lerp loop with intelligent gaze blending ---
  useEffect(() => {
    const tick = () => {
      const now = Date.now();
      const timeSinceKeystroke = now - lastKeystrokeTimeRef.current;
      const timeSinceMouseMove = now - lastMouseMoveTimeRef.current;

      // 2. 60 FPS RAF loop with organic curved gaze pursuit
      let targetX = mouseTargetRef.current.x;
      let targetY = mouseTargetRef.current.y;

      const isMouseRecentlyActive = timeSinceMouseMove < 600;

      if (isError) {
        if (isMouseRecentlyActive) {
          targetX = lerp(-0.4, mouseTargetRef.current.x, 0.7);
          targetY = lerp(0.3, mouseTargetRef.current.y, 0.7);
        } else {
          targetX = -0.55;
          targetY = 0.45;
        }
      } else if (isPasswordBanana) {
        // Privacy mode: reciprocal gaze between Purple & Black (down-right)
        targetX = 0.78;
        targetY = 0.60;
      } else if (isRevealed) {
        targetX = mouseTargetRef.current.x;
        targetY = mouseTargetRef.current.y;
      } else if (isPasswordTyping) {
        const pwdProgress = Math.min(1, passwordLength / 14);
        targetX = lerp(0.88, 1.0, pwdProgress);
        targetY = lerp(0.62, 0.72, pwdProgress);
      } else if (isEmail) {
        // Looking at email field
        const emailProgress = Math.min(1, emailLength / 18);
        targetX = lerp(0.85, 1.0, emailProgress);
        targetY = 0.40;
      } else {
        // Free cursor tracking
        targetX = mouseTargetRef.current.x;
        targetY = mouseTargetRef.current.y;
      }

      // Smooth organic gaze interpolation with biological curve
      const dx = targetX - renderVec.current.x;
      const dy = targetY - renderVec.current.y;
      const dist = Math.hypot(dx, dy);

      // Fast, responsive initial response on state changes, gentle settling in idle
      const adaptiveLerp = dist > 0.25 ? 0.35 : 0.22;

      renderVec.current = {
        x: lerp(renderVec.current.x, targetX, adaptiveLerp),
        y: lerp(renderVec.current.y, targetY, adaptiveLerp),
      };

      setPupil({ x: renderVec.current.x, y: renderVec.current.y });
      rafId.current = requestAnimationFrame(tick);
    };

    rafId.current = requestAnimationFrame(tick);
    return () => {
      if (rafId.current) cancelAnimationFrame(rafId.current);
    };
  }, [
    isError,
    isPasswordBanana,
    isPasswordTyping,
    isEmail,
    isRevealed,
    passwordLength,
    emailLength,
  ]);

  // Unified, snappy 200ms transition across all characters (exact human saccade speed, 100% synchronized)
  const unifiedTransition = {
    duration: 0.20,
    ease: [0.22, 1, 0.36, 1] as const,
  };

  const springTransition = unifiedTransition;
  const smoothPathTransition = unifiedTransition;

  // Keystroke bounce
  const keystrokeBounce =
    keystrokeCount > 0
      ? keystrokeCount % 2 === 0
        ? -2.4
        : 1.2
      : 0;

  // Yellow beak orientation: flips left when cursor is to the left
  const yellowFacesLeft = !isPasswordBanana && !isError && pupil.x < -0.15;

  const isYellowSad = isError || (isPasswordTyping && isPasswordLiveWrong);

  // Yellow mouth line: Proportionate to Yellow's 88px wide body (x: 250..338)
  // - Sad Frown (Live wrong password or submit error, F114): Compact, expressive wavy squiggly frown from 292 under eye to 336 (44px = 50% body width)
  // - Password Focused Empty (Banana stare, F80): Alert perky beak looking at Purple & Black (36px = 41% body width)
  // - Password Revealed (F140): Crisp alert straight beak (48px length)
  // - Password Typing Correct (Happy): Subtle cheerful upturned smile beak (y: 265 -> 259)
  // - Facing Left (Email focused / cursor on left, F35): Starts flush at left contour 250, ends under eye at 286 (36px = 41% body width)
  // - Idle / Facing Right (F20, F50): Starts under eye at 302, extends to 356 (protruding 18px past 338 = 20.5% body width, 54px total length)
  const yellowMouthD = isYellowSad
    ? "M 292 268 Q 304 258 316 263 T 336 266"
    : isPasswordBanana
    ? "M 312 262 L 348 262"
    : isRevealed
    ? "M 304 263 L 352 263"
    : isPasswordTyping && isPasswordLiveCorrect
    ? "M 302 265 L 354 259"
    : yellowFacesLeft
    ? "M 250 262 L 286 262"
    : "M 302 264 L 356 264";

  // Morph paths for Purple pillar's body (matching cubic bezier structure: M ... C ... C ... C ... C ... Z)
  // 1. Tall upright pillar (F20, F35, F50, F100)
  const purpleStraightPath =
    "M 115 350 C 116 250, 117 150, 118 50 C 148 50, 178 50, 212 50 C 211 150, 210 250, 210 350 C 178 350, 146 350, 115 350 Z";
  // 2. The iconic banana curve arching forward over Black (F78-F82)
  const purpleBananaPath =
    "M 115 350 C 115 240, 132 120, 192 55 C 215 78, 238 108, 256 135 C 240 210, 222 280, 212 350 C 178 350, 146 350, 115 350 Z";
  // 3. Bent Z-kink back on wrong password error (F114)
  const purpleZkinkPath =
    "M 115 350 C 95 270, 70 230, 68 220 C 72 180, 85 120, 95 65 C 126 75, 158 85, 190 95 C 180 200, 195 260, 210 350 C 178 350, 146 350, 115 350 Z";

  const purpleActivePath = isError
    ? purpleZkinkPath
    : isPasswordBanana
    ? purpleBananaPath
    : purpleStraightPath;

  // Pupil deflection multipliers (sclera radius 6.5 -> max travel 3.8px)
  const purplePupilX = pupil.x * 3.8;
  const purplePupilY = pupil.y * 3.4;

  const blackPupilX = pupil.x * 3.6;
  const blackPupilY = pupil.y * 3.2;

  const orangeFaceX = pupil.x * 14.0;
  const orangeFaceY = pupil.y * 10.0;

  const yellowEyeX = pupil.x * 7.5;
  const yellowEyeY = pupil.y * 5.5;

  // --- CONTINUOUS PERSISTENT FACIAL COORDINATES (Eliminates DOM unmounting clicks) ---
  // Purple facial features
  const purpleEye1CX = isPasswordBanana ? 206 : 150;
  const purpleEye1CY = isPasswordBanana ? 115 : 90;
  const purpleEye1R = isPasswordBanana ? 5.2 : isRevealed ? 7.2 : 6.5;
  const purplePupil1CX = isPasswordBanana ? 209.2 : (150 + (isRevealed ? 3.5 : purplePupilX));
  const purplePupil1CY = isPasswordBanana ? 118.2 : (90 + (isRevealed ? 2.5 : purplePupilY));
  const purplePupil1R = isPasswordBanana ? 2.6 : isRevealed ? 3.8 : 3.2;

  const purpleEye2CX = isPasswordBanana ? 230 : 180;
  const purpleEye2CY = isPasswordBanana ? 138 : 90;
  const purpleEye2R = isPasswordBanana ? 5.2 : isRevealed ? 7.2 : 6.5;
  const purplePupil2CX = isPasswordBanana ? 233.2 : (180 + (isRevealed ? 3.5 : purplePupilX));
  const purplePupil2CY = isPasswordBanana ? 141.2 : (90 + (isRevealed ? 2.5 : purplePupilY));
  const purplePupil2R = isPasswordBanana ? 2.6 : isRevealed ? 3.8 : 3.2;

  const purpleMouthX1 = isPasswordBanana ? 219 : 158;
  const purpleMouthY1 = isPasswordBanana ? 126 : 110;
  const purpleMouthX2 = isPasswordBanana ? 223 : 172;
  const purpleMouthY2 = isPasswordBanana ? 138 : 110;

  // Black eye coordinates
  const blackLeftScleraX = isPasswordBanana ? 224 : 226;
  const blackLeftScleraY = isPasswordBanana ? 198 : 195;
  const blackLeftScleraR = isRevealed ? 6.8 : isPasswordBanana ? 5.5 : 6.0;
  const blackLeftPupilX = isPasswordBanana ? 220.8 : (226 + (isRevealed ? 3.2 : blackPupilX));
  const blackLeftPupilY = isPasswordBanana ? 194.8 : (195 + (isRevealed ? 2.5 : blackPupilY));
  const blackLeftPupilR = isRevealed ? 3.5 : isPasswordBanana ? 2.8 : 3.0;

  const blackRightScleraX = isPasswordBanana ? 240 : 244;
  const blackRightScleraY = isPasswordBanana ? 198 : 195;
  const blackRightScleraR = isRevealed ? 6.8 : isPasswordBanana ? 5.5 : 6.0;
  const blackRightPupilX = isPasswordBanana ? 236.8 : (244 + (isRevealed ? 3.2 : blackPupilX));
  const blackRightPupilY = isPasswordBanana ? 194.8 : (195 + (isRevealed ? 2.5 : blackPupilY));
  const blackRightPupilR = isRevealed ? 3.5 : isPasswordBanana ? 2.8 : 3.0;

  // Orange eye coordinates (clean, non-jittered base positions)
  const orangeEye1CX = isPasswordBanana ? 135 : 105;
  const orangeEye1CY = isPasswordBanana ? 282 : 285;
  const orangeEye1R = isPasswordBanana ? 4.2 : 4.8;

  const orangeEye2CX = isPasswordBanana ? 156 : 140;
  const orangeEye2CY = isPasswordBanana ? 282 : 285;
  const orangeEye2R = isPasswordBanana ? 4.2 : 4.8;

  // Static expressions for Orange mouth - zero per-frame string parsing lag!
  const orangeMouthD = isError || (isPasswordTyping && isPasswordLiveWrong)
    ? "M 114 304 Q 122.5 294 131 304"
    : isPasswordTyping && isPasswordLiveCorrect
    ? "M 114 295 Q 122.5 306 131 295"
    : isEmail
    ? "M 115 297 Q 122.5 305 130 297"
    : "M 114 296 Q 122.5 306 131 296";

  // Yellow eye coordinates
  const yellowEyeCX =
    (yellowFacesLeft ? 285 : 312) +
    (isError
      ? -2.5
      : isPasswordBanana
      ? 2.5
      : yellowEyeX);
  const yellowEyeCY = 250 + (isError ? -2.0 : yellowEyeY);
  const yellowEyeR = isRevealed ? 4.8 : 4.2;

  return (
    <div
      ref={stageRef}
      className="relative w-full h-full min-h-[380px] flex items-center justify-center select-none overflow-hidden"
      aria-hidden="true"
      role="presentation"
    >
      <svg
        viewBox="0 0 400 400"
        className="w-full max-w-[360px] drop-shadow-sm"
        aria-hidden="true"
      >
        <defs>
          <clipPath id="stageBaselineClip">
            <rect x="0" y="0" width="400" height="350" />
          </clipPath>
        </defs>

        <g clipPath="url(#stageBaselineClip)">
          {/* ============================================================== */}
          {/* LAYER 1: PURPLE PILLAR (Back Layer)                            */}
          {/* ============================================================== */}
          <motion.g
            initial={{ scaleY: 0.25, opacity: 0.7 }}
            animate={{
              scaleY: 1,
              opacity: 1,
              rotate: prefersReducedMotion
                ? 0
                : isError || isPasswordBanana
                ? 0
                : isEmail
                ? 9.3 // Measured peak lean shear (Doc 3 Section 4)
                : retractingFromEmail
                ? -2.5 // Measured retraction overshoot (Doc 3 Section 4)
                : isPasswordTyping
                ? (isPasswordLiveWrong ? -2.5 : 4.5)
                : pupil.x * 3.5, // Dynamic lean with cursor
              x: prefersReducedMotion
                ? 0
                : isPasswordBanana
                ? 0
                : isEmail
                ? 8.0 // Measured +8px horizontal shift at peak lean (Doc 3 Section 4)
                : retractingFromEmail
                ? -4.0 // Measured -4px at overshoot (Doc 3 Section 4)
                : isPasswordTyping
                ? (isPasswordLiveWrong ? -2.0 : 2.0)
                : 0,
            }}
            transition={
              prefersReducedMotion
                ? { duration: 0 }
                : retractingFromEmail
                ? { duration: 0.45, ease: [0.22, 1, 0.36, 1] }
                : unifiedTransition
            }
            style={{ transformOrigin: "160px 350px" }}
          >
            {/* Body */}
            <motion.path
              d={purpleActivePath}
              animate={{ d: purpleActivePath }}
              transition={smoothPathTransition}
              fill="#6727FE"
            />

            {/* Facial Features for Purple (Persistent elements glide smoothly between banana arch and upright posture) */}
            {isError ? (
              // Error state (F114): Squinting sad eyes and downturned frown on Z-kink
              <motion.g
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.2 }}
              >
                <path
                  d="M 125 115 Q 133 107 141 115"
                  stroke="#FFF"
                  strokeWidth="3.2"
                  strokeLinecap="round"
                  fill="none"
                />
                <path
                  d="M 156 122 Q 164 114 172 122"
                  stroke="#FFF"
                  strokeWidth="3.2"
                  strokeLinecap="round"
                  fill="none"
                />
                <path
                  d="M 142 134 Q 149 126 156 134"
                  stroke="#111"
                  strokeWidth="3.0"
                  strokeLinecap="round"
                  fill="none"
                />
              </motion.g>
            ) : (
              // Persistent eyes and mouth that smoothly glide along human-like motion curves
              <motion.g
                animate={{
                  y:
                    isPasswordTyping || isEmail
                      ? keystrokeBounce * 0.8
                      : 0,
                }}
                transition={springTransition}
              >
                {/* Left Eye Sclera & Pupil */}
                <motion.circle
                  animate={{ cx: purpleEye1CX, cy: purpleEye1CY, r: purpleEye1R }}
                  transition={springTransition}
                  fill="#FFF"
                />
                <motion.circle
                  animate={{ cx: purplePupil1CX, cy: purplePupil1CY, r: purplePupil1R }}
                  transition={springTransition}
                  fill="#111"
                />

                {/* Right Eye Sclera & Pupil */}
                <motion.circle
                  animate={{ cx: purpleEye2CX, cy: purpleEye2CY, r: purpleEye2R }}
                  transition={springTransition}
                  fill="#FFF"
                />
                <motion.circle
                  animate={{ cx: purplePupil2CX, cy: purplePupil2CY, r: purplePupil2R }}
                  transition={springTransition}
                  fill="#111"
                />

                {/* Mouth: Expression arcs on specific states, smoothly interpolating line otherwise */}
                {retractingFromEmail || (isPasswordTyping && isPasswordLiveWrong) ? (
                  <motion.path
                    d="M 158 112 Q 165 105 172 112"
                    stroke="#111"
                    strokeWidth="2.8"
                    strokeLinecap="round"
                    fill="none"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.15 }}
                  />
                ) : isRevealed ? (
                  <motion.ellipse
                    cx={165}
                    cy={112}
                    rx={4.5}
                    ry={6.0}
                    fill="#111"
                    initial={{ scale: 0.5 }}
                    animate={{ scale: 1 }}
                    transition={{ duration: 0.2 }}
                  />
                ) : isPasswordTyping && isPasswordLiveCorrect ? (
                  <motion.path
                    d="M 158 109 Q 165 113 172 109"
                    stroke="#111"
                    strokeWidth="2.8"
                    strokeLinecap="round"
                    fill="none"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.15 }}
                  />
                ) : (
                  <motion.line
                    animate={{
                      x1: purpleMouthX1,
                      y1: purpleMouthY1,
                      x2: purpleMouthX2,
                      y2: purpleMouthY2,
                    }}
                    transition={springTransition}
                    stroke="#111"
                    strokeWidth={isPasswordBanana ? 2.6 : 2.8}
                    strokeLinecap="round"
                  />
                )}
              </motion.g>
            )}
          </motion.g>

          {/* ============================================================== */}
          {/* LAYER 2: BLACK CHARACTER (Middle-Back)                         */}
          {/* ============================================================== */}
          <motion.g
            initial={{ opacity: 0, y: 20 }}
            animate={{
              opacity: 1,
              rotate: isPasswordBanana
                ? 16 // CLOCKWISE leaning right directly into Purple's gaze!
                : isPasswordTyping
                ? (isPasswordLiveWrong ? 1.0 : 3.0)
                : isEmail
                ? 2.0
                : pupil.x * 1.5,
              x: isPasswordBanana
                ? 4
                : isPasswordTyping
                ? (isPasswordLiveWrong ? -2 : 2)
                : 0,
              y: isError
                ? 46 // Squats low in shame/embarrassment on error
                : isPasswordTyping
                ? (isPasswordLiveWrong ? 18 : keystrokeBounce * 0.8)
                : 0,
            }}
            transition={springTransition}
            style={{ transformOrigin: "235px 350px" }}
          >
            {/* Body */}
            <rect
              x="202"
              y="180"
              width="68"
              height="170"
              rx="3"
              fill="#1B1C21"
            />

            {/* Eyes container with blink support */}
            <motion.g
              animate={{
                scaleY: blackBlink ? 0.1 : 1.0,
              }}
              transition={{ duration: 0.08 }}
              style={{ transformOrigin: "235px 195px" }}
            >
              {/* Left Eye Sclera & Pupil - persistent motion elements */}
              <motion.circle
                animate={{
                  cx: blackLeftScleraX,
                  cy: blackLeftScleraY,
                  r: blackLeftScleraR,
                }}
                transition={springTransition}
                fill="#FFF"
              />
              <motion.circle
                animate={{
                  cx: blackLeftPupilX,
                  cy: blackLeftPupilY,
                  r: blackLeftPupilR,
                }}
                transition={springTransition}
                fill="#111"
              />

              {/* Right Eye Sclera & Pupil - persistent motion elements */}
              <motion.circle
                animate={{
                  cx: blackRightScleraX,
                  cy: blackRightScleraY,
                  r: blackRightScleraR,
                }}
                transition={springTransition}
                fill="#FFF"
              />
              <motion.circle
                animate={{
                  cx: blackRightPupilX,
                  cy: blackRightPupilY,
                  r: blackRightPupilR,
                }}
                transition={springTransition}
                fill="#111"
              />
            </motion.g>
          </motion.g>

          {/* ============================================================== */}
          {/* LAYER 3: YELLOW CHARACTER (Middle-Front)                       */}
          {/* ============================================================== */}
          <motion.g
            initial={{ opacity: 0, x: 15 }}
            animate={{
              opacity: 1,
              x: 0,
              y: isPasswordTyping
                ? keystrokeBounce * 0.8
                : isEmail
                ? keystrokeBounce * 0.4
                : 0,
            }}
            transition={springTransition}
            style={{ transformOrigin: "295px 350px" }}
          >
            {/* Body: Rounded dome top */}
            <path
              d="M 250 350 L 250 255 C 250 205, 338 205, 338 255 L 338 350 Z"
              fill="#E5C90A"
            />

            {/* Profile Eye Dot - persistent animated motion element */}
            <motion.circle
              animate={{
                cx: yellowEyeCX,
                cy: yellowEyeCY,
                r: yellowEyeR,
              }}
              transition={springTransition}
              fill="#111"
            />

            {/* Horizontal Beak Mouth Line (flips with cursor, frowns on error) */}
            <motion.path
              d={yellowMouthD}
              animate={{ d: yellowMouthD }}
              transition={{ duration: 0.2, ease: "easeInOut" }}
              stroke="#111"
              strokeWidth="3.0"
              strokeLinecap="round"
              fill="none"
            />
          </motion.g>

          {/* ============================================================== */}
          {/* LAYER 4: ORANGE BLOB (Foreground Layer)                        */}
          {/* ============================================================== */}
          <motion.g
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{
              opacity: 1,
              scale: 1,
              y: isError
                ? 6
                : isPasswordTyping
                ? (isPasswordLiveWrong ? 3 : keystrokeBounce * 0.7)
                : 0,
              scaleY: isError
                ? 0.95
                : isPasswordTyping && isPasswordLiveWrong
                ? 0.97
                : isPasswordTyping && keystrokeCount > 0
                ? 1.02
                : (1.0 + Math.abs(pupil.y) * 0.025),
              scaleX: isPasswordTyping && keystrokeCount > 0
                ? 0.98
                : (1.0 - Math.abs(pupil.x) * 0.035),
              rotate: prefersReducedMotion
                ? 0
                : isError || (isPasswordTyping && isPasswordLiveWrong)
                ? [0, -3.5, 3.5, -3.5, 3.5, 0] // Living "no-no-no" head shake on error
                : isPasswordBanana
                ? 2.5 // Inquisitive upward tilt towards Purple & Black
                : isEmail
                ? 3.2 // Attentive lean towards email
                : pupil.x * 5.5, // Continuous organic head tilt tracking cursor
            }}
            transition={
              isError || (isPasswordTyping && isPasswordLiveWrong)
                ? { duration: 0.35, ease: "easeInOut" }
                : springTransition
            }
            style={{ transformOrigin: "135px 350px" }}
          >
            {/* Asymmetrical Wide Dome Body */}
            <path
              d="M 35 350 C 40 270, 95 255, 135 255 C 185 255, 235 285, 240 350 Z"
              fill="#FE8332"
            />

            {/* Facial Features for Orange: Persistent elements that smoothly sweep across the body */}
            {isRevealed ? (
              // Password revealed: Two wide happy eyes and open ":O" mouth of shock!
              <motion.g
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.2 }}
              >
                <path
                  d="M 100 282 Q 110 274 120 282"
                  stroke="#111"
                  strokeWidth="3.5"
                  strokeLinecap="round"
                  fill="none"
                />
                <path
                  d="M 138 282 Q 148 274 158 282"
                  stroke="#111"
                  strokeWidth="3.5"
                  strokeLinecap="round"
                  fill="none"
                />
                <circle cx={129} cy={300} r={7.5} fill="#111" />
              </motion.g>
            ) : (
              <motion.g
                animate={{
                  x: isPasswordBanana ? 0 : orangeFaceX,
                  y: isPasswordBanana ? 0 : orangeFaceY,
                }}
                transition={springTransition}
              >
                {/* Primary Eye 1 (Left) - Persistent */}
                <motion.circle
                  animate={{
                    cx: orangeEye1CX,
                    cy: orangeEye1CY,
                    r: orangeEye1R,
                  }}
                  transition={springTransition}
                  fill="#111"
                />

                {/* Primary Eye 2 (Right) - Persistent */}
                <motion.circle
                  animate={{
                    cx: orangeEye2CX,
                    cy: orangeEye2CY,
                    r: orangeEye2R,
                  }}
                  transition={springTransition}
                  fill="#111"
                />

                {/* Third Dot for Password Banana mode (looking up-right at Purple) */}
                <motion.circle
                  animate={{
                    cx: 174,
                    cy: 270,
                    r: isPasswordBanana ? 4.2 : 0,
                    opacity: isPasswordBanana ? 1 : 0,
                  }}
                  transition={springTransition}
                  fill="#111"
                />

                {/* Mouth Arc (Hidden during Banana mode, smoothly morphs between smile and frown) */}
                <motion.path
                  d={orangeMouthD}
                  animate={{
                    d: orangeMouthD,
                    opacity: isPasswordBanana ? 0 : 1,
                  }}
                  transition={springTransition}
                  stroke="#111"
                  strokeWidth="3.0"
                  strokeLinecap="round"
                  fill="none"
                />
              </motion.g>
            )}
          </motion.g>
        </g>
      </svg>
    </div>
  );
}



