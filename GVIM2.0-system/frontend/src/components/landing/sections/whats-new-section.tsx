"use client";

import { Database, Cpu, Beaker, Terminal, Microscope, ShieldCheck } from "lucide-react";
import MagicBento, { type BentoCardProps } from "@/components/ui/magic-bento";
import { cn } from "@/lib/utils";

import { Section } from "../section";

const features: BentoCardProps[] = [
  {
    color: "rgba(8, 12, 24, 0.45)",
    label: (
      <span className="rounded-full bg-emerald-500/10 border border-emerald-500/25 px-2.5 py-0.5 text-[10px] font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1">
        <span className="size-1.5 rounded-full bg-emerald-400 animate-pulse" />
        科学长效记忆
      </span>
    ),
    title: <span className="text-zinc-100 font-semibold tracking-tight text-base">分子与上下文记忆网络</span>,
    description: (
      <div className="relative w-full h-full flex flex-col justify-end">
        {/* Animated Molecular Network */}
        <div className="relative w-full h-[64px] flex items-center justify-center overflow-hidden mb-3 bg-emerald-950/10 border border-emerald-900/10 rounded-lg">
          <div className="absolute size-6 rounded-full bg-emerald-500/10 border border-emerald-500/20 animate-pulse flex items-center justify-center">
            <div className="size-1.5 rounded-full bg-emerald-400" />
          </div>
          <div className="absolute w-12 h-6 rounded-full border border-emerald-500/15 rotate-[30deg] animate-[spin_6s_linear_infinite]" />
          <div className="absolute w-12 h-6 rounded-full border border-emerald-500/15 rotate-[-30deg] animate-[spin_8s_linear_infinite]" />
          <Database className="absolute bottom-1 right-2 size-5 text-emerald-400/5" />
        </div>
        <span className="relative z-10">提供结构化记忆图谱，智能关联和记忆科研对话中提到的 SMILES 表达式、分子结构片段与实验参数，为连续实验提供精准参考。</span>
      </div>
    ),
  },
  {
    color: "rgba(8, 12, 24, 0.45)",
    label: (
      <span className="rounded-full bg-cyan-500/10 border border-cyan-500/25 px-2.5 py-0.5 text-[10px] font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-1">
        <span className="size-1.5 rounded-full bg-cyan-400 animate-pulse" />
        多智能体协作
      </span>
    ),
    title: <span className="text-zinc-100 font-semibold tracking-tight text-base">科学多智能体编排引擎</span>,
    description: (
      <div className="relative w-full h-full flex flex-col justify-end">
        {/* Animated Satellites Pulse */}
        <div className="relative w-full h-[64px] flex items-center justify-center overflow-hidden mb-3 bg-cyan-950/10 border border-cyan-900/10 rounded-lg">
          <div className="size-2 rounded-full bg-cyan-400 shadow-[0_0_6px_rgba(34,211,238,0.4)] z-10 animate-pulse" />
          <div className="absolute -translate-x-8 size-1.5 rounded-full bg-cyan-500/40 animate-ping" />
          <div className="absolute -translate-x-8 size-1.5 rounded-full bg-cyan-500" />
          <div className="absolute translate-x-8 size-1.5 rounded-full bg-cyan-500/40 animate-ping" />
          <div className="absolute translate-x-8 size-1.5 rounded-full bg-cyan-500" />
          <div className="absolute size-10 rounded-full border border-cyan-500/10 animate-[ping_2s_ease-in-out_infinite]" />
          <Cpu className="absolute bottom-1 right-2 size-5 text-cyan-400/5" />
        </div>
        <span className="relative z-10">人机协同式多智能体架构，辅助开展文献数据挖掘、合成路线智能推荐以及量子化学性质预测的辅助规划。</span>
      </div>
    ),
  },
  {
    color: "rgba(8, 12, 24, 0.45)",
    label: (
      <span className="rounded-full bg-blue-500/10 border border-blue-500/25 px-2.5 py-0.5 text-[10px] font-bold text-blue-400 uppercase tracking-wider flex items-center gap-1">
        <span className="size-1.5 rounded-full bg-blue-400 animate-pulse" />
        底层引擎生态
      </span>
    ),
    title: <span className="text-zinc-100 font-semibold tracking-tight text-base">内置 130+ 科学技能库</span>,
    description: (
      <div className="relative w-full h-full flex flex-col justify-end">
        {/* Animated Molecular Structure Rotating (Large Card) */}
        <div className="relative w-full h-[180px] flex flex-col items-center justify-center overflow-hidden mb-3 bg-[#04060a]/70 border border-blue-900/10 rounded-xl">
          <div className="absolute size-28 rounded-full border border-blue-500/[0.05] animate-[spin_16s_linear_infinite] flex items-center justify-center">
            <div className="absolute top-0 size-2 rounded-full bg-blue-400 shadow-[0_0_6px_rgba(59,130,246,0.4)]" />
            <div className="absolute bottom-0 size-2 rounded-full bg-blue-400 shadow-[0_0_6px_rgba(59,130,246,0.4)]" />
            <div className="absolute left-0 size-1.5 rounded-full bg-teal-400" />
            <div className="absolute right-0 size-1.5 rounded-full bg-teal-400" />
          </div>
          <div className="absolute size-16 rounded-full border border-blue-500/[0.08] animate-[spin_10s_linear_infinite_reverse] flex items-center justify-center">
            <div className="absolute top-0 size-1.5 rounded-full bg-indigo-400" />
            <div className="absolute bottom-0 size-1.5 rounded-full bg-indigo-400" />
          </div>
          <div className="size-3 rounded-full bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.6)] z-10 animate-pulse" />
          <Beaker className="absolute bottom-2 right-3 size-6 text-blue-400/5" />
        </div>
        <span className="relative z-10">预置丰富的科研工具箱，支持快速调用 RDKit 分析分子、pymatgen 辅助构建晶胞，并能自动生成 Opentrons 实验脚本。</span>
      </div>
    ),
  },

  {
    color: "rgba(8, 12, 24, 0.45)",
    label: (
      <span className="rounded-full bg-indigo-500/10 border border-indigo-500/25 px-2.5 py-0.5 text-[10px] font-bold text-indigo-400 uppercase tracking-wider flex items-center gap-1">
        <span className="size-1.5 rounded-full bg-indigo-400 animate-pulse" />
        沙盒安全底座
      </span>
    ),
    title: <span className="text-zinc-100 font-semibold tracking-tight text-base">隔离的物理仿真沙盒</span>,
    description: (
      <div className="relative w-full h-full flex flex-col justify-end">
        {/* Animated Coding Console Logging (Large Card) */}
        <div className="relative w-full h-[180px] flex flex-col justify-start overflow-hidden mb-3 bg-[#020408]/90 border border-indigo-950/40 rounded-xl p-3 font-mono text-[9px] text-zinc-500">
          <div className="flex items-center justify-between pb-1.5 border-b border-indigo-950/50">
            <div className="flex gap-1">
              <span className="size-1.5 rounded-full bg-red-500/30" />
              <span className="size-1.5 rounded-full bg-yellow-500/30" />
              <span className="size-1.5 rounded-full bg-green-500/30" />
            </div>
            <span className="text-[7.5px] text-indigo-400/40">gvim-sandbox-console</span>
          </div>
          <div className="pt-2 space-y-1 text-left leading-[1.4]">
            <div className="flex items-center gap-1 text-emerald-400/70">
              <span>&gt;</span>
              <span>pip install pymatgen rdkit</span>
            </div>
            <div className="text-zinc-600 flex items-center gap-1 pl-2">
              <span className="size-1 rounded-full bg-emerald-400 animate-pulse" />
              <span>Loaded cached wheels for rdkit (2026.03.1)</span>
            </div>
            <div className="flex items-center gap-1 text-indigo-400/70 mt-1">
              <span>&gt;</span>
              <span>python run_dft_prediction.py</span>
            </div>
            <div className="text-blue-400/60 pl-2">
              <span>Perovskite lattice Pm-3m checked successfully.</span>
            </div>
            <div className="text-zinc-700 animate-pulse pl-2">
              <span>_ (Sandbox isolated, awaiting computation...)</span>
            </div>
          </div>
          <Terminal className="absolute bottom-2 right-3 size-6 text-indigo-400/5" />
        </div>
        <span className="relative z-10">提供本地隔离的科学计算沙箱，预装编译环境，在用户可控的安全容器中辅助运行分子动力学模拟或数据处理脚本。</span>
      </div>
    ),
  },
  {
    color: "rgba(8, 12, 24, 0.45)",
    label: (
      <span className="rounded-full bg-purple-500/10 border border-purple-500/25 px-2.5 py-0.5 text-[10px] font-bold text-purple-400 uppercase tracking-wider flex items-center gap-1">
        <span className="size-1.5 rounded-full bg-purple-400 animate-pulse" />
        进阶科研推理
      </span>
    ),
    title: <span className="text-zinc-100 font-semibold tracking-tight text-base">自动化全流程科学研究</span>,
    description: (
      <div className="relative w-full h-full flex flex-col justify-end">
        {/* Animated Radar Scanning */}
        <div className="relative w-full h-[64px] flex items-center justify-center overflow-hidden mb-3 bg-purple-950/10 border border-purple-900/10 rounded-lg">
          <div className="absolute size-10 rounded-full border border-purple-500/[0.05]" />
          <div className="absolute size-6 rounded-full border border-purple-500/[0.08]" />
          <div className="absolute w-[20px] h-[0.75px] bg-gradient-to-r from-purple-400/70 to-transparent origin-left top-1/2 left-1/2 animate-[spin_4s_linear_infinite]" />
          <div className="absolute -translate-y-2 translate-x-2 size-1 rounded-full bg-purple-400 animate-pulse" />
          <div className="absolute translate-y-2 -translate-x-3 size-0.5 rounded-full bg-indigo-400" />
          <Microscope className="absolute bottom-1 right-2 size-5 text-purple-400/5" />
        </div>
        <span className="relative z-10">支持长时序人机交互式科研探索，引导科研人员开展文献检索，辅助提取关键数据，并逐步提炼高价值科研洞察。</span>
      </div>
    ),
  },
  {
    color: "rgba(8, 12, 24, 0.45)",
    label: (
      <span className="rounded-full bg-teal-500/10 border border-teal-500/25 px-2.5 py-0.5 text-[10px] font-bold text-teal-400 uppercase tracking-wider flex items-center gap-1">
        <span className="size-1.5 rounded-full bg-teal-400 animate-pulse" />
        数据资产安全
      </span>
    ),
    title: <span className="text-zinc-100 font-semibold tracking-tight text-base">100% 私有化本地部署</span>,
    description: (
      <div className="relative w-full h-full flex flex-col justify-end">
        {/* Animated Secure Local Server LED Stack */}
        <div className="relative w-full h-[64px] flex flex-col gap-1 items-center justify-center overflow-hidden mb-3 bg-teal-950/10 border border-teal-900/10 rounded-lg">
          <div className="w-16 h-2 rounded bg-zinc-900/90 border border-teal-900/20 flex items-center justify-between px-1.5">
            <div className="w-4 h-0.5 rounded bg-teal-500/10" />
            <div className="flex gap-0.5">
              <span className="size-0.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="size-0.5 rounded-full bg-teal-500" />
            </div>
          </div>
          <div className="w-16 h-2 rounded bg-zinc-900/90 border border-teal-900/20 flex items-center justify-between px-1.5">
            <div className="w-4 h-0.5 rounded bg-teal-500/10" />
            <div className="flex gap-0.5">
              <span className="size-0.5 rounded-full bg-teal-400 animate-pulse" />
              <span className="size-0.5 rounded-full bg-teal-500" />
            </div>
          </div>
          <ShieldCheck className="absolute bottom-1 right-2 size-5 text-teal-400/5" />
        </div>
        <span className="relative z-10">支持企业级私有化与局域网部署，保障科研核心机密，确保您的专有化学结构库与实验配方资产 100% 局域网内安全流转。</span>
      </div>
    ),
  },
];

export function WhatsNewSection({ className }: { className?: string }) {
  return (
    <Section
      className={cn("relative overflow-hidden", className)}
      title="GVIM AI 核心特性"
      subtitle="GVIM AI 将深度科研推理、领域工作流与全栈智能体执行完美融合于统一工作台"
    >
      {/* Background ambient light */}
      <div className="absolute top-[20%] left-1/2 -translate-x-1/2 w-[550px] h-[550px] rounded-full bg-blue-500/[0.03] blur-[150px] pointer-events-none" />

      <div className="flex w-full items-center justify-center mt-12 [&_.magic-bento-card]:bg-zinc-950/45 [&_.magic-bento-card]:backdrop-blur-2xl [&_.magic-bento-card]:border-zinc-900/60 [&_.magic-bento-card]:hover:border-blue-500/25 [&_.magic-bento-card]:transition-all [&_.magic-bento-card]:duration-500 [&_.magic-bento-card]:hover:shadow-[0_0_25px_rgba(59,130,246,0.12)]">
        <MagicBento
          data={features}
          enableStars={true}
          particleCount={16}
          glowColor="59, 130, 246"
          spotlightRadius={350}
        />
      </div>
    </Section>
  );
}
