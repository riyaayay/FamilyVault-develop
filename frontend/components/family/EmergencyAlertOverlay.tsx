"use client";

import React, { useState } from "react";

export type EmergencyPayload = {
  memberId: string;
  memberName: string;
  condition: string;
  bloodGroup: string;
  allergies: string[];
  medicalNotes: string[];
  emergencyContact: {
    name: string;
    hospital: string;
    phone: string;
  };
  signedTokenPassUrl: string;
  isActive: boolean;
};

// Canonical Eleanor Vance emergency record (Sprint 5)
export const CANONICAL_ELEANOR_ALERT: EmergencyPayload = {
  memberId: "00000000-0000-0000-0000-000000000002",
  memberName: "Eleanor Vance",
  condition: "Cardiac Arrhythmia / Pacemaker Active",
  bloodGroup: "A+",
  allergies: ["Penicillin", "Sulfa Drugs"],
  medicalNotes: [
    "St. Jude Medical Dual-Chamber Pacemaker (2021)",
    "Strict contraindication: No high-field MRI without cardiac clearance",
    "Requires immediate telemetry upon ER admission",
  ],
  emergencyContact: {
    name: "Dr. R. K. Sharma",
    hospital: "AIIMS Cardiology Emergency Care",
    phone: "+91-11-26588500",
  },
  signedTokenPassUrl: "https://familyvault.internal/api/v1/health/emergency-pass/eleanor-vance-24h",
  isActive: true,
};

interface EmergencyAlertOverlayProps {
  alertData?: EmergencyPayload;
  isOpen: boolean;
  onClose: () => void;
}

export function EmergencyAlertDossierModal({
  alertData = CANONICAL_ELEANOR_ALERT,
  isOpen,
  onClose,
}: EmergencyAlertOverlayProps) {
  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="emergency-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm animate-in fade-in duration-200"
    >
      <div className="relative w-full max-w-lg overflow-hidden rounded-2xl border-2 border-rose-500 bg-white p-6 shadow-2xl dark:bg-slate-900">
        {/* Header Banner */}
        <div className="flex items-start justify-between border-b border-rose-100 pb-3 dark:border-rose-950">
          <div className="flex items-center gap-2.5">
            <span className="flex h-4 w-4 rounded-full bg-rose-600 animate-ping" />
            <div>
              <h2 id="emergency-title" className="text-lg font-black tracking-wide text-rose-600 uppercase">
                Emergency Medical Red Alert
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                AIIMS Immediate Response Telemetry Pass
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close Emergency Dossier"
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
          >
            ✕
          </button>
        </div>

        {/* Member & Critical Info */}
        <div className="mt-4 space-y-3">
          <div className="flex items-center justify-between rounded-lg bg-rose-50 p-3 border border-rose-200 dark:bg-rose-950/40 dark:border-rose-900">
            <div>
              <p className="text-xs font-semibold text-rose-950 dark:text-rose-200">
                Patient: <span className="text-sm font-bold">{alertData.memberName}</span>
              </p>
              <p className="text-xs text-rose-700 dark:text-rose-300 font-medium">
                {alertData.condition}
              </p>
            </div>
            <div className="text-right">
              <span className="rounded bg-rose-600 px-2.5 py-1 text-xs font-black text-white">
                Blood: {alertData.bloodGroup}
              </span>
            </div>
          </div>

          {/* Allergies and Critical Notes */}
          <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
            <p className="text-[11px] font-bold tracking-wider text-rose-600 uppercase">
              Severe Contraindicated Allergies
            </p>
            <div className="mt-1 flex flex-wrap gap-1.5">
              {alertData.allergies.map((allergy, idx) => (
                <span
                  key={idx}
                  className="rounded-md bg-rose-100 px-2 py-0.5 text-xs font-bold text-rose-800 dark:bg-rose-950 dark:text-rose-300"
                >
                  ⚠️ {allergy}
                </span>
              ))}
            </div>

            <p className="mt-3 text-[11px] font-bold tracking-wider text-slate-600 uppercase dark:text-slate-400">
              Clinical Directive & Pacemaker Specs
            </p>
            <ul className="mt-1 space-y-1">
              {alertData.medicalNotes.map((note, idx) => (
                <li key={idx} className="text-xs text-slate-700 dark:text-slate-300 leading-snug">
                  • {note}
                </li>
              ))}
            </ul>
          </div>

          {/* Emergency Hospital Contact */}
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-800/60">
            <p className="text-[10px] font-bold tracking-wider text-slate-500 uppercase dark:text-slate-400">
              Assigned Emergency Contact
            </p>
            <div className="mt-1 flex items-center justify-between text-xs">
              <div>
                <p className="font-bold text-slate-900 dark:text-slate-100">
                  {alertData.emergencyContact.name}
                </p>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  {alertData.emergencyContact.hospital}
                </p>
              </div>
              <a
                href={`tel:${alertData.emergencyContact.phone}`}
                className="rounded-md bg-rose-600 px-3 py-1.5 font-bold text-white shadow-sm hover:bg-rose-700"
              >
                Call Hotline
              </a>
            </div>
          </div>

          {/* Scannable Offline Pass Simulation */}
          <div className="flex items-center justify-between rounded-lg border border-dashed border-rose-300 bg-rose-50/50 p-3 dark:border-rose-900 dark:bg-rose-950/20">
            <div className="text-xs">
              <p className="font-bold text-rose-900 dark:text-rose-200">
                24-Hour Signed Offline Emergency QR
              </p>
              <p className="text-[10px] text-slate-500 dark:text-slate-400">
                Instant cryptographic token verification for first responders
              </p>
            </div>
            <div className="flex h-12 w-12 items-center justify-center rounded border border-slate-300 bg-white font-mono text-[9px] font-bold text-slate-800 shadow-sm dark:bg-slate-800 dark:text-slate-100">
              [QR]
            </div>
          </div>
        </div>

        <button
          onClick={onClose}
          className="mt-4 w-full rounded-xl bg-slate-900 py-2.5 text-xs font-bold text-white hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
        >
          Dismiss Medical Alert Dossier
        </button>
      </div>
    </div>
  );
}
