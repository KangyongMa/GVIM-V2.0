import { Footer } from "@/components/landing/footer";
import { Header } from "@/components/landing/header";
import { Hero } from "@/components/landing/hero";
import { CaseStudySection } from "@/components/landing/sections/case-study-section";
import { CommunitySection } from "@/components/landing/sections/community-section";
import { SandboxSection } from "@/components/landing/sections/sandbox-section";
import { ScientificPillarsSection } from "@/components/landing/sections/scientific-pillars-section";
import { WhatsNewSection } from "@/components/landing/sections/whats-new-section";

export default function LandingPage() {
  return (
    <div className="min-h-screen w-full bg-[#030508] text-zinc-100 overflow-x-hidden relative">
      {/* Ambient glowing energy bands representing micro orbitals */}
      <div className="absolute top-[10%] left-1/4 w-[500px] h-[500px] rounded-full bg-emerald-500/5 blur-[160px] pointer-events-none" />
      <div className="absolute top-[35%] right-1/4 w-[600px] h-[600px] rounded-full bg-cyan-500/5 blur-[180px] pointer-events-none" />
      <div className="absolute top-[65%] left-1/3 w-[550px] h-[550px] rounded-full bg-indigo-500/5 blur-[170px] pointer-events-none" />

      <Header />
      <main className="flex w-full flex-col relative z-10">
        <Hero />
        <ScientificPillarsSection />
        <CaseStudySection />
        <SandboxSection />
        <WhatsNewSection />
        <CommunitySection />
      </main>
      <Footer />
    </div>
  );
}
