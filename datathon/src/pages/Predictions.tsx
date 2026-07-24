import React, { useEffect, useState } from 'react';
import ForecastChart from '../components/charts/ForecastChart';
import CorrelationChart from '../components/charts/CorrelationChart';
import WeatherCorrelationChart from '../components/charts/WeatherCorrelationChart';
import { Cpu, RefreshCw, BarChart2, ShieldAlert, Sparkles, TrendingUp } from 'lucide-react';
import { getAnomalies, getRiskScores, getModelInfo, type AnomalyRecord, type RiskScoresResponse, type ModelInfo } from '../services/api';

export const Predictions: React.FC = () => {
  const [riskScores, setRiskScores] = useState<RiskScoresResponse | null>(null);
  const [anomalies, setAnomalies] = useState<AnomalyRecord[]>([]);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);

  useEffect(() => {
    let isMounted = true;

    void Promise.all([getRiskScores(), getAnomalies(), getModelInfo()])
      .then(([riskResponse, anomalyResponse, modelResponse]) => {
        if (!isMounted) {
          return;
        }

        setRiskScores(riskResponse);
        setAnomalies(anomalyResponse.anomalies);
        setModelInfo(modelResponse);
      })
      .catch(() => {
        if (isMounted) {
          setRiskScores(null);
          setAnomalies([]);
          setModelInfo(null);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const predictionRows = riskScores?.grid_predictions ?? [];

  return (
    <div className="flex flex-col gap-6 p-1 md:p-3 select-none bg-[var(--bg-primary)]">
      
      {/* Title Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-[var(--border-muted)] pb-3">
        <div>
          <h2 className="text-md font-mono font-bold text-[var(--text-primary)] uppercase tracking-wider flex items-center gap-2">
            <Cpu className="w-5 h-5 text-[#0E9E78] animate-pulse" />
            AI Crime Predictive Intelligence
          </h2>
          <p className="text-[9.5px] font-mono text-[var(--text-muted)] mt-0.5">
            D3 REGRESSION SCATTER MODELS â€” AUTO-PREDICTOR LSTM TIMELINES SENSING ANOMALIES
          </p>
        </div>

        <button
          onClick={() => {
            alert(`Backend model  is active for  forecasts.`);
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
          <span className="text-[10px] font-mono font-bold text-[var(--text-muted)] uppercase tracking-widest block border-b border-[var(--border-muted)] pb-2">
            Strategic Threat Assessments {modelInfo ? `• ${modelInfo.version}` : ''}
          </span>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
            {predictionRows.slice(0, 2).map((row) => (
              <div key={row.district} className="p-3.5 bg-[var(--bg-secondary)]/45 border border-[var(--border-primary)] rounded-btn flex gap-3 relative overflow-hidden">
                <ShieldAlert className="w-5 h-5 text-[#C94A2A] shrink-0" />
                <div>
                  <span className="text-[var(--text-primary)] font-bold uppercase text-[10.5px]">{row.district} risk score {row.risk_score}%</span>
                  <p className="text-[10px] text-[var(--text-secondary)] leading-relaxed mt-1">
                    Confidence {Math.round((row.confidence ?? 0.8) * 100)}% • Backend forecast window {riskScores?.window ?? 'No backend window'}.
                  </p>
                </div>
              </div>
            ))}

            {anomalies.slice(0, 2).map((anomaly) => (
              <div key={anomaly.case_id} className="p-3.5 bg-[var(--bg-secondary)]/45 border border-[var(--border-primary)] rounded-btn flex gap-3 relative overflow-hidden">
                <Sparkles className="w-5 h-5 text-[#0E9E78] shrink-0" />
                <div>
                  <span className="text-[var(--text-primary)] font-bold uppercase text-[10.5px]">{anomaly.label}</span>
                  <p className="text-[10px] text-[var(--text-secondary)] leading-relaxed mt-1">
                    {anomaly.reason} • Case {anomaly.case_id}.
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Side: Performance stats (4 cols on lg) */}
        <div className="lg:col-span-4 bg-secondary-bg/25 border border-border-color p-5 rounded-card flex flex-col justify-between">
          <span className="text-[10px] font-mono font-bold text-[var(--text-muted)] uppercase tracking-widest block border-b border-[var(--border-muted)] pb-2 select-none">
            Predictive Model Metrics
          </span>

          <div className="flex-1 flex flex-col justify-center gap-3.5 py-4 font-mono text-xs">
            <div className="flex justify-between items-center">
              <span className="text-[var(--text-muted)]">Algorithm Model</span>
              <span className="text-[var(--text-primary)] font-bold">{modelInfo?.risk_algorithm ?? 'No backend model'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[var(--text-muted)]">Root Mean Square Error</span>
              <span className="text-orange-400 font-bold">
                {modelInfo?.risk_metrics?.rmse ? modelInfo.risk_metrics.rmse.toFixed(4) : (modelInfo?.risk_model_loaded === false ? 'Rule-based fallback active' : 'No backend metric')}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[var(--text-muted)]">Verification Dataset</span>
              <span className="text-[var(--text-primary)] font-bold">{modelInfo?.training_rows ? `${modelInfo.training_rows} rows` : `${predictionRows.length} risk clusters`}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[var(--text-muted)]">Last Epoch updates</span>
              <span className="text-[#0E9E78] font-bold">{modelInfo?.trained_on ? new Date(modelInfo.trained_on).toLocaleDateString() : (riskScores?.window ?? 'No backend window')}</span>
            </div>
          </div>
        </div>
      </div>

    </div>
  );
};
export default Predictions;

