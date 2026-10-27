"use client";

import React, { useState } from "react";
import CharacterStage from "./CharacterStage";
import LoginForm from "./LoginForm";

export default function LoginCard() {
  const [emailFocused, setEmailFocused] = useState(false);
  const [passwordFocused, setPasswordFocused] = useState(false);
  const [emailHovered, setEmailHovered] = useState(false);
  const [passwordHovered, setPasswordHovered] = useState(false);
  const [passwordRevealed, setPasswordRevealed] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [passwordLength, setPasswordLength] = useState(0);
  const [emailLength, setEmailLength] = useState(0);
  const [keystrokeCount, setKeystrokeCount] = useState(0);
  const [isPasswordLiveWrong, setIsPasswordLiveWrong] = useState(false);
  const [isPasswordLiveCorrect, setIsPasswordLiveCorrect] = useState(false);

  const handlePasswordChange = (val: string) => {
    setPasswordLength(val.length);
    setKeystrokeCount((c) => c + 1);
  };

  const handleEmailChange = (val: string) => {
    setEmailLength(val.length);
    setKeystrokeCount((c) => c + 1);
  };

  const handlePasswordLiveStatus = ({
    isLiveWrong,
    isLiveCorrect,
  }: {
    isLiveWrong: boolean;
    isLiveCorrect: boolean;
  }) => {
    setIsPasswordLiveWrong(isLiveWrong);
    setIsPasswordLiveCorrect(isLiveCorrect);
  };

  return (
    <div className="min-h-screen w-full bg-[#f3f4f6] flex items-center justify-center p-4">
      <div className="w-full max-w-4xl bg-white rounded-3xl shadow-xl overflow-hidden grid grid-cols-1 md:grid-cols-[56.9%_43.1%] min-h-[620px]">
        {/* Left Panel: Character Stage */}
        <div className="relative bg-[#E8E8E8] flex items-center justify-center p-8 border-b md:border-b-0 md:border-r border-gray-200 select-none overflow-hidden min-h-[300px] md:min-h-auto">
          <CharacterStage
            emailFocused={emailFocused}
            passwordFocused={passwordFocused}
            emailHovered={emailHovered}
            passwordHovered={passwordHovered}
            passwordRevealed={passwordRevealed}
            hasError={hasError}
            passwordLength={passwordLength}
            emailLength={emailLength}
            keystrokeCount={keystrokeCount}
            isPasswordLiveWrong={isPasswordLiveWrong}
            isPasswordLiveCorrect={isPasswordLiveCorrect}
          />
        </div>

        {/* Right Panel: Clean Underline Login Form */}
        <LoginForm
          onEmailFocusChange={setEmailFocused}
          onPasswordFocusChange={setPasswordFocused}
          onEmailHoverChange={setEmailHovered}
          onPasswordHoverChange={setPasswordHovered}
          onPasswordRevealChange={setPasswordRevealed}
          onPasswordChange={handlePasswordChange}
          onEmailChange={handleEmailChange}
          onErrorChange={setHasError}
          onPasswordLiveStatusChange={handlePasswordLiveStatus}
          hasError={hasError}
        />
      </div>
    </div>
  );
}
