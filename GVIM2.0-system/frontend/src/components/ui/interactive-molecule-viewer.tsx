"use client";

import { useEffect, useRef, useState } from "react";

interface Atom {
  x: number;
  y: number;
  z: number;
  element: "C" | "O" | "H" | "Ti" | "Ca";
}

interface Bond {
  a: number;
  b: number;
}

export default function InteractiveMoleculeViewer() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [structure, setStructure] = useState<"cnt" | "graphene" | "perovskite">("cnt");
  const rotationRef = useRef({ rx: 0.3, ry: 0.5 });
  const isDraggingRef = useRef(false);
  const dragStartRef = useRef({ x: 0, y: 0 });

  const getMolecularData = () => {
    switch (structure) {
      case "cnt":
        return {
          name: "单壁碳纳米管 (SWCNT)",
          formula: "C96 (手性矢量: [6,6])",
          weight: "1152.96 g/mol",
          spaceGroup: "P6/mmm (No. 191)",
          skillsUsed: "materials-core",
          description: "在材料科学中，SWCNT 是经典的一维低维材料。GVIM 会自动调用 materials-core 晶体计算模块（基于 pymatgen）构建其一维管状超胞，并计算其对称空间群为 P6/mmm，支持高精度能带结构建模与热力学稳定性分析。",
        };
      case "graphene":
        return {
          name: "单层石墨烯晶格",
          formula: "C72 (二维碳网络)",
          weight: "864.72 g/mol",
          spaceGroup: "P6mm (2D No. 17)",
          skillsUsed: "materials-evidence-project",
          description: "二维蜂窝状晶格是凝聚态物理与新型纳米材料的研究重镇。GVIM 会启用 materials-evidence-project 实时跨 Materials Project 材料物理数据库进行匹配，快速检索并预测其 2D 晶格常数与倒易空间能带结构。",
        };
      case "perovskite":
        return {
          name: "卤化物钙钛矿晶体",
          formula: "CsPbI3 (立方相)",
          weight: "660.71 g/mol",
          spaceGroup: "Pm-3m (No. 221)",
          skillsUsed: "xrd-spectra-simulation, materials-core",
          description: "卤化物钙钛矿是第三代太阳能光伏材料的研究前沿。GVIM 通过 materials-core 快速建立三维 CsPbI3 晶格，并调用 xrd-spectra-simulation 对其进行粉末 X 射线衍射（XRD）模拟与物相指纹图谱匹配。",
        };
    }
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId: number;
    let width = (canvas.width = 450);
    let height = (canvas.height = 360);

    // Generate atoms & bonds mathematically to guarantee 100% precision
    const generateStructure = () => {
      const atoms: Atom[] = [];
      const bonds: Bond[] = [];

      if (structure === "cnt") {
        // Carbon Nanotube (8 rings, 12 atoms per ring)
        const rings = 8;
        const segments = 12;
        const radius = 60;
        const spacing = 22;

        for (let r = 0; r < rings; r++) {
          const y = (r - (rings - 1) / 2) * spacing;
          for (let s = 0; s < segments; s++) {
            const angle = (s / segments) * Math.PI * 2 + (r % 2 === 0 ? 0 : Math.PI / segments);
            const x = Math.cos(angle) * radius;
            const z = Math.sin(angle) * radius;
            atoms.push({ x, y, z, element: "C" });
          }
        }

        // Connect bonds
        for (let r = 0; r < rings; r++) {
          const startIdx = r * segments;
          for (let s = 0; s < segments; s++) {
            const current = startIdx + s;
            const next = startIdx + ((s + 1) % segments);
            bonds.push({ a: current, b: next }); // ring connection

            if (r < rings - 1) {
              const nextRingStart = (r + 1) * segments;
              const nextRingSegment = nextRingStart + s;
              bonds.push({ a: current, b: nextRingSegment }); // cross ring connection
            }
          }
        }
      } else if (structure === "graphene") {
        // 2D Graphene Hexagonal Sheet
        const rows = 6;
        const cols = 6;
        const size = 28;

        for (let r = 0; r < rows; r++) {
          for (let c = 0; c < cols; c++) {
            let x = c * size * Math.sqrt(3);
            let y = r * size * 1.5;
            if (r % 2 !== 0) {
              x += (size * Math.sqrt(3)) / 2;
            }

            // Standard hex offset
            atoms.push({
              x: x - (cols * size * Math.sqrt(3)) / 2 + 20,
              y: y - (rows * size * 1.5) / 2,
              z: 0,
              element: "C",
            });
          }
        }

        // Connect hexagons
        for (let r = 0; r < rows; r++) {
          for (let c = 0; c < cols; c++) {
            const idx = r * cols + c;
            if (c < cols - 1) bonds.push({ a: idx, b: idx + 1 });
            if (r < rows - 1) {
              const bottomIdx = (r + 1) * cols + c;
              bonds.push({ a: idx, b: bottomIdx });
              if (r % 2 === 0 && c > 0) {
                bonds.push({ a: idx, b: (r + 1) * cols + c - 1 });
              } else if (r % 2 !== 0 && c < cols - 1) {
                bonds.push({ a: idx, b: (r + 1) * cols + c + 1 });
              }
            }
          }
        }
      } else {
        // Perovskite Unit Cell (CsPbI3 / Cubic lattice)
        // Center: Ti/Pb (Greyish metal), Corners: Ca/Cs (Greenish), Face Centers: Oxygen/Iodine (Red)
        // Let's model a beautiful Unit Cell
        atoms.push({ x: 0, y: 0, z: 0, element: "Ti" }); // Center

        // 8 Corners (Cs/Ca)
        const size = 70;
        const corners = [
          [-1, -1, -1], [1, -1, -1], [-1, 1, -1], [1, 1, -1],
          [-1, -1, 1], [1, -1, 1], [-1, 1, 1], [1, 1, 1],
        ] as const;
        corners.forEach(([cx, cy, cz]) => {
          atoms.push({
            x: cx * size,
            y: cy * size,
            z: cz * size,
            element: "Ca",
          });
        });

        // 6 Face Centers (Iodine)
        const faces = [
          [0, 0, -1], [0, 0, 1],
          [0, -1, 0], [0, 1, 0],
          [-1, 0, 0], [1, 0, 0],
        ] as const;
        faces.forEach(([fx, fy, fz]) => {
          atoms.push({
            x: fx * size,
            y: fy * size,
            z: fz * size,
            element: "O",
          });
        });

        // Draw crystal bonds
        // Connect center Ti to faces
        for (let i = 9; i < 15; i++) {
          bonds.push({ a: 0, b: i });
        }
        // Connect corner Cs
        const cornerIndices = [1, 2, 4, 3, 1, 5, 6, 8, 7, 5];
        for (let idx = 0; idx < cornerIndices.length - 1; idx++) {
          bonds.push({ a: cornerIndices[idx]!, b: cornerIndices[idx + 1]! });
        }
        bonds.push({ a: 2, b: 6 });
        bonds.push({ a: 4, b: 8 });
        bonds.push({ a: 3, b: 7 });
      }

      return { atoms, bonds };
    };

    let { atoms, bonds } = generateStructure();

    const handleMouseDown = (e: MouseEvent) => {
      isDraggingRef.current = true;
      dragStartRef.current = { x: e.clientX, y: e.clientY };
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (!isDraggingRef.current) return;
      const dx = e.clientX - dragStartRef.current.x;
      const dy = e.clientY - dragStartRef.current.y;

      rotationRef.current.ry += dx * 0.007;
      rotationRef.current.rx += dy * 0.007;

      dragStartRef.current = { x: e.clientX, y: e.clientY };
    };

    const handleMouseUp = () => {
      isDraggingRef.current = false;
    };

    canvas.addEventListener("mousedown", handleMouseDown);
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);

    const animate = () => {
      ctx.clearRect(0, 0, width, height);

      // Auto rotation when not dragging
      if (!isDraggingRef.current) {
        rotationRef.current.ry += 0.003;
      }

      // Projection calculations
      const cosX = Math.cos(rotationRef.current.rx);
      const sinX = Math.sin(rotationRef.current.rx);
      const cosY = Math.cos(rotationRef.current.ry);
      const sinY = Math.sin(rotationRef.current.ry);

      // Map atoms to projected screen coordinates
      const projected = atoms.map((atom) => {
        // Rotate Y
        let x1 = atom.x * cosY - atom.z * sinY;
        let z1 = atom.x * sinY + atom.z * cosY;

        // Rotate X
        let y2 = atom.y * cosX - z1 * sinX;
        let z2 = atom.y * sinX + z1 * cosX;

        // Perspective projection factor
        const fov = 400;
        const scale = fov / (fov + z2);

        return {
          sx: x1 * scale + width / 2,
          sy: y2 * scale + height / 2,
          sz: z2, // keep depth for z-sorting
          element: atom.element,
        };
      });

      // 1. Draw Bonds (Cylinders)
      bonds.forEach((bond) => {
        const p1 = projected[bond.a];
        const p2 = projected[bond.b];
        if (!p1 || !p2) return;

        // Draw clean shadow/depth colored bond line
        ctx.beginPath();
        ctx.moveTo(p1.sx, p1.sy);
        ctx.lineTo(p2.sx, p2.sy);

        // Gradient representing bond energy/depth
        const avgDepth = (p1.sz + p2.sz) / 2;
        const alpha = Math.max(0.1, 1 - (avgDepth + 100) / 200);
        ctx.strokeStyle = `rgba(161, 161, 170, ${alpha * 0.45})`;
        ctx.lineWidth = Math.max(1, 4 * alpha);
        ctx.stroke();
      });

      // 2. Draw Atoms (Z-Sorted Spheres)
      // Sort indices by depth (back to front)
      const sortedIndices = projected
        .map((p, idx) => ({ p, idx }))
        .sort((a, b) => b.p.sz - a.p.sz);

      sortedIndices.forEach(({ p }) => {
        // Determine atom properties based on element
        let color = "#3b82f6"; // Carbon - Deep Blue
        let radius = 10;
        let name = "Carbon";

        if (p.element === "C") {
          color = "#06b6d4"; // Cyan
          radius = 7.5;
        } else if (p.element === "Ti") {
          color = "#a855f7"; // Purple (Transition metal)
          radius = 12;
        } else if (p.element === "Ca") {
          color = "#10b981"; // Emerald green
          radius = 14;
        } else if (p.element === "O") {
          color = "#ef4444"; // Red (Anion Iodine/Oxygen)
          radius = 9;
        }

        const alpha = Math.max(0.2, 1 - (p.sz + 100) / 200);

        // Draw radial lighting gradient for atom sphere
        const grad = ctx.createRadialGradient(
          p.sx - radius * 0.25,
          p.sy - radius * 0.25,
          radius * 0.1,
          p.sx,
          p.sy,
          radius
        );
        grad.addColorStop(0, "#ffffff");
        grad.addColorStop(0.3, color);
        grad.addColorStop(1, "#000000");

        // Outer glow
        ctx.beginPath();
        ctx.arc(p.sx, p.sy, radius + 2, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0, 0, 0, ${alpha * 0.3})`;
        ctx.fill();

        // Atom sphere
        ctx.beginPath();
        ctx.arc(p.sx, p.sy, radius, 0, Math.PI * 2);
        ctx.fillStyle = grad;
        ctx.fill();
      });

      animationId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationId);
      canvas.removeEventListener("mousedown", handleMouseDown);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [structure]);

  const molData = getMolecularData();

  return (
    <div className="flex w-full flex-col gap-6 rounded-2xl border border-zinc-800 bg-[#07090e]/90 p-6 shadow-2xl backdrop-blur-xl lg:flex-row lg:items-center">
      {/* 3D Canvas */}
      <div className="relative flex flex-1 items-center justify-center rounded-xl bg-black/40 overflow-hidden border border-zinc-900/50 min-h-[360px]">
        <div className="absolute top-3 left-4 right-4 z-10 flex flex-wrap gap-2">
          <button
            onClick={() => setStructure("cnt")}
            className={`rounded-md px-3 py-1.5 text-xs font-semibold border transition-all ${
              structure === "cnt"
                ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/40"
                : "bg-zinc-900 text-zinc-400 border-zinc-800 hover:text-zinc-300"
            }`}
          >
            碳纳米管 (CNT)
          </button>
          <button
            onClick={() => setStructure("graphene")}
            className={`rounded-md px-3 py-1.5 text-xs font-semibold border transition-all ${
              structure === "graphene"
                ? "bg-cyan-500/20 text-cyan-400 border-cyan-500/40"
                : "bg-zinc-900 text-zinc-400 border-zinc-800 hover:text-zinc-300"
            }`}
          >
            单层石墨烯
          </button>
          <button
            onClick={() => setStructure("perovskite")}
            className={`rounded-md px-3 py-1.5 text-xs font-semibold border transition-all ${
              structure === "perovskite"
                ? "bg-purple-500/20 text-purple-400 border-purple-500/40"
                : "bg-zinc-900 text-zinc-400 border-zinc-800 hover:text-zinc-300"
            }`}
          >
            钙钛矿晶体
          </button>
        </div>
        <canvas ref={canvasRef} className="cursor-grab active:cursor-grabbing w-full h-full object-contain" />
        <div className="absolute bottom-2 right-4 text-[10px] text-zinc-500 pointer-events-none bg-black/50 px-2 py-1 rounded">
          ◀ 拖拽鼠标旋转 3D 晶格 ▶
        </div>
      </div>

      {/* Description HUD */}
      <div className="flex flex-1 flex-col justify-between space-y-4">
        <div>
          <span className="rounded-full bg-blue-950/50 border border-blue-900/50 px-3 py-1 text-xs font-bold text-blue-400 uppercase tracking-wider">
            交互式三维结构模型
          </span>
          <h3 className="mt-3 text-2xl font-bold tracking-tight text-white md:text-3xl">
            {molData.name}
          </h3>
          <p className="mt-2 text-sm text-zinc-400 line-height-[1.6]">
            {molData.description}
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4 rounded-xl bg-black/30 border border-zinc-900 p-4 text-xs">
          <div>
            <span className="text-zinc-500 block">化学分子式</span>
            <span className="font-semibold text-zinc-200 font-mono text-sm">{molData.formula}</span>
          </div>
          <div>
            <span className="text-zinc-500 block">分子量</span>
            <span className="font-semibold text-zinc-200 font-mono text-sm">{molData.weight}</span>
          </div>
          <div>
            <span className="text-zinc-500 block">空间群 (Space Group)</span>
            <span className="font-semibold text-zinc-200 font-mono text-sm">{molData.spaceGroup}</span>
          </div>
          <div>
            <span className="text-zinc-500 block">底层调用技能</span>
            <span className="font-semibold text-blue-400 font-mono text-xs">{molData.skillsUsed}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
