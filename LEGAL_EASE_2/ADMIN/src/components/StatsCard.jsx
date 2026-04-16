export default function StatsCard({ title, value, subtitle, icon: Icon, color = 'text-[#0071e3]' }) {
  return (
    <div className="card group hover:shadow-apple-md transition-all duration-300">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[11px] font-medium text-[#86868b] uppercase tracking-widest">{title}</p>
          <p className={`text-2xl font-bold mt-1 tracking-tight ${color}`}>{value}</p>
          {subtitle && <p className="text-xs text-[#86868b] mt-0.5">{subtitle}</p>}
        </div>
        {Icon && (
          <div className="w-10 h-10 rounded-2xl bg-[#f5f5f7] flex items-center justify-center group-hover:scale-110 transition-transform">
            <Icon className={`w-5 h-5 ${color}`} />
          </div>
        )}
      </div>
    </div>
  );
}
