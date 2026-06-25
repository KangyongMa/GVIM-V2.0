"use client";

import confetti from "canvas-confetti";
import {
  X,
  ArrowLeft,
  ArrowRight,
  Sparkles,
  Compass,
  Brain,
  LayoutGrid,
  Play,
  Check,
  Settings,
} from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState, useRef, useCallback, useMemo } from "react";

import { Button } from "@/components/ui/button";
import { useSidebar } from "@/components/ui/sidebar";
import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";

interface Step {
  target: string;
  titleKey:
    | "welcomeTitle"
    | "sidebarTitle"
    | "inputTitle"
    | "toolkitTitle"
    | "settingsIntroTitle"
    | "settingsLlmTitle"
    | "settingsScienceTitle"
    | "settingsToolsTitle"
    | "settingsIntegrationsTitle"
    | "settingsSkillsTitle";
  descKey:
    | "welcomeDesc"
    | "sidebarDesc"
    | "inputDesc"
    | "toolkitDesc"
    | "settingsIntroDesc"
    | "settingsLlmDesc"
    | "settingsScienceDesc"
    | "settingsToolsDesc"
    | "settingsIntegrationsDesc"
    | "settingsSkillsDesc";
  icon: React.ReactNode;
  placement: "center" | "right" | "top" | "bottom" | "bottom-left";
}

const LOCAL_STORAGE_KEY = "gvim_onboarding_tour_completed";
const TRIGGER_EVENT = "gvim-trigger-onboarding-tour";

export function OnboardingTour() {
  const { t } = useI18n();
  const { open: isSidebarOpen, setOpen: setSidebarOpen } = useSidebar();
  const [isActive, setIsActive] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [displayedStep, setDisplayedStep] = useState(0);
  const [targetRect, setTargetRect] = useState<DOMRect | null>(null);
  const [windowSize, setWindowSize] = useState({ width: 0, height: 0 });
  const [cardPosition, setCardPosition] = useState({ top: 0, left: 0 });
  const cardRef = useRef<HTMLDivElement>(null);

  // Define translations securely with fallback support
  const tourT = t.onboardingTour ?? {
    welcomeTitle: "Welcome to GVIM AI",
    welcomeDesc: "Your intelligent agent workspace designed specifically for chemical and materials science research. Let's take a quick 1-minute tour to get familiar with the workspace!",
    sidebarTitle: "Workspace Navigation",
    sidebarDesc: "This is your control center. Create new chat threads, access historical conversations, and manage custom agent skills or settings here.",
    inputTitle: "Reasoning Depth & Input",
    inputDesc: "Ask questions, paste calculations, or import files here. You can select your desired AI mode (Flash, Reasoning, Pro, Ultra) to adjust how deep the AI agent and sub-agents think.",
    toolkitTitle: "Scientific Toolkit & Artifacts",
    toolkitDesc: "Monitor your token budget, export chats, and open the Artifacts drawer. When the AI generates 3D molecules, diagrams, or code, they are displayed beautifully inside the Artifacts drawer.",
    settingsIntroTitle: "System Configuration Portal",
    settingsIntroDesc: "This is your Settings and API key portal. Let's open it to set up your AI models and database connection keys!",
    settingsLlmTitle: "Activate AI Provider Keys",
    settingsLlmDesc: "Input your AI provider keys here! Paste your Gemini, DeepSeek, or Qwen API keys and click 'Save' to activate your core research assistants. Without this, the system won't respond.",
    settingsScienceTitle: "Unlock Computational Tools",
    settingsScienceDesc: "Input your Materials Project (MP) or Citrination API keys here to unlock professional computational tools, material structure databases, and advanced scientific query skills!",
    settingsToolsTitle: "Connect Custom Tools & MCP",
    settingsToolsDesc: "Configure Model Context Protocol (MCP) servers here. Expose external databases, code sandboxes, or search tools directly to your LLM agent to expand its capabilities.",
    settingsIntegrationsTitle: "Connect Third-Party Chat Channels",
    settingsIntegrationsDesc: "Connect your research assistant to Telegram, WeChat, Feishu, DingTalk, Slack, or Discord! Let the AI chat with you and run calculations right in your mobile/team chat app.",
    settingsSkillsTitle: "Enable Chemistry & Scientific Skills",
    settingsSkillsDesc: "Manage custom scientific workflow skills here. Enable built-in or custom chemistry research skill plugins to query material properties and execute synthesis pathways.",
    startBtn: "Start Tour",
    skipBtn: "Skip",
    nextBtn: "Next",
    prevBtn: "Back",
    finishBtn: "Finish 🎉",
    toastFinished: "Enjoy your scientific journey with GVIM AI!",
    restartBtn: "Restart Guide Tour",
    configureBtn: "Configure AI & Tools",
  };

  const steps: Step[] = useMemo(() => [
    {
      target: "",
      titleKey: "welcomeTitle",
      descKey: "welcomeDesc",
      icon: <Sparkles className="size-6 text-emerald-400 animate-pulse" />,
      placement: "center",
    },
    {
      target: '[data-sidebar="sidebar"]',
      titleKey: "sidebarTitle",
      descKey: "sidebarDesc",
      icon: <Compass className="size-6 text-cyan-400" />,
      placement: "right",
    },
    {
      target: "#prompt-input-container",
      titleKey: "inputTitle",
      descKey: "inputDesc",
      icon: <Brain className="size-6 text-indigo-400 animate-pulse" />,
      placement: "top",
    },
    {
      target: '[data-tour="header-actions"]',
      titleKey: "toolkitTitle",
      descKey: "toolkitDesc",
      icon: <LayoutGrid className="size-6 text-purple-400" />,
      placement: "bottom-left",
    },
    {
      target: '[data-tour="settings-menu-button"]',
      titleKey: "settingsIntroTitle",
      descKey: "settingsIntroDesc",
      icon: <Settings className="size-6 text-yellow-400 animate-spin-slow" />,
      placement: "right",
    },
    {
      target: '[data-tour="llm-keys-card"]',
      titleKey: "settingsLlmTitle",
      descKey: "settingsLlmDesc",
      icon: <Brain className="size-6 text-purple-400 animate-pulse" />,
      placement: "bottom",
    },
    {
      target: '[data-tour="science-keys-card"]',
      titleKey: "settingsScienceTitle",
      descKey: "settingsScienceDesc",
      icon: <Sparkles className="size-6 text-emerald-400" />,
      placement: "bottom",
    },
    {
      target: '[data-tour="mcp-servers-container"]',
      titleKey: "settingsToolsTitle",
      descKey: "settingsToolsDesc",
      icon: <Settings className="size-6 text-cyan-400" />,
      placement: "bottom",
    },
    {
      target: '[data-tour="im-integrations-container"]',
      titleKey: "settingsIntegrationsTitle",
      descKey: "settingsIntegrationsDesc",
      icon: <Settings className="size-6 text-indigo-400" />,
      placement: "bottom",
    },
    {
      target: '[data-tour="skills-settings-container"]',
      titleKey: "settingsSkillsTitle",
      descKey: "settingsSkillsDesc",
      icon: <Sparkles className="size-6 text-pink-400" />,
      placement: "bottom",
    },
  ], []);

  // Initialize and check localStorage
  useEffect(() => {
    if (typeof window !== "undefined") {
      setWindowSize({ width: window.innerWidth, height: window.innerHeight });

      const completed = localStorage.getItem(LOCAL_STORAGE_KEY);
      if (!completed) {
        // Delay slightly for elements to mount and render fully
        const timer = setTimeout(() => {
          setIsActive(true);
        }, 1200);
        return () => clearTimeout(timer);
      }
    }
  }, []);

  // Listen to custom restart event
  useEffect(() => {
    const handleRestart = () => {
      setCurrentStep(0);
      setIsActive(true);
      // Auto-open sidebar if it is closed for the sidebar step
      if (!isSidebarOpen) {
        setSidebarOpen(true);
      }
    };

    window.addEventListener(TRIGGER_EVENT, handleRestart);
    return () => {
      window.removeEventListener(TRIGGER_EVENT, handleRestart);
    };
  }, [isSidebarOpen, setSidebarOpen]);

  // Handle window resizing
  useEffect(() => {
    const handleResize = () => {
      setWindowSize({ width: window.innerWidth, height: window.innerHeight });
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Automatically switch Settings Dialog tabs when currentStep changes
  useEffect(() => {
    if (!isActive) return;
    const step = steps[currentStep];
    if (step) {
      if (step.titleKey === "settingsLlmTitle" || step.titleKey === "settingsScienceTitle") {
        window.dispatchEvent(new CustomEvent("gvim-open-settings", { detail: { section: "models" } }));
      } else if (step.titleKey === "settingsToolsTitle") {
        window.dispatchEvent(new CustomEvent("gvim-open-settings", { detail: { section: "tools" } }));
      } else if (step.titleKey === "settingsIntegrationsTitle") {
        window.dispatchEvent(new CustomEvent("gvim-open-settings", { detail: { section: "integrations" } }));
      } else if (step.titleKey === "settingsSkillsTitle") {
        window.dispatchEvent(new CustomEvent("gvim-open-settings", { detail: { section: "skills" } }));
      }
    }
  }, [currentStep, isActive, steps]);

  // Synchronize currentStep to displayedStep when target element is ready in DOM
  useEffect(() => {
    if (!isActive) return;

    const step = steps[currentStep];
    if (!step) return;

    // Auto-open sidebar if we are highlighting the sidebar
    if (step.target === '[data-sidebar="sidebar"]' && !isSidebarOpen) {
      setSidebarOpen(true);
    }

    if (!step.target) {
      // If there is no target (e.g. center placement for welcome step), update immediately
      setTargetRect(null);
      setDisplayedStep(currentStep);
      return;
    }

    let attempts = 0;
    const maxAttempts = 30; // 30 * 100ms = 3s max wait

    const checkElement = () => {
      const el = document.querySelector(step.target);
      if (el) {
        const rect = el.getBoundingClientRect();
        // Ensure element is actually rendered and visible (has non-zero width/height)
        if (rect.width > 0 && rect.height > 0) {
          setTargetRect(rect);
          setDisplayedStep(currentStep);
          return true;
        }
      }
      return false;
    };

    if (checkElement()) return;

    const interval = setInterval(() => {
      attempts++;
      if (checkElement() || attempts >= maxAttempts) {
        clearInterval(interval);
        // Fallback if we timeout
        if (attempts >= maxAttempts) {
          console.warn(`OnboardingTour: Target element ${step.target} not found after timeout, displaying step.`);
          setTargetRect(null);
          setDisplayedStep(currentStep);
        }
      }
    }, 100);

    return () => clearInterval(interval);
  }, [currentStep, isActive, isSidebarOpen, setSidebarOpen, steps]);

  // Keep targetRect in sync with the displayed step's element for scrolling/resizing
  const updateTargetRect = useCallback(() => {
    if (!isActive) {
      setTargetRect(null);
      return;
    }

    const step = steps[displayedStep];
    if (!step?.target) {
      setTargetRect(null);
      return;
    }

    const el = document.querySelector(step.target);
    if (el) {
      const rect = el.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0) {
        setTargetRect((prev) => {
          if (!prev) return rect;
          const diffX = Math.abs(rect.x - prev.x);
          const diffY = Math.abs(rect.y - prev.y);
          const diffW = Math.abs(rect.width - prev.width);
          const diffH = Math.abs(rect.height - prev.height);
          // If shift is negligible (less than 2px), do not update to prevent micro-tremors
          if (diffX < 2 && diffY < 2 && diffW < 2 && diffH < 2) {
            return prev;
          }
          return rect;
        });
      }
    }
  }, [isActive, displayedStep, steps]);

  useEffect(() => {
    updateTargetRect();
    const interval = setInterval(updateTargetRect, 200);
    return () => clearInterval(interval);
  }, [updateTargetRect]);

  // Compute the perfect card positioning based on targeted element rect and placement preference
  useEffect(() => {
    if (!isActive) return;

    const step = steps[displayedStep];
    if (!step) return;

    if (step.placement === "center" || !targetRect) {
      // Centered dialog placement
      setCardPosition({
        top: windowSize.height / 2 - (cardRef.current?.offsetHeight ?? 220) / 2,
        left: windowSize.width / 2 - (cardRef.current?.offsetWidth ?? 420) / 2,
      });
      return;
    }

    const cardWidth = cardRef.current?.offsetWidth ?? 380;
    const cardHeight = cardRef.current?.offsetHeight ?? 200;
    const gap = 16;

    let top = 0;
    let left = 0;

    switch (step.placement) {
      case "right":
        top = Math.max(gap, Math.min(targetRect.top + 80, windowSize.height - cardHeight - gap));
        left = targetRect.right + gap;
        break;
      case "top":
        top = targetRect.top - cardHeight - gap;
        left = Math.max(gap, Math.min(targetRect.left + targetRect.width / 2 - cardWidth / 2, windowSize.width - cardWidth - gap));
        break;
      case "bottom-left":
        top = targetRect.bottom + gap;
        left = Math.max(gap, Math.min(targetRect.right - cardWidth, windowSize.width - cardWidth - gap));
        break;
      case "bottom":
      default:
        top = targetRect.bottom + gap;
        left = Math.max(gap, Math.min(targetRect.left + targetRect.width / 2 - cardWidth / 2, windowSize.width - cardWidth - gap));
        break;
    }

    // Secondary viewport boundary check to prevent card overflow
    if (left < gap) left = gap;
    if (left + cardWidth > windowSize.width - gap) left = windowSize.width - cardWidth - gap;
    if (top < gap) top = gap;
    if (top + cardHeight > windowSize.height - gap) top = windowSize.height - cardHeight - gap;

    setCardPosition({ top, left });
  }, [isActive, displayedStep, targetRect, windowSize, steps]);

  // Actions
  const handleClose = () => {
    setIsActive(false);
    localStorage.setItem(LOCAL_STORAGE_KEY, "true");
  };

  const handleNext = () => {
    const step = steps[currentStep];
    if (step?.titleKey === "settingsIntroTitle") {
      // Auto-open settings dialog
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("gvim-open-settings", { detail: { section: "models" } }));
      }
      // Give dialog modal a brief moment to mount and render, then advance step
      setTimeout(() => {
        setCurrentStep((prev) => prev + 1);
      }, 350);
      return;
    }

    if (currentStep < steps.length - 1) {
      setCurrentStep((prev) => prev + 1);
    } else {
      // Completed! Trigger confetti 🎉
      triggerCelebration();
      handleClose();
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep((prev) => prev - 1);
    }
  };

  const triggerCelebration = () => {
    const duration = 2.5 * 1000;
    const end = Date.now() + duration;

    const frame = () => {
      confetti({
        particleCount: 4,
        angle: 60,
        spread: 55,
        origin: { x: 0, y: 0.8 },
        colors: ["#10b981", "#06b6d4", "#6366f1", "#a855f7"],
      });
      confetti({
        particleCount: 4,
        angle: 120,
        spread: 55,
        origin: { x: 1, y: 0.8 },
        colors: ["#10b981", "#06b6d4", "#6366f1", "#a855f7"],
      });

      if (Date.now() < end) {
        requestAnimationFrame(frame);
      }
    };
    frame();
  };

  if (!isActive) return null;

  const currentStepData = steps[displayedStep];
  if (!currentStepData) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden pointer-events-none select-none">
      {/* Dynamic SVG Spotlight overlay mask */}
      <svg className="absolute inset-0 pointer-events-auto z-40 size-full">
        <defs>
          <mask id="gvim-onboarding-spotlight-mask">
            {/* White represents opaque masking (preserves background color) */}
            <rect x="0" y="0" width="100%" height="100%" fill="white" />
            {/* Black represents transparency cutout */}
            {targetRect && (
              <rect
                x={targetRect.x - 8}
                y={targetRect.y - 8}
                width={targetRect.width + 16}
                height={targetRect.height + 16}
                rx="14"
                ry="14"
                fill="black"
                className="transition-all duration-300 ease-out"
              />
            )}
          </mask>
        </defs>
        <rect
          x="0"
          y="0"
          width="100%"
          height="100%"
          fill="rgba(3, 5, 8, 0.72)"
          mask="url(#gvim-onboarding-spotlight-mask)"
          className="backdrop-blur-[1px] transition-all duration-300"
          onClick={handleClose}
        />
      </svg>

      {/* Floating Interactive Tooltip Dialog */}
      <AnimatePresence mode="wait">
        <motion.div
          key={displayedStep}
          ref={cardRef}
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: -10 }}
          transition={{ duration: 0.25, ease: "easeOut" }}
          style={{
            position: "absolute",
            top: cardPosition.top,
            left: cardPosition.left,
          }}
          className={cn(
            "pointer-events-auto z-50 w-full max-w-[390px] md:max-w-[420px]",
            "rounded-2xl border border-white/10 bg-[#070b12]/90 p-6 shadow-2xl backdrop-blur-xl",
            "before:absolute before:inset-0 before:-z-10 before:rounded-2xl before:bg-gradient-to-b before:from-white/5 before:to-transparent before:content-['']",
            "after:absolute after:inset-0 after:-z-20 after:rounded-2xl after:shadow-[0_0_30px_-5px_rgba(16,185,129,0.15)] after:content-['']",
          )}
        >
          {/* Header */}
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/5 border border-white/10">
                {currentStepData.icon}
              </div>
              <div>
                <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
                  Step {displayedStep + 1} of {steps.length}
                </span>
                <h3 className="text-lg font-bold text-zinc-100 mt-0.5 leading-snug">
                  {tourT[currentStepData.titleKey]}
                </h3>
              </div>
            </div>
            <button
              onClick={handleClose}
              className="text-zinc-400 hover:text-zinc-100 transition-colors p-1 rounded-lg hover:bg-white/5"
            >
              <X className="size-4" />
            </button>
          </div>

          {/* Description */}
          <p className="mt-4 text-sm leading-relaxed text-zinc-300">
            {tourT[currentStepData.descKey]}
          </p>

          {/* Divider & Footer Navigation Buttons */}
          <div className="mt-8 flex items-center justify-between gap-3 border-t border-white/5 pt-4">
            {/* Left side: Skip button (if not Step 0, to balance layout) */}
            <div>
              {displayedStep > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleClose}
                  className="h-8 text-xs text-zinc-400 hover:text-zinc-200 hover:bg-white/5 px-2.5"
                >
                  {tourT.skipBtn}
                </Button>
              )}
            </div>

            {/* Right side: Back + Next/Configure buttons */}
            <div className="flex items-center gap-2">
              {displayedStep > 0 ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handlePrev}
                  className="h-8 border-white/5 bg-transparent hover:bg-white/5 text-xs text-zinc-300 hover:text-zinc-100 gap-1.5 px-3"
                >
                  <ArrowLeft className="size-3.5" />
                  {tourT.prevBtn}
                </Button>
              ) : (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleClose}
                  className="h-8 text-xs text-zinc-400 hover:text-zinc-200 hover:bg-white/5 px-2.5"
                >
                  {tourT.skipBtn}
                </Button>
              )}

              <Button
                size="sm"
                onClick={handleNext}
                className={cn(
                  "h-8 gap-1.5 shadow-md transition-all duration-300 text-xs px-3.5",
                  displayedStep === steps.length - 1
                    ? "bg-gradient-to-r from-emerald-500 to-cyan-500 text-zinc-950 font-bold hover:brightness-110 border-0"
                    : currentStepData.titleKey === "settingsIntroTitle"
                    ? "bg-gradient-to-r from-amber-400 to-yellow-500 text-zinc-950 font-bold hover:brightness-110 border-0"
                    : "bg-zinc-100 text-zinc-950 hover:bg-zinc-200 font-medium"
                )}
              >
                {displayedStep === steps.length - 1 ? (
                  <>
                    {tourT.finishBtn}
                    <Check className="size-3.5 stroke-[3px]" />
                  </>
                ) : currentStepData.titleKey === "settingsIntroTitle" ? (
                  <>
                    {tourT.configureBtn}
                    <Settings className="size-3.5 text-zinc-950 animate-spin-slow" />
                  </>
                ) : displayedStep === 0 ? (
                  <>
                    {tourT.startBtn}
                    <Play className="size-3.5 fill-current" />
                  </>
                ) : (
                  <>
                    {tourT.nextBtn}
                    <ArrowRight className="size-3.5" />
                  </>
                )}
              </Button>
            </div>
          </div>

          {/* Sleek bottom progress bar */}
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-zinc-900 rounded-b-2xl overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500 transition-all duration-300 ease-out"
              style={{ width: `${((displayedStep + 1) / steps.length) * 100}%` }}
            />
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
