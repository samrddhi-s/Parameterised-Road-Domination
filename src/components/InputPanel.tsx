import { useState } from "react";
import { MapPin, Globe, Square, Settings2, Zap } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface InputPanelProps {
  onRun: (config: PipelineConfig) => void;
  isRunning: boolean;
}

export interface PipelineConfig {
  mode: string;
  lat: number;
  lon: number;
  place: string;
  bbox: { n: number; s: number; e: number; w: number };
  networkType: string;
  kModulator: number;
  maxNodes: number;
  radius: number;
}

const InputPanel = ({ onRun, isRunning }: InputPanelProps) => {
  const [mode, setMode] = useState("point");
  const [lat, setLat] = useState(13.0002);
  const [lon, setLon] = useState(80.2719);
  const [place, setPlace] = useState("Adyar, Chennai");
  const [bbox, setBbox] = useState({ n: 13.005, s: 12.995, e: 80.275, w: 80.265 });
  const [networkType, setNetworkType] = useState("drive");
  const [kModulator, setKModulator] = useState(10);
  const [maxNodes, setMaxNodes] = useState(100);
  const [radius, setRadius] = useState(200);

  const handleRun = () => {
    onRun({ mode, lat, lon, place, bbox, networkType, kModulator, maxNodes, radius });
  };

  return (
    <div className="space-y-6">
      {/* Location Mode */}
      <div className="glass-card p-5">
        <div className="flex items-center gap-2 mb-4">
          <MapPin className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-semibold uppercase tracking-wider text-foreground">
            Location Mode
          </h3>
        </div>
        <Tabs value={mode} onValueChange={setMode}>
          <TabsList className="w-full bg-secondary/50">
            <TabsTrigger value="point" className="flex-1 text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
              <MapPin className="w-3 h-3 mr-1" /> Point
            </TabsTrigger>
            <TabsTrigger value="place" className="flex-1 text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
              <Globe className="w-3 h-3 mr-1" /> Place
            </TabsTrigger>
            <TabsTrigger value="bbox" className="flex-1 text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
              <Square className="w-3 h-3 mr-1" /> BBox
            </TabsTrigger>
          </TabsList>

          <TabsContent value="point" className="mt-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs text-muted-foreground">Latitude</Label>
                <Input
                  type="number"
                  step="0.000001"
                  value={lat}
                  onChange={(e) => setLat(parseFloat(e.target.value))}
                  className="bg-secondary/50 border-border/50 text-foreground"
                />
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Longitude</Label>
                <Input
                  type="number"
                  step="0.000001"
                  value={lon}
                  onChange={(e) => setLon(parseFloat(e.target.value))}
                  className="bg-secondary/50 border-border/50 text-foreground"
                />
              </div>
            </div>
          </TabsContent>

          <TabsContent value="place" className="mt-4">
            <Label className="text-xs text-muted-foreground">Region</Label>
            <Input
              value={place}
              onChange={(e) => setPlace(e.target.value)}
              placeholder="E.g., Adyar, Chennai"
              className="bg-secondary/50 border-border/50 text-foreground"
            />
          </TabsContent>

          <TabsContent value="bbox" className="mt-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              {(["n", "s", "e", "w"] as const).map((k) => (
                <div key={k}>
                  <Label className="text-xs text-muted-foreground capitalize">
                    {k === "n" ? "North" : k === "s" ? "South" : k === "e" ? "East" : "West"}
                  </Label>
                  <Input
                    type="number"
                    step="0.000001"
                    value={bbox[k]}
                    onChange={(e) => setBbox({ ...bbox, [k]: parseFloat(e.target.value) })}
                    className="bg-secondary/50 border-border/50 text-foreground"
                  />
                </div>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* Advanced Parameters */}
      <div className="glass-card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Settings2 className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-semibold uppercase tracking-wider text-foreground">
            Parameters
          </h3>
        </div>
        <div className="space-y-4">
          <div>
            <Label className="text-xs text-muted-foreground">Network Topology</Label>
            <Select value={networkType} onValueChange={setNetworkType}>
              <SelectTrigger className="bg-secondary/50 border-border/50 text-foreground">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="drive">Drive</SelectItem>
                <SelectItem value="walk">Walk</SelectItem>
                <SelectItem value="bike">Bike</SelectItem>
                <SelectItem value="all">All</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <Label className="text-xs text-muted-foreground">Modulator Vector (k)</Label>
              <span className="text-xs font-mono text-primary">{kModulator}</span>
            </div>
            <Slider
              value={[kModulator]}
              onValueChange={([v]) => setKModulator(v)}
              min={1}
              max={20}
              step={1}
              className="[&_[role=slider]]:bg-primary [&_[role=slider]]:border-primary"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs text-muted-foreground">Max Nodes</Label>
              <Input
                type="number"
                value={maxNodes}
                onChange={(e) => setMaxNodes(parseInt(e.target.value))}
                className="bg-secondary/50 border-border/50 text-foreground"
              />
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Radius (m)</Label>
              <Input
                type="number"
                value={radius}
                onChange={(e) => setRadius(parseInt(e.target.value))}
                className="bg-secondary/50 border-border/50 text-foreground"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Run Button */}
      <Button
        onClick={handleRun}
        disabled={isRunning}
        className="w-full h-12 bg-primary text-primary-foreground font-semibold text-base tracking-wide hover:brightness-110 transition-all duration-200 glow-accent"
      >
        {isRunning ? (
          <span className="flex items-center gap-2">
            <span className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
            Processing...
          </span>
        ) : (
          <span className="flex items-center gap-2">
            <Zap className="w-4 h-4" />
            Initialize Engine
          </span>
        )}
      </Button>
    </div>
  );
};

export default InputPanel;
