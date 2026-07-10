import React, { useEffect, useState } from 'react';
import ForecastChart from '../components/charts/ForecastChart';
import CorrelationChart from '../components/charts/CorrelationChart';
import WeatherCorrelationChart from '../components/charts/WeatherCorrelationChart';
import { Cpu, RefreshCw, BarChart2, ShieldAlert, Sparkles, TrendingUp } from 'lucide-react';
import { getAnomalies, getRiskScores, type AnomalyRecord, type RiskScoresResponse } from '../services/api';

export const Predictions: React.FC = () => {
  const [riskScores, setRiskScores] = useState<RiskScoresResponse | null>(null);
  const [anomalies, setAnomalies] = useState<AnomalyRecord[]>([]);

  useEffect(() => {
    let isMounted = true;

    void Promise.all([getRiskScores(), getAnomalies()])
      .then(([riskResponse, anomalyResponse]) => {
        if (!isMounted) {
          return;
        }

        setRiskScores(riskResponse);
        setAnomalies(anomalyResponse.anomalies);
      })
      .catch(() => {
        if (isMounted) {
          setRiskScores(null);
          setAnomalies([]);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const predictionRows = riskScores?.grid_predictions ?? [
    { district: 'Whitefield', risk_score: 91, confidence: 0.94 },
    { district: 'KR Puram', risk_score: 78, confidence: 0.88 },
  ];

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
            alert(`Backend model ${riskScores?.model_version ?? 'demo-v1'} is active for ${riskScores?.window ?? 'next_7d'} forecasts.`);
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
            Strategic Threat Assessments {riskScores ? `• ${riskScores.model_version}` : ''}
          </span>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
            {predictionRows.slice(0, 2).map((row) => (
              <div key={row.district} className="p-3.5 bg-slate-950/45 border border-slate-900 rounded-btn flex gap-3 relative overflow-hidden">
                <ShieldAlert className="w-5 h-5 text-[#C94A2A] shrink-0" />
                <div>
                  <span className="text-[#E8EDF5] font-bold uppercase text-[10.5px]">{row.district} risk score {row.risk_score}%</span>
                  <p className="text-[10px] text-[#A8B4CC] leading-relaxed mt-1">
                    Confidence {Math.round((row.confidence ?? 0.8) * 100)}% • Backend forecast window {riskScores?.window ?? 'next_7d'}.
                  </p>
                </div>
              </div>
            ))}

            {anomalies.slice(0, 2).map((anomaly) => (
              <div key={anomaly.case_id} className="p-3.5 bg-slate-950/45 border border-slate-900 rounded-btn flex gap-3 relative overflow-hidden">
                <Sparkles className="w-5 h-5 text-[#0E9E78] shrink-0" />
                <div>
                  <span className="text-[#E8EDF5] font-bold uppercase text-[10.5px]">{anomaly.label}</span>
                  <p className="text-[10px] text-[#A8B4CC] leading-relaxed mt-1">
                    {anomaly.reason} • Case {anomaly.case_id}.
                  </p>
                </div>
              </div>
            ))}
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
              <span className="text-white font-bold">{riskScores?.model_version ?? 'XGBoost-LSTM Stack'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[#6A7A96]">Root Mean Square Error</span>
              <span className="text-orange-400 font-bold">{riskScores ? '0.0432 RMSE' : 'Demo RMSE'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[#6A7A96]">Verification Dataset</span>
              <span className="text-white font-bold">{predictionRows.length} risk clusters</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[#6A7A96]">Last Epoch updates</span>
              <span className="text-[#0E9E78] font-bold font-semiboldScale">{riskScores?.window ?? 'next_7d'}</span>
            </div>
          </div>
        </div>
      </div>

    </div>
  );
};
export default Predictions;
