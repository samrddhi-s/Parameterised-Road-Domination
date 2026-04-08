import { useState } from "react";
import { toast } from "sonner";
import heroImg from "@/assets/hero-network.jpg";
import InputPanel, { PipelineConfig } from "@/components/InputPanel";
import ResultsDashboard from "@/components/ResultsDashboard";
import { runPipeline, PipelineResult } from "@/lib/api";

const Index = () => {
  const [results, setResults] = useState<PipelineResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const handleRun = async (config: PipelineConfig) => {
    setIsRunning(true);
    setResults(null);

    try {
      const data = await runPipeline(config);
      setResults(data);
      toast.success(`Pipeline complete — ${data.ds_type} size: ${data.ds_size}`);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Pipeline failed";
      toast.error(message);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="min-h-screen bg-background relative">
      {/* Subtle radial glow background */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse 80% 50% at 80% 0%, hsl(190 100% 50% / 0.06) 0%, transparent 60%), radial-gradient(ellipse 60% 40% at 10% 100%, hsl(220 80% 50% / 0.04) 0%, transparent 50%)",
        }}
      />

      <div className="relative z-10 flex min-h-screen">
        {/* Sidebar */}
        <aside className="w-[340px] min-h-screen border-r border-border/50 bg-card/30 backdrop-blur-sm p-6 overflow-y-auto shrink-0 hidden lg:block">
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-lg">🗺️</span>
              <h2 className="text-sm font-bold uppercase tracking-widest text-primary">
                TDS Pipeline
              </h2>
            </div>
            <p className="text-xs text-muted-foreground">
              Configure & execute graph analysis
            </p>
          </div>
          <InputPanel onRun={handleRun} isRunning={isRunning} />
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto">
          {/* Hero Section */}
          <div className="relative h-[280px] overflow-hidden">
            <img
              src={heroImg}
              alt="Network visualization"
              className="absolute inset-0 w-full h-full object-cover opacity-40"
              width={1920}
              height={800}
            />
            <div className="absolute inset-0 bg-gradient-to-b from-background/30 via-background/60 to-background" />
            <div className="relative z-10 h-full flex flex-col justify-end px-8 pb-8">
              <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-gradient-hero mb-2">
                Minimum Total Dominating Set
              </h1>
              <p className="text-muted-foreground text-base max-w-xl">
                Optimize spatial road networks intelligently using block graph deletion modulators.
              </p>
            </div>
          </div>

          {/* Mobile Input Panel */}
          <div className="lg:hidden px-6 py-6">
            <InputPanel onRun={handleRun} isRunning={isRunning} />
          </div>

          {/* Results */}
          <div className="px-8 py-8">
            {isRunning && (
              <div className="flex flex-col items-center justify-center py-20 animate-fade-in">
                <div className="w-12 h-12 border-3 border-primary/20 border-t-primary rounded-full animate-spin mb-4" />
                <p className="text-sm text-muted-foreground">
                  Engine is processing the graph topology...
                </p>
              </div>
            )}

            {results && !isRunning && (
              <>
                <h2 className="text-lg font-semibold text-foreground mb-6 tracking-tight">
                  Dashboard Statistics
                </h2>
                <ResultsDashboard data={results} />
              </>
            )}

            {!results && !isRunning && (
              <div className="flex flex-col items-center justify-center py-24 text-center">
                <div className="w-16 h-16 rounded-full bg-secondary/50 flex items-center justify-center mb-4 animate-pulse-glow">
                  <span className="text-2xl">🗺️</span>
                </div>
                <h3 className="text-lg font-semibold text-foreground mb-2">
                  Ready to Analyze
                </h3>
                <p className="text-sm text-muted-foreground max-w-md">
                  Configure your target coordinates and parameters in the sidebar, then initialize the engine to compute the optimal Total Dominating Set.
                </p>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
};

export default Index;
