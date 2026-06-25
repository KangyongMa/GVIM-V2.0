"use client";

import { useEffect, useRef } from "react";

interface Node {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  color: string;
}

export default function MolecularCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mouseRef = useRef({ x: 0, y: 0, active: false });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    // Color definitions
    const colors = [
      "rgba(16, 185, 129, 0.4)", // emerald
      "rgba(6, 182, 212, 0.4)",  // cyan
      "rgba(99, 102, 241, 0.3)",  // indigo
    ];

    // Generate floating atoms (nodes)
    const nodeCount = Math.min(Math.floor((width * height) / 12000), 120);
    const nodes: Node[] = [];

    for (let i = 0; i < nodeCount; i++) {
      nodes.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.4, // slow drift
        vy: (Math.random() - 0.5) * 0.4,
        radius: Math.random() * 3 + 2,
        color: colors[Math.floor(Math.random() * colors.length)] ?? "rgba(16, 185, 129, 0.4)",
      });
    }

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current.x = e.clientX;
      mouseRef.current.y = e.clientY;
      mouseRef.current.active = true;
    };

    const handleMouseLeave = () => {
      mouseRef.current.active = false;
    };

    window.addEventListener("resize", handleResize);
    window.addEventListener("mousemove", handleMouseMove);
    canvas.addEventListener("mouseleave", handleMouseLeave);

    const animate = () => {
      ctx.clearRect(0, 0, width, height);

      // 1. Draw connections (bonds)
      for (let i = 0; i < nodes.length; i++) {
        const nodeI = nodes[i];
        if (!nodeI) continue;

        for (let j = i + 1; j < nodes.length; j++) {
          const nodeJ = nodes[j];
          if (!nodeJ) continue;

          const dx = nodeI.x - nodeJ.x;
          const dy = nodeI.y - nodeJ.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          // Draw bond line if nodes are close enough
          const maxDist = 120;
          if (dist < maxDist) {
            const alpha = (1 - dist / maxDist) * 0.15;
            ctx.beginPath();
            ctx.moveTo(nodeI.x, nodeI.y);
            ctx.lineTo(nodeJ.x, nodeJ.y);
            ctx.strokeStyle = `rgba(6, 182, 212, ${alpha})`;
            ctx.lineWidth = 1;
            ctx.stroke();
          }
        }

        // Draw connection to mouse if active
        if (mouseRef.current.active) {
          const dx = nodeI.x - mouseRef.current.x;
          const dy = nodeI.y - mouseRef.current.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const maxMouseDist = 180;

          if (dist < maxMouseDist) {
            const alpha = (1 - dist / maxMouseDist) * 0.25;
            ctx.beginPath();
            ctx.moveTo(nodeI.x, nodeI.y);
            ctx.lineTo(mouseRef.current.x, mouseRef.current.y);
            ctx.strokeStyle = `rgba(16, 185, 129, ${alpha})`;
            ctx.lineWidth = 1.2;
            ctx.stroke();
          }
        }
      }

      // 2. Update and draw nodes (atoms)
      nodes.forEach((node) => {
        // Apply slight mouse avoidance
        if (mouseRef.current.active) {
          const dx = node.x - mouseRef.current.x;
          const dy = node.y - mouseRef.current.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 150) {
            const force = (150 - dist) / 150;
            node.vx += (dx / dist) * force * 0.02;
            node.vy += (dy / dist) * force * 0.02;
          }
        }

        // Speed limit
        const speedLimit = 0.8;
        const speed = Math.sqrt(node.vx * node.vx + node.vy * node.vy);
        if (speed > speedLimit) {
          node.vx = (node.vx / speed) * speedLimit;
          node.vy = (node.vy / speed) * speedLimit;
        }

        // Move
        node.x += node.vx;
        node.y += node.vy;

        // Bounce off bounds
        if (node.x < 0 || node.x > width) node.vx *= -1;
        if (node.y < 0 || node.y > height) node.vy *= -1;

        // Draw atom glow
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius + 3, 0, Math.PI * 2);
        const glowColor = node.color.replace("0.4", "0.08");
        ctx.fillStyle = glowColor;
        ctx.fill();

        // Draw atom center
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.fillStyle = node.color;
        ctx.fill();
      });

      animationId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("mousemove", handleMouseMove);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 size-full pointer-events-none z-0"
      style={{ opacity: 0.8 }}
    />
  );
}
