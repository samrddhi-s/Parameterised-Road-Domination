import { Network, GitBranch, Cpu, Target } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import MetricCard from "./MetricCard";
import type { PipelineResult } from "@/lib/api";

interface ResultsDashboardProps {
  data: PipelineResult;
}

const ResultsDashboard = ({ data }: ResultsDashboardProps) => (
  <div className="space-y-8 animate-fade-in">
    {/* Metrics Grid */}
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <MetricCard label="Graph Nodes" value={data.nodes.toLocaleString()} icon={Network} delay={0} />
      <MetricCard label="Network Edges" value={data.edges.toLocaleString()} icon={GitBranch} delay={100} />
      <MetricCard label="Modulator Set" value={data.modulator_size.toString()} icon={Cpu} delay={200} />
      <MetricCard label="Optimum TDS" value={data.tds_size.toString()} icon={Target} delay={300} />
    </div>

    {/* Visualization Tabs */}
    <div className="glass-card overflow-hidden">
      <Tabs defaultValue="modulator">
        <div className="border-b border-border/50 px-6 pt-4">
          <TabsList className="bg-transparent p-0 h-auto gap-0">
            <TabsTrigger
              value="modulator"
              className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:text-primary bg-transparent px-5 pb-3 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              Focus Mode: Modulator
            </TabsTrigger>
            <TabsTrigger
              value="tds"
              className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:text-primary bg-transparent px-5 pb-3 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              Vector Simulation: TDS
            </TabsTrigger>
            <TabsTrigger
              value="satellite"
              className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:text-primary bg-transparent px-5 pb-3 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              Spatio-Semantic Satellite
            </TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="modulator" className="p-0 m-0">
          {data.img_modulator ? (
            <img src={`data:image/png;base64,${data.img_modulator}`} alt="Modulator visualization" className="w-full h-auto" />
          ) : (
            <div className="flex items-center justify-center py-16 text-muted-foreground text-sm">
              No modulator visualization available
            </div>
          )}
        </TabsContent>
        <TabsContent value="tds" className="p-0 m-0">
          {data.img_tds ? (
            <img src={`data:image/png;base64,${data.img_tds}`} alt="TDS visualization" className="w-full h-auto" />
          ) : (
            <div className="flex items-center justify-center py-16 text-muted-foreground text-sm">
              No TDS visualization available
            </div>
          )}
        </TabsContent>
        <TabsContent value="satellite" className="p-0 m-0">
          {data.img_satellite ? (
            <img src={`data:image/png;base64,${data.img_satellite}`} alt="Satellite visualization" className="w-full h-auto" />
          ) : (
            <div className="flex items-center justify-center py-16 text-muted-foreground text-sm">
              Satellite view requires Point or BBox mode with contextily installed on the server
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  </div>
);

export default ResultsDashboard;
