"use client";

import { useState } from "react";
import { Beaker, Layers, Cpu, Check, Activity, BarChart2, Zap } from "lucide-react";

interface Pillar {
  id: string;
  icon: any;
  label: string;
  title: string;
  subtitle: string;
  skills: string[];
  features: string[];
  metrics: { label: string; value: string }[];
  visualCode: string;
}

export function ScientificPillarsSection() {
  const [activeTab, setActiveTab] = useState<string>("compchem");

  const pillars: Pillar[] = [
    {
      id: "compchem",
      icon: Beaker,
      label: "计算化学 (DFT & MD)",
      title: "密度泛函理论与分子动力学",
      subtitle: "自动化执行原子级模拟、几何结构优化及第一性原理量子计算，降低计算门槛。",
      skills: ["pymatgen", "materials-core", "molecular-dynamics", "geometry-optimizer"],
      features: [
        "通过 Pymatgen 自动化构建晶体单胞与执行几何结构优化。",
        "自动解析分子动力学模拟中的分子轨迹数据。",
        "从 PDF 报告或文献中精准提取 DFT 计算参数与元数据。",
        "支持交互式的 3D 晶胞渲染及自定义原子序号映射。"
      ],
      metrics: [
        { label: "DFT参数提取准确率", value: "98.4%" },
        { label: "原子坐标映射", value: "毫秒级实时" }
      ],
      visualCode: `import pymatgen.core as pmg
from pymatgen.analysis.structure_matcher import StructureMatcher

# Initialize crystal unit cell structure
lattice = pmg.Lattice.cubic(4.15)
structure = pmg.Structure(lattice, ["Cs", "Pb", "I"], 
                          [[0,0,0], [0.5,0.5,0.5], [0.5,0.5,0]])

# Match and optimize atomic coordinates
matcher = StructureMatcher(ltol=0.2, stol=0.3, angle_tol=5)
print(f"Space Group: {structure.get_space_group_info()}")`
    },
    {
      id: "characterization",
      icon: Layers,
      label: "光谱与表征解析",
      title: "自动化谱图拟合与物相匹配",
      subtitle: "高保真地生成、匹配和预测多维光谱 (XRD, NMR, Raman, UV-Vis, MS)。",
      skills: ["xrd-spectra-simulation", "nmr-prediction", "ir-spectra-simulation", "ms-spectra-simulation", "uv-vis-spectrum-simulation"],
      features: [
        "X射线衍射 (XRD) 峰位匹配及粉末晶体物相指标化。",
        "高精度一维/二维核磁共振 (NMR) 预测，助力有机化学结构确证。",
        "利用 MatchMS 进行质谱碎片模拟及相似度匹配分析。",
        "分子振动动力学特征与红外 (IR) 光谱模拟。"
      ],
      metrics: [
        { label: "XRD 物相匹配率", value: "95.7%" },
        { label: "NMR 谱图预测速度", value: "< 2.5s" }
      ],
      visualCode: `# Load raw experimental XRD intensity peaks
import numpy as np
from scipy.signal import find_peaks

xrd_data = np.loadtxt("experimental_xrd.txt")
peaks, _ = find_peaks(xrd_data[:, 1], distance=20, prominence=0.05)

# Simulate theoretical XRD matching using core skills
simulated_peaks = simulate_xrd_pattern(cif_filepath="perovskite.cif")
match_score = calculate_similarity(peaks, simulated_peaks)
print(f"XRD Match Index: {match_score:.2%}")`
    },
    {
      id: "synthesis",
      icon: Cpu,
      label: "合成与虚拟筛选",
      title: "AI 逆合成与 ADMET 高通量筛选",
      subtitle: "精准回溯小分子抑制剂的合成路径，并开展高通量 ADMET 药代动力学评估。",
      skills: ["adme-prediction", "pka-predictor", "chemistry-structure-resolution", "opentrons-integration", "pylabrobot"],
      features: [
        "基于逆合成分析，规划具备经济可行性的多步有机合成路线。",
        "高通量虚拟筛选分子的吸收、分布、代谢、排泄及毒性 (ADMET) 属性。",
        "精确预测分子 pKa 值及相关热力学常数。",
        "自动生成 Opentrons 移液机器人控制脚本，实现实验自动化。"
      ],
      metrics: [
        { label: "逆合成推导深度", value: "多达 8 步" },
        { label: "ADMET 筛选通量", value: "10,000+/分钟" }
      ],
      visualCode: `from rdkit import Chem
from rdkit.Chem import Descriptors

# Load drug candidate SMILES
smiles = "CC(=O)Oc1ccccc1C(=O)O"
mol = Chem.MolFromSmiles(smiles)

# High-throughput virtual screening of descriptors
mw = Descriptors.MolWt(mol)
logp = Descriptors.MolLogP(mol)
hbd = Descriptors.NumHAcceptors(mol)

print(f"MW: {mw:.2f} | LogP: {logp:.2f} | Lipinski HBD: {hbd}")`
    }
  ];

  const activePillar = pillars.find((p) => p.id === activeTab) ?? pillars[0]!;

  return (
    <section className="container-md mx-auto w-full px-4 py-20 relative z-10 md:px-20">
      <div className="flex flex-col items-center text-center space-y-4">
        <span className="rounded-full bg-blue-950/40 border border-blue-900/50 px-4 py-1 text-xs font-bold text-blue-400 uppercase tracking-wider">
          领域核心能力
        </span>
        <h2 className="text-4xl font-bold tracking-tight text-white md:text-5xl">
          GVIM 科学智能三大支柱
        </h2>
        <p className="text-lg text-zinc-400 max-w-3xl">
          GVIM AI 预置 130+ 严谨的科学技能，专为应对化学与材料科学前沿研究中的核心痛点而生，重塑科研范式。
        </p>
      </div>

      {/* Tabs Selector */}
      <div className="mt-12 flex flex-wrap justify-center gap-3">
        {pillars.map((pillar) => {
          const TabIcon = pillar.icon;
          return (
            <button
              key={pillar.id}
              onClick={() => setActiveTab(pillar.id)}
              className={`flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold border transition-all duration-300 ${
                activeTab === pillar.id
                  ? "bg-gradient-to-r from-blue-500/20 to-teal-500/20 text-blue-400 border-blue-500/40 shadow-[0_0_15px_rgba(59,130,246,0.15)]"
                  : "bg-zinc-950/40 text-zinc-400 border-zinc-900/80 hover:text-zinc-200 hover:border-zinc-800"
              }`}
            >
              <TabIcon className="size-4" />
              {pillar.label}
            </button>
          );
        })}
      </div>

      {/* Interactive Showcase Block */}
      <div className="mt-8 grid grid-cols-1 gap-8 rounded-3xl border border-zinc-900 bg-zinc-950/30 p-6 backdrop-blur-xl lg:grid-cols-12 lg:p-8">
        {/* Left Info HUD */}
        <div className="flex flex-col justify-between space-y-6 lg:col-span-5">
          <div className="space-y-4">
            <h3 className="text-2xl font-bold text-white md:text-3xl leading-[1.25]">
              {activePillar.title}
            </h3>
            <p className="text-zinc-400 text-sm leading-[1.6]">
              {activePillar.subtitle}
            </p>

            {/* List of features */}
            <div className="space-y-2 pt-2">
              {activePillar.features.map((feature, idx) => (
                <div key={idx} className="flex items-start gap-2.5 text-xs text-zinc-300">
                  <div className="mt-0.5 rounded-full bg-emerald-950/60 p-0.5 text-emerald-400 border border-emerald-900/40">
                    <Check className="size-3" />
                  </div>
                  <span className="leading-[1.5]">{feature}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Real precompiled Skills tag list */}
          <div className="space-y-3 pt-4 border-t border-zinc-900">
            <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest block">
              底层调用技能引擎
            </span>
            <div className="flex flex-wrap gap-2">
              {activePillar.skills.map((skill) => (
                <span
                  key={skill}
                  className="rounded-md bg-black/40 border border-zinc-900 px-2.5 py-1 text-[11px] font-mono text-cyan-400"
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Right Code Sandbox Mockup */}
        <div className="relative rounded-2xl border border-zinc-900 bg-[#04060a] p-4 lg:col-span-7 overflow-hidden shadow-2xl flex flex-col justify-between min-h-[360px]">
          {/* Top terminal tab header */}
          <div className="flex items-center justify-between pb-3 border-b border-zinc-900">
            <div className="flex items-center gap-1.5">
              <span className="size-3 rounded-full bg-red-500/70" />
              <span className="size-3 rounded-full bg-yellow-500/70" />
              <span className="size-3 rounded-full bg-green-500/70" />
              <span className="ml-2 text-[10px] font-mono text-zinc-500">gvim_science_agent.py</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-blue-500/10 border border-blue-500/20 px-2.5 py-0.5 text-[9px] font-bold text-blue-400 font-mono tracking-wider flex items-center gap-1">
                <Activity className="size-2.5 animate-pulse" />
                虚拟沙盒执行
              </span>
            </div>
          </div>

          {/* Syntax highlighted code block */}
          <div className="flex-1 pt-4 text-xs font-mono text-zinc-300 overflow-x-auto whitespace-pre leading-[1.6]">
            {activePillar.visualCode}
          </div>

          {/* Bottom telemetry block */}
          <div className="mt-4 pt-3 border-t border-zinc-900 flex items-center justify-between text-[11px] font-mono text-zinc-500">
            <div className="flex gap-4">
              {activePillar.metrics.map((metric, idx) => (
                <span key={idx}>
                  {metric.label}: <span className="text-emerald-400 font-semibold">{metric.value}</span>
                </span>
              ))}
            </div>
            <div className="text-[10px] text-zinc-600">
              Agent Framework v2.0
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
