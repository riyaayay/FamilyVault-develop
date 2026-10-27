'use client';

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Lock, Network, Users } from "lucide-react";

type DashboardBentoProps = {
  memberCount: number;
  petCount: number;
};

function WelcomeType() {
  const [scale, setScale] = useState(1);

  useEffect(() => {
    const interval = setInterval(() => {
      setScale((prev) => (prev === 1 ? 1.06 : 1));
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-center justify-center h-full">
      <motion.span
        className="font-serif text-4xl md:text-6xl text-foreground font-medium text-center"
        animate={{ scale }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
      >
        Welcome back
      </motion.span>
    </div>
  );
}

function LayoutAnimation() {
  const [layout, setLayout] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setLayout((prev) => (prev + 1) % 3);
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  const layouts = ["grid-cols-2", "grid-cols-3", "grid-cols-1"];

  return (
    <div className="h-full flex items-center justify-center">
      <motion.div
        className={`grid ${layouts[layout]} gap-1.5 w-full max-w-[140px] h-full`}
        layout
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      >
        {[1, 2, 3].map((i) => (
          <motion.div
            key={i}
            className="bg-foreground/15 rounded-md h-5 w-full"
            layout
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          />
        ))}
      </motion.div>
    </div>
  );
}

function TrustCounter({ memberCount, petCount }: { memberCount: number; petCount: number }) {
  const [loading, setLoading] = useState(true);
  const [idx, setIdx] = useState(0);

  const values = [
    { value: memberCount, label: "members" },
    { value: petCount, label: "pets" },
  ];

  useEffect(() => {
    const timeout = setTimeout(() => setLoading(false), 500);
    return () => clearTimeout(timeout);
  }, []);

  useEffect(() => {
    if (loading) return;
    const interval = setInterval(() => setIdx((prev) => (prev + 1) % values.length), 2000);
    return () => clearInterval(interval);
  }, [loading, values.length]);

  const current = values[idx];

  return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <div className="h-12 flex items-center justify-center overflow-hidden relative w-full">
        <AnimatePresence mode="wait">
          {loading ? (
            <motion.div
              key="loader"
              className="h-8 w-24 bg-foreground/10 rounded"
              initial={{ opacity: 0.5 }}
              animate={{ opacity: [0.4, 0.7, 0.4] }}
              exit={{ opacity: 0, y: -20, position: 'absolute' }}
              transition={{ duration: 1, repeat: Infinity }}
            />
          ) : (
            <motion.span
              key={current.label}
              initial={{ y: 20, opacity: 0, filter: "blur(5px)" }}
              animate={{ y: 0, opacity: 1, filter: "blur(0px)" }}
              className="text-3xl md:text-4xl font-sans font-medium text-foreground"
            >
              {current.value} {current.label}
            </motion.span>
          )}
        </AnimatePresence>
      </div>
      <span className="text-sm text-muted-foreground">Clan Trust</span>
      <div className="w-full max-w-[120px] h-1.5 bg-foreground/10 rounded-full overflow-hidden">
        <motion.div
          className="h-full bg-foreground rounded-full"
          initial={{ width: 0 }}
          animate={{ width: loading ? 0 : "100%" }}
          transition={{ type: "spring", stiffness: 100, damping: 15, mass: 1 }}
        />
      </div>
    </div>
  );
}

function SecurityBadge() {
  const [shields, setShields] = useState([
    { id: 1, active: false },
    { id: 2, active: false },
    { id: 3, active: false },
  ]);

  useEffect(() => {
    const interval = setInterval(() => {
      setShields((prev) => {
        const nextIndex = prev.findIndex((s) => !s.active);
        if (nextIndex === -1) {
          return prev.map(() => ({ id: Math.random(), active: false }));
        }
        return prev.map((s, i) => (i === nextIndex ? { ...s, active: true } : s));
      });
    }, 800);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-center justify-center h-full gap-2">
      {shields.map((shield) => (
        <motion.div
          key={shield.id}
          className={`w-12 h-12 rounded-lg flex items-center justify-center ${
            shield.active ? "bg-foreground/10" : "bg-foreground/5"
          }`}
          animate={{ scale: shield.active ? 1.1 : 1 }}
          transition={{ duration: 0.3 }}
        >
          <Lock className={`w-5 h-5 ${shield.active ? "text-foreground" : "text-muted-foreground/60"}`} />
        </motion.div>
      ))}
    </div>
  );
}

function ClanNetwork() {
  const [pulses] = useState([0, 1, 2, 3, 4]);

  return (
    <div className="flex items-center justify-center h-full relative">
      <Network className="w-16 h-16 text-foreground/80 z-10" />
      {pulses.map((pulse) => (
        <motion.div
          key={pulse}
          className="absolute w-16 h-16 border-2 border-foreground/20 rounded-full"
          initial={{ scale: 0.5, opacity: 1 }}
          animate={{ scale: 3, opacity: 0 }}
          transition={{
            duration: 3,
            repeat: Infinity,
            delay: pulse * 0.8,
            ease: "easeOut",
          }}
        />
      ))}
    </div>
  );
}

export function DashboardBento({ memberCount, petCount }: DashboardBentoProps) {
  return (
    <section className="bg-background px-6 py-24 min-h-screen flex items-center justify-center">
      <div className="max-w-7xl w-full mx-auto">
        <motion.p
          className="text-muted-foreground text-sm uppercase tracking-widest mb-8"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          Clan Overview
        </motion.p>

        {/* Bento Grid */}
        <div className="grid grid-cols-1 md:grid-cols-6 gap-4 auto-rows-[200px]">
          {/* Welcome - Tall (2x2) */}
          <motion.div
            className="md:col-span-2 md:row-span-2 bg-card border border-border rounded-xl p-8 flex flex-col hover:border-foreground/20 transition-colors cursor-pointer overflow-hidden"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            whileHover={{ scale: 1.02, backgroundColor: "rgba(244, 244, 245, 1)" }}
          >
            <div className="flex-1">
              <WelcomeType />
            </div>
            <div className="mt-4">
              <h3 className="font-serif text-xl text-foreground font-medium">FamilyVault</h3>
              <p className="text-muted-foreground text-sm mt-1">Your family dashboard will appear here.</p>
            </div>
          </motion.div>

          {/* Nuclear Family - Standard (2x1) */}
          <Link href="/dashboard/nuclear-family" className="md:col-span-2 block h-full">
            <motion.div
              className="bg-card border border-border rounded-xl h-full p-8 flex flex-col hover:border-foreground/20 transition-colors cursor-pointer overflow-hidden"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 }}
              whileHover={{ scale: 0.98 }}
            >
              <div className="flex-1">
                <LayoutAnimation />
              </div>
              <div className="mt-4">
                <h3 className="font-serif text-xl text-foreground font-medium">Nuclear Family</h3>
                <p className="text-muted-foreground text-sm mt-1">Personal records, health, pets</p>
              </div>
            </motion.div>
          </Link>

          {/* Family Tree - Tall (2x2) */}
          <Link href="/dashboard/family" className="md:col-span-2 md:row-span-2 block h-full">
            <motion.div
              className="bg-card border border-border rounded-xl h-full p-6 flex flex-col hover:border-foreground/20 transition-colors cursor-pointer overflow-hidden"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2 }}
              whileHover={{ scale: 1.02, boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.15)" }}
            >
              <div className="flex-1 flex items-center justify-center">
                <div className="relative">
                  <ClanNetwork />
                </div>
              </div>
              <div className="mt-auto relative z-20 bg-background/60 backdrop-blur-sm rounded-lg p-2">
                <h3 className="font-serif text-xl text-foreground flex items-center gap-2 font-medium">
                  <Network className="w-5 h-5" />
                  Family Tree
                </h3>
                <p className="text-muted-foreground text-sm mt-1">Full generational tree view</p>
              </div>
            </motion.div>
          </Link>

          {/* Clan Trust Summary - Standard (2x1) */}
          <motion.div
            className="md:col-span-2 bg-card border border-border rounded-xl p-8 flex flex-col hover:border-foreground/20 transition-colors cursor-pointer overflow-hidden"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
            whileHover={{ scale: 0.98 }}
          >
            <div className="flex-1">
              <TrustCounter memberCount={memberCount} petCount={petCount} />
            </div>
            <div className="mt-4">
              <h3 className="font-serif text-xl text-foreground font-medium">Clan Trust Summary</h3>
              <p className="text-muted-foreground text-sm mt-1">Household members and pets under protection.</p>
            </div>
          </motion.div>

          {/* Protected Records - Wide (3x1) */}
          <motion.div
            className="md:col-span-3 bg-card border border-border rounded-xl p-8 flex flex-col hover:border-foreground/20 transition-colors cursor-pointer overflow-hidden"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.4 }}
            whileHover={{ scale: 0.98 }}
          >
            <div className="flex-1">
              <SecurityBadge />
            </div>
            <div className="mt-4">
              <h3 className="font-serif text-xl text-foreground flex items-center gap-2 font-medium">
                <Lock className="w-5 h-5" />
                Protected Records
              </h3>
              <p className="text-muted-foreground text-sm mt-1">
                {memberCount} Household members · {petCount} Pets
              </p>
            </div>
          </motion.div>

          {/* Vance Ancestral Clan - Wide (3x1) */}
          <motion.div
            className="md:col-span-3 bg-card border border-border rounded-xl p-8 flex flex-col hover:border-foreground/20 transition-colors cursor-pointer overflow-hidden"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.5 }}
            whileHover={{ scale: 0.98 }}
          >
            <div className="flex-1 flex items-center justify-center">
              <Users className="w-16 h-16 text-foreground" />
            </div>
            <div className="mt-4">
              <h3 className="font-serif text-xl text-foreground font-medium">Vance Ancestral Clan</h3>
              <p className="text-muted-foreground text-sm mt-1">Joint family</p>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
