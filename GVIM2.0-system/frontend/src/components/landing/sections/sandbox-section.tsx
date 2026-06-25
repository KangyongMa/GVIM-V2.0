"use client";

import {
  AnimatedSpan,
  Terminal,
  TypingAnimation,
} from "@/components/ui/terminal";

import InteractiveMoleculeViewer from "@/components/ui/interactive-molecule-viewer";
import { Section } from "../section";

export function SandboxSection({ className }: { className?: string }) {
  return (
    <Section
      className={className}
      title="全能科学沙盒环境"
      subtitle={
        <p>
          GVIM AI 内置基于 Docker 的安全沙盒，预装 RDKit、Pymatgen 等全套科学套件，能够安全地执行复杂的科学模拟与 Python 自动化工作流。
        </p>
      }
    >
      <div className="mt-8 flex w-full max-w-6xl flex-col items-center gap-12 lg:flex-row lg:gap-16">
        {/* Left: Terminal */}
        <div className="w-full flex-1">
          <Terminal className="h-[360px] w-full">
            {/* Scene 1: Scientific packages installation */}
            <TypingAnimation>$ cat requirements.txt</TypingAnimation>
            <AnimatedSpan delay={800} className="text-zinc-400">
              rdkit==2023.9.5
              <br />
              pymatgen==2024.2.20
            </AnimatedSpan>

            <TypingAnimation delay={1200}>
              $ pip install -r requirements.txt
            </TypingAnimation>
            <AnimatedSpan delay={2000} className="text-green-500">
              ✔ Installed rdkit, pymatgen successfully
            </AnimatedSpan>

            <TypingAnimation delay={2400}>
              $ write check_properties.py --lines 45
            </TypingAnimation>
            <AnimatedSpan delay={3200} className="text-blue-500">
              ✔ Written 45 lines of molecular property calculator using RDKit
            </AnimatedSpan>

            <TypingAnimation delay={3600}>
              $ python check_properties.py --smiles "CC(=O)Oc1ccccc1C(=O)O"
            </TypingAnimation>
            <AnimatedSpan delay={4200} className="text-green-500">
              ✔ Loaded Aspirin (C9H8O4)
            </AnimatedSpan>
            <AnimatedSpan delay={4500} className="text-green-500">
              ✔ MW: 180.16 g/mol | LogP: 1.21
            </AnimatedSpan>
            <AnimatedSpan delay={4800} className="text-green-500">
              ✔ Estimated pKa: 3.5
            </AnimatedSpan>

            {/* Scene 2: Pymatgen simulation */}
            <TypingAnimation delay={5400}>
              $ python optimize_cell.py --cif perovskite.cif
            </TypingAnimation>
            <AnimatedSpan delay={6200} className="text-zinc-400">
              ✔ Perovskite lattice optimized: Space group Pm-3m (No. 221)
            </AnimatedSpan>
          </Terminal>
        </div>

        {/* Right: Description */}
        <div className="w-full flex-1 space-y-6">
          <div className="space-y-4">
            <p className="text-sm font-medium tracking-wider text-blue-400 uppercase">
              隔离安全与全量预装
            </p>
            <h2 className="text-4xl font-bold tracking-tight lg:text-5xl">
              科学计算沙盒
            </h2>
          </div>

          <div className="space-y-4 text-lg text-zinc-400">
            <p>
              我们的容器化沙盒工作区开箱即用，预配置了完整的 RDKit、Pymatgen 等科学计算库与编译器。
              智能体可在沙盒中安全无忧地进行密度泛函计算、原始光谱曲线拟合、XRD 物相匹配，甚至执行自动化的移液工作站脚本，完全隔离对您本地系统的影响。
            </p>
          </div>

          {/* Feature Tags */}
          <div className="flex flex-wrap gap-3 pt-4">
            <span className="rounded-full border border-zinc-800 bg-zinc-900 px-4 py-2 text-sm text-zinc-300">
              隔离的 Docker 环境
            </span>
            <span className="rounded-full border border-zinc-800 bg-zinc-900 px-4 py-2 text-sm text-zinc-300">
              安全代码执行
            </span>
            <span className="rounded-full border border-zinc-800 bg-zinc-900 px-4 py-2 text-sm text-zinc-300">
              内嵌 RDKit
            </span>
            <span className="rounded-full border border-zinc-800 bg-zinc-900 px-4 py-2 text-sm text-zinc-300">
              开箱即用 Pymatgen
            </span>
            <span className="rounded-full border border-zinc-800 bg-zinc-900 px-4 py-2 text-sm text-zinc-300">
              持久化存储引擎
            </span>
          </div>
        </div>
      </div>

      {/* 3D Interactive Molecule Viewer Block */}
      <div className="mt-16 w-full max-w-6xl">
        <InteractiveMoleculeViewer />
      </div>
    </Section>
  );
}
