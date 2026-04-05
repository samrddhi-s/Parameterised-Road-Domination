import { Network, GitBranch, Cpu, Target } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import MetricCard from "./MetricCard";
import modulatorImg from "@/assets/modulator-preview.jpg";
import tdsImg from "@/assets/tds-preview.jpg";
import satelliteImg from "@/assets/satellite-preview.jpg";

interface ResultsData {
  nodes: number;
  edges: number;
  modulatorSize: number;
  tdsSize: number;
}

interface ResultsDashboardProps {
  data: ResultsData;
}

const ResultsDashboard = ({ data }: ResultsDashboardProps) => (
  <div className="space-y-8 animate-fade-in">
    {/* Metrics Grid */}
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <MetricCard label="Graph Nodes" value={data.nodes.toLocaleString()} icon={Network} delay={0} />
      <MetricCard label="Network Edges" value={data.edges.toLocaleString()} icon={GitBranch} delay={100} />
      <MetricCard label="Modulator Set" value={data.modulatorSize.toString()} icon={Cpu} delay={200} />
      <MetricCard label="Optimum TDS" value={data.tdsSize.toString()} icon={Target} delay={300} />
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
          <img src={modulatorImg} alt="Modulator visualization" className="w-full h-auto" loading="lazy" width={1200} height={800} />
        </TabsContent>
        <TabsContent value="tds" className="p-0 m-0">
          <img src={tdsImg} alt="TDS visualization" className="w-full h-auto" loading="lazy" width={1200} height={800} />
        </TabsContent>
        <TabsContent value="satellite" className="p-0 m-0">
          <img src={satelliteImg} alt="Satellite visualization" className="w-full h-auto" loading="lazy" width={1200} height={800} />
        </TabsContent>
      </Tabs>
    </div>
  </div>
);

export default ResultsDashboard;
