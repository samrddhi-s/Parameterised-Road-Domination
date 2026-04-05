import { LucideIcon } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  delay?: number;
}

const MetricCard = ({ label, value, icon: Icon, delay = 0 }: MetricCardProps) => (
  <div
    className="glass-card p-6 group hover:border-primary/30 transition-all duration-300 hover:-translate-y-1 animate-fade-up"
    style={{ animationDelay: `${delay}ms` }}
  >
    <div className="flex items-center justify-between mb-3">
      <span className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
        {label}
      </span>
      <Icon className="w-4 h-4 text-primary/60 group-hover:text-primary transition-colors" />
    </div>
    <p className="text-3xl font-bold text-foreground tracking-tight">{value}</p>
  </div>
);

export default MetricCard;
