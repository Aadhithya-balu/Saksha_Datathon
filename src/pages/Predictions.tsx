import React from 'react';
import ForecastChart from '../components/charts/ForecastChart';
import CorrelationChart from '../components/charts/CorrelationChart';
import WeatherCorrelationChart from '../components/charts/WeatherCorrelationChart';
import { Cpu, RefreshCw, BarChart2, ShieldAlert, Sparkles, TrendingUp } from 'lucide-react';

export const Predictions: React.FC = () => {
  return (
    <div className="flex flex-col gap-6 p-1 md:p-3 select-none bg-[#060b13]">
      
      {/* Title Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-white/5 pb-3">
        <div>
          <h2 className="text-md font-mono font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Cpu className="w-5 h-5 text-[#0E9E78] animate-pulse" />
            AI Crime Predictive Intelligence
          </h2>
          <p className="text-[9.5px] font-mono text-[#6A7A96] mt-0.5">
            D3 REGRESSION SCATTER MODELS — AUTO-PREDICTOR LSTM TIMELINES SENSING ANOMALIES
          </p>
        </div>

        <button
          onClick={() => {
            alert('Re-triggering model fit logs: 20 epochs training complete (current error rate: 0.043 RMSE)');
          }}
          className="px-2.5 py-1.5 bg-[#0E9E78]/10 hover:bg-[#0E9E78]/20 border border-[#0e9e78]/30 text-[#0E9E78] font-mono text-[9px] uppercase rounded-btn transition-colors cursor-pointer flex items-center gap-1.5"
        >
          <RefreshCw className="w-3 h-3 animate-spin" />
          Retrain Model Net
        </button>
      </div>

      {/* DOUBLE GRAPH GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <ForecastChart />
        <CorrelationChart />
      </div>

      {/* WEATHER & SEASONAL CORRELATION */}
      <div className="w-full">
        <WeatherCorrelationChart />
      </div>

      {/* DETAILED STATS ROW */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Side: Insight Bullet cards (8 cols on lg) */}
        <div className="lg:col-span-8 bg-secondary-bg/25 border border-border-color p-5 rounded-card flex flex-col gap-4">
          <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest block border-b border-white/5 pb-2">
            Strategic Threat Assessments
          </span>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
            {/* Intel item 1 */}
            <div className="p-3.5 bg-slate-950/45 border border-slate-900 rounded-btn flex gap-3 relative overflow-hidden">
              <ShieldAlert className="w-5 h-5 text-[#C94A2A] shrink-0" />
              <div>
                <span className="text-[#E8EDF5] font-bold uppercase text-[10.5px]">Weekend Night Patrol Surge</span>
                <p className="text-[10px] text-[#A8B4CC] leading-relaxed mt-1">
                  Predictive matrices indicate a 35% crime volume spike in South Bengaluru on Fridays 22:00-02:00. Recommend doubling sector patrols.
                </p>
              </div>
            </div>

            {/* Intel item 2 */}
            <div className="p-3.5 bg-slate-950/45 border border-slate-900 rounded-btn flex gap-3 relative overflow-hidden">
              <Sparkles className="w-5 h-5 text-[#0E9E78] shrink-0" />
              <div>
                <span className="text-[#E8EDF5] font-bold uppercase text-[10.5px]">Cyber-Fraud Phishing Warnings</span>
                <p className="text-[10px] text-[#A8B4CC] leading-relaxed mt-1">
                  Unemployment correlations show high correlation to online financial scams in northern districts (Kalaburagi and Ballari sectors).
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side: Performance stats (4 cols on lg) */}
        <div className="lg:col-span-4 bg-secondary-bg/25 border border-border-color p-5 rounded-card flex flex-col justify-between">
          <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest block border-b border-white/5 pb-2 select-none">
            Predictive Model Metrics
          </span>

          <div className="flex-1 flex flex-col justify-center gap-3.5 py-4 font-mono text-xs">
            <div className="flex justify-between items-center">
              <span className="text-[#6A7A96]">Algorithm Model</span>
              <span className="text-white font-bold">XGBoost-LSTM Stack</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[#6A7A96]">Root Mean Square Error</span>
              <span className="text-orange-400 font-bold">0.0432 RMSE</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[#6A7A96]">Verification Dataset</span>
              <span className="text-white font-bold">92.4k training rows</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[#6A7A96]">Last Epoch updates</span>
              <span className="text-[#0E9E78] font-bold font-semiboldScale">4 minutes ago</span>
            </div>
          </div>
        </div>
      </div>

    </div>
  );
};
export default Predictions;
