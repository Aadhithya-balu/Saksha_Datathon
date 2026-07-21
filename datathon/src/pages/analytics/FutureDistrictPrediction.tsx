import React, { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, BarChart3, Loader2, Radar, ShieldAlert } from 'lucide-react';
import {
  getFutureDistrictRiskDistricts,
  predictFutureDistrictRisk,
  type FutureDistrictRiskRequest,
  type FutureDistrictRiskResponse,
} from '../../services/api';

type FormState = Record<keyof FutureDistrictRiskRequest, string>;

const initialForm: FormState = {
  DISTRICT: '',
  YEAR: new Date().getFullYear().toString(),
  VIOLENT_CRIME: '',
  PROPERTY_CRIME: '',
  WOMEN_CRIME: '',
  PREVIOUS_YEAR_CRIME: '',
  CRIME_GROWTH: '',
  ROLLING_AVG: '',
};

const numericFields: Array<keyof FutureDistrictRiskRequest> = [
  'YEAR',
  'VIOLENT_CRIME',
  'PROPERTY_CRIME',
  'WOMEN_CRIME',
  'PREVIOUS_YEAR_CRIME',
  'CRIME_GROWTH',
  'ROLLING_AVG',
];

const fieldLabels: Record<keyof FutureDistrictRiskRequest, string> = {
  DISTRICT: 'District',
  YEAR: 'Prediction Year',
  VIOLENT_CRIME: 'Violent Crime',
  PROPERTY_CRIME: 'Property Crime',
  WOMEN_CRIME: 'Women Crime',
  PREVIOUS_YEAR_CRIME: 'Previous Year Crime',
  CRIME_GROWTH: 'Crime Growth',
  ROLLING_AVG: 'Rolling Average',
};

const riskClasses: Record<FutureDistrictRiskResponse['risk_level'], string> = {
  LOW: 'bg-[#0E9E78]/10 border-[#0E9E78]/30 text-[#0E9E78]',
  MEDIUM: 'bg-[#D4820A]/10 border-[#D4820A]/30 text-[#D4820A]',
  HIGH: 'bg-[#C94A2A]/10 border-[#C94A2A]/30 text-[#C94A2A]',
  VERY_HIGH: 'bg-red-500/10 border-red-500/40 text-red-300',
};

const formatNumber = (value: number) => new Intl.NumberFormat('en-IN').format(value);

export const FutureDistrictPrediction: React.FC = () => {
  const [form, setForm] = useState<FormState>(initialForm);
  const [districts, setDistricts] = useState<string[]>([]);
  const [result, setResult] = useState<FutureDistrictRiskResponse | null>(null);
  const [error, setError] = useState<string>('');
  const [districtError, setDistrictError] = useState<string>('');
  const [isDistrictsLoading, setIsDistrictsLoading] = useState(true);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    let isMounted = true;

    setIsDistrictsLoading(true);
    void getFutureDistrictRiskDistricts()
      .then((trainedDistricts) => {
        if (!isMounted) {
          return;
        }
        setDistricts(trainedDistricts);
        setDistrictError('');
      })
      .catch((apiError) => {
        if (!isMounted) {
          return;
        }
        setDistricts([]);
        setDistrictError(apiError instanceof Error ? apiError.message : 'Unable to load trained districts.');
      })
      .finally(() => {
        if (isMounted) {
          setIsDistrictsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const validationError = useMemo(() => {
    if (!form.DISTRICT.trim()) {
      return 'Select a trained district.';
    }

    if (districts.length > 0 && !districts.includes(form.DISTRICT)) {
      return 'Select a district from the trained model list.';
    }

    for (const field of numericFields) {
      const value = Number(form[field]);
      if (form[field] === '' || Number.isNaN(value)) {
        return `${fieldLabels[field]} must be a valid number.`;
      }
      if (field !== 'CRIME_GROWTH' && value < 0) {
        return `${fieldLabels[field]} cannot be negative.`;
      }
    }

    const year = Number(form.YEAR);
    if (year < 1900 || year > 2100) {
      return 'Prediction Year must be between 1900 and 2100.';
    }

    return '';
  }, [districts, form]);

  const updateField = (field: keyof FutureDistrictRiskRequest, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');

    if (validationError) {
      setError(validationError);
      return;
    }

    const payload = Object.fromEntries(
      Object.entries(form).map(([key, value]) => [
        key,
        key === 'DISTRICT' ? value.trim() : Number(value),
      ])
    ) as unknown as FutureDistrictRiskRequest;

    setIsLoading(true);
    try {
      const response = await predictFutureDistrictRisk(payload);
      setResult(response);
    } catch (apiError) {
      setResult(null);
      setError(apiError instanceof Error ? apiError.message : 'Prediction request failed.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 p-1 md:p-3 select-none bg-[#060b13]">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-white/5 pb-3">
        <div>
          <h2 className="text-md font-mono font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Radar className="w-5 h-5 text-[#0E9E78]" />
            Future District Risk Prediction
          </h2>
          <p className="text-[9.5px] font-mono text-[#6A7A96] mt-0.5">
            DISTRICT CRIME COUNT FORECAST - RANDOM FOREST REGRESSOR
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-5">
        <form
          onSubmit={handleSubmit}
          className="xl:col-span-7 bg-secondary-bg/25 border border-border-color p-5 rounded-card flex flex-col gap-4"
        >
          <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest block border-b border-white/5 pb-2">
            District Feature Input
          </span>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <label className="flex flex-col gap-1.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-[#6A7A96]">
                {fieldLabels.DISTRICT}
              </span>
              <select
                value={form.DISTRICT}
                disabled={isDistrictsLoading || districts.length === 0}
                onChange={(event) => updateField('DISTRICT', event.target.value)}
                className="w-full rounded-btn border border-border-color bg-slate-950/60 px-3 py-2 text-xs font-mono text-[#E8EDF5] outline-none transition-colors focus:border-[#1E6FD9]/60 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <option value="">{isDistrictsLoading ? 'Loading trained districts' : 'Select district'}</option>
                {districts.map((district) => (
                  <option key={district} value={district}>
                    {district}
                  </option>
                ))}
              </select>
            </label>

            {numericFields.map((field) => (
              <label key={field} className="flex flex-col gap-1.5">
                <span className="text-[10px] font-mono uppercase tracking-wider text-[#6A7A96]">
                  {fieldLabels[field]}
                </span>
                <input
                  value={form[field]}
                  type="number"
                  step={field === 'YEAR' ? 1 : 'any'}
                  min={field !== 'CRIME_GROWTH' ? 0 : undefined}
                  onChange={(event) => updateField(field, event.target.value)}
                  className="w-full rounded-btn border border-border-color bg-slate-950/60 px-3 py-2 text-xs font-mono text-[#E8EDF5] outline-none transition-colors placeholder:text-[#46546C] focus:border-[#1E6FD9]/60"
                />
              </label>
            ))}
          </div>

          {(districtError || error) && (
            <div className="flex items-start gap-2 rounded-btn border border-[#C94A2A]/30 bg-[#C94A2A]/10 px-3 py-2 text-[10px] font-mono text-[#ffb09a]">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>{districtError || error}</span>
            </div>
          )}

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={isLoading || isDistrictsLoading || districts.length === 0}
              className="px-3 py-2 bg-[#0E9E78]/10 hover:bg-[#0E9E78]/20 disabled:opacity-60 border border-[#0e9e78]/30 text-[#0E9E78] font-mono text-[10px] uppercase rounded-btn transition-colors cursor-pointer flex items-center gap-2"
            >
              {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <BarChart3 className="w-3.5 h-3.5" />}
              Predict Risk
            </button>
          </div>
        </form>

        <div className="xl:col-span-5 bg-secondary-bg/25 border border-border-color p-5 rounded-card flex flex-col gap-4">
          <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest block border-b border-white/5 pb-2">
            Prediction Output
          </span>

          {result ? (
            <>
              <div className="flex items-center justify-between gap-3 rounded-btn border border-slate-900 bg-slate-950/45 p-4">
                <div className="flex items-center gap-3">
                  <ShieldAlert className="h-6 w-6 text-[#C94A2A]" />
                  <div>
                    <p className="text-[10px] font-mono uppercase tracking-wider text-[#6A7A96]">Predicted Crime Count</p>
                    <p className="text-2xl font-mono font-bold text-white">{formatNumber(result.predicted_crime_count)}</p>
                  </div>
                </div>
                <span className={`rounded-btn border px-2.5 py-1 text-[10px] font-mono font-bold uppercase ${riskClasses[result.risk_level]}`}>
                  {result.risk_level}
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 font-mono text-xs">
                <div className="rounded-btn border border-slate-900 bg-slate-950/45 p-3">
                  <span className="text-[#6A7A96]">Model Name</span>
                  <p className="mt-1 font-bold text-[#E8EDF5]">{result.model}</p>
                </div>
                <div className="rounded-btn border border-slate-900 bg-slate-950/45 p-3">
                  <span className="text-[#6A7A96]">R2</span>
                  <p className="mt-1 font-bold text-[#0E9E78]">{result.metrics.r2}</p>
                </div>
                <div className="rounded-btn border border-slate-900 bg-slate-950/45 p-3">
                  <span className="text-[#6A7A96]">MAE</span>
                  <p className="mt-1 font-bold text-[#E8EDF5]">{result.metrics.mae}</p>
                </div>
                <div className="rounded-btn border border-slate-900 bg-slate-950/45 p-3">
                  <span className="text-[#6A7A96]">RMSE</span>
                  <p className="mt-1 font-bold text-[#E8EDF5]">{result.metrics.rmse}</p>
                </div>
              </div>
            </>
          ) : (
            <div className="flex min-h-[220px] items-center justify-center rounded-btn border border-dashed border-border-color bg-slate-950/30 text-center font-mono text-[10px] uppercase tracking-wider text-[#6A7A96]">
              Awaiting district feature submission
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FutureDistrictPrediction;
