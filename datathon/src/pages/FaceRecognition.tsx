import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  ScanFace, Upload, Camera, AlertTriangle, CheckCircle, XCircle,
  Loader2, Info, Shield, Eye, ChevronDown, ChevronUp, FlaskConical,
} from 'lucide-react';
import {
  recognizeFace,
  testSampleFace,
  getFaceDemoInfo,
  getFaceSamples,
  getFaceSampleImageUrl,
  getFaceRecognitionStatus,
  type FaceRecognizeResult,
  type FaceSampleImage,
} from '../services/api';

// ── Types ──────────────────────────────────────────────────────────────────

interface DemoIdentity {
  id: string;
  name: string;
  variations: string[];
  prompt: string | null;
}

// ── Result Card ────────────────────────────────────────────────────────────

const ResultCard: React.FC<{ result: FaceRecognizeResult }> = ({ result }) => (
  <div className="rounded-xl border border-[var(--border-primary)] bg-[var(--bg-secondary)] overflow-hidden">
    <div className={`px-4 py-3 border-b ${
      result.match_found
        ? 'border-[var(--accent-teal)]/30 bg-[var(--accent-teal-subtle)]'
        : result.status === 'no_face'
          ? 'border-[var(--accent-amber)]/30 bg-amber-950/20'
          : 'border-[var(--accent-coral)]/30 bg-red-950/20'
    }`}>
      <div className="flex items-center gap-2">
        {result.match_found ? (
          <CheckCircle className="w-4 h-4 text-[var(--accent-teal)]" />
        ) : result.status === 'no_face' ? (
          <AlertTriangle className="w-4 h-4 text-[var(--accent-amber)]" />
        ) : (
          <XCircle className="w-4 h-4 text-[var(--accent-coral)]" />
        )}
        <span className="text-[13px] font-bold text-[var(--text-primary)]">
          {result.match_found ? 'Match Found' : result.status === 'no_face' ? 'No Face Detected' : 'No Match'}
        </span>
      </div>
    </div>

    <div className="p-4 space-y-3">
      {/* Matched person */}
      {result.matched_person && (
        <div className="flex items-center gap-3 p-3 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-primary)]">
          <div className="w-10 h-10 rounded-full bg-[var(--accent-teal-subtle)] border border-[var(--accent-teal)]/20 flex items-center justify-center">
            <ScanFace className="w-5 h-5 text-[var(--accent-teal)]" />
          </div>
          <div>
            <p className="text-[13px] font-bold text-[var(--text-primary)]">{result.matched_person.name}</p>
            <p className="text-[11px] font-mono text-[var(--text-muted)]">{result.matched_person.id} &middot; {result.matched_person.dataset_type}</p>
          </div>
        </div>
      )}

      {/* Confidence */}
      {result.confidence !== null && (
        <div className="flex items-center justify-between p-3 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-primary)]">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">Confidence</span>
          <div className="flex items-center gap-2">
            <div className="w-24 h-2 rounded-full bg-[var(--bg-tertiary)] overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  result.confidence >= 0.8 ? 'bg-[var(--accent-teal)]' : result.confidence >= 0.6 ? 'bg-[var(--accent-amber)]' : 'bg-[var(--accent-coral)]'
                }`}
                style={{ width: `${Math.min(100, result.confidence * 100)}%` }}
              />
            </div>
            <span className="text-[13px] font-mono font-bold text-[var(--text-primary)]">{(result.confidence * 100).toFixed(1)}%</span>
          </div>
        </div>
      )}

      {/* Faces detected */}
      <div className="flex items-center justify-between p-3 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-primary)]">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">Faces Detected</span>
        <span className="text-[13px] font-mono font-bold text-[var(--text-primary)]">{result.faces_detected}</span>
      </div>

      {/* Analysis */}
      {result.analysis && (result.analysis.age || result.analysis.gender || result.analysis.emotion) && (
        <div className="p-3 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-primary)] space-y-2">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">Face Analysis</span>
          <div className="grid grid-cols-3 gap-2">
            {result.analysis.age && (
              <div className="text-center">
                <p className="text-[10px] text-[var(--text-muted)]">Age</p>
                <p className="text-[13px] font-mono font-bold text-[var(--text-primary)]">{result.analysis.age}</p>
              </div>
            )}
            {result.analysis.gender && (
              <div className="text-center">
                <p className="text-[10px] text-[var(--text-muted)]">Gender</p>
                <p className="text-[13px] font-mono font-bold text-[var(--text-primary)]">{result.analysis.gender}</p>
              </div>
            )}
            {result.analysis.emotion && (
              <div className="text-center">
                <p className="text-[10px] text-[var(--text-muted)]">Emotion</p>
                <p className="text-[13px] font-mono font-bold text-[var(--text-primary)]">{result.analysis.emotion}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Message */}
      {result.message && (
        <p className="text-[12px] text-[var(--text-muted)] italic">{result.message}</p>
      )}

      {/* Threshold info */}
      {result.threshold !== null && (
        <p className="text-[10px] text-[var(--text-disabled)] font-mono">
          Threshold: {(result.threshold * 100).toFixed(0)}% &middot; Source: {result.analysis_source || 'local'}
        </p>
      )}
    </div>
  </div>
);

// ── Demo Testing Gallery ───────────────────────────────────────────────────

const DemoGallery: React.FC<{
  samples: FaceSampleImage[];
  identities: DemoIdentity[];
  onTestSample: (imageRef: string) => void;
  testing: boolean;
}> = ({ samples, identities, onTestSample, testing }) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 pb-2 border-b border-[var(--border-primary)]">
        <FlaskConical className="w-4 h-4 text-[var(--accent-purple)]" />
        <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-primary)]">Demo Testing Gallery</span>
      </div>

      <div className="p-3 rounded-lg bg-[var(--accent-purple-subtle)] border border-[var(--accent-purple)]/20">
        <div className="flex items-start gap-2">
          <Info className="w-3.5 h-3.5 text-[var(--accent-purple)] shrink-0 mt-0.5" />
          <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">
            Select a demo identity image below to test recognition. These are synthetic/consented demo subjects — not real individuals.
          </p>
        </div>
      </div>

      {identities.map(ident => {
        const isExpanded = expandedId === ident.id;
        const identitySamples = samples.filter(s => s.id === ident.id || s.image_ref.startsWith(ident.id));

        return (
          <div key={ident.id} className="rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)] overflow-hidden">
            <button
              onClick={() => setExpandedId(isExpanded ? null : ident.id)}
              className="w-full flex items-center justify-between px-4 py-3 hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-[var(--accent-purple-subtle)] border border-[var(--accent-purple)]/20 flex items-center justify-center text-[var(--accent-purple)] font-bold text-[11px] font-mono">
                  {ident.id.slice(-3)}
                </div>
                <div className="text-left">
                  <p className="text-[13px] font-semibold text-[var(--text-primary)]">{ident.name}</p>
                  <p className="text-[10px] font-mono text-[var(--text-muted)]">{ident.id} &middot; {identitySamples.length} samples</p>
                </div>
              </div>
              {isExpanded ? <ChevronUp className="w-4 h-4 text-[var(--text-muted)]" /> : <ChevronDown className="w-4 h-4 text-[var(--text-muted)]" />}
            </button>

            {isExpanded && (
              <div className="px-4 pb-4 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                {identitySamples.map(sample => (
                  <button
                    key={sample.image_ref}
                    onClick={() => onTestSample(sample.image_ref)}
                    disabled={testing}
                    className="group relative rounded-lg border border-[var(--border-primary)] bg-[var(--bg-primary)] overflow-hidden hover:border-[var(--accent-purple)]/40 transition-all cursor-pointer disabled:opacity-50"
                  >
                    <img
                      src={getFaceSampleImageUrl(sample.image_ref)}
                      alt={`${ident.name} - ${sample.variation}`}
                      className="w-full aspect-square object-cover"
                      loading="lazy"
                    />
                    <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
                      <Camera className="w-5 h-5 text-white" />
                    </div>
                    <div className="px-2 py-1.5 text-[10px] font-mono text-[var(--text-muted)] truncate">{sample.variation}</div>
                  </button>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

// ── Main Page ──────────────────────────────────────────────────────────────

const FaceRecognition: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<FaceRecognizeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [demoIdentities, setDemoIdentities] = useState<DemoIdentity[]>([]);
  const [samples, setSamples] = useState<FaceSampleImage[]>([]);
  const [featureEnabled, setFeatureEnabled] = useState(true);
  const [testingSample, setTestingSample] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getFaceRecognitionStatus()
      .then(s => setFeatureEnabled(s.enabled))
      .catch(() => setFeatureEnabled(false));
    getFaceDemoInfo()
      .then(d => setDemoIdentities(d.identities))
      .catch(() => {});
    getFaceSamples()
      .then(s => setSamples(s))
      .catch(() => {});
  }, []);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (!selected) return;
    setFile(selected);
    setResult(null);
    setError(null);
    const url = URL.createObjectURL(selected);
    setPreview(url);
  }, []);

  const handleRecognize = useCallback(async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const res = await recognizeFace(file);
      setResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Recognition failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [file]);

  const handleTestSample = useCallback(async (imageRef: string) => {
    setTestingSample(true);
    setError(null);
    setResult(null);
    setPreview(getFaceSampleImageUrl(imageRef));
    try {
      const res = await testSampleFace(imageRef);
      setResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Test failed';
      setError(msg);
    } finally {
      setTestingSample(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const dropped = e.dataTransfer.files?.[0];
    if (!dropped || !dropped.type.startsWith('image/')) return;
    setFile(dropped);
    setResult(null);
    setError(null);
    setPreview(URL.createObjectURL(dropped));
  }, []);

  if (!featureEnabled) {
    return (
      <div className="max-w-3xl mx-auto space-y-5 pb-10">
        <div>
          <h2 className="text-lg font-bold text-[var(--text-primary)] flex items-center gap-2">
            <ScanFace className="w-5 h-5 text-[var(--accent-purple)]" />
            Face Recognition
          </h2>
        </div>
        <div className="p-6 rounded-xl border border-[var(--accent-amber)]/30 bg-amber-950/20 text-center space-y-3">
          <AlertTriangle className="w-8 h-8 text-[var(--accent-amber)] mx-auto" />
          <p className="text-[13px] font-semibold text-[var(--text-primary)]">Feature Unavailable</p>
          <p className="text-[12px] text-[var(--text-muted)]">Face recognition is disabled on this deployment.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-5 pb-10">
      {/* Header */}
      <div>
        <h2 className="text-lg font-bold text-[var(--text-primary)] flex items-center gap-2">
          <ScanFace className="w-5 h-5 text-[var(--accent-purple)]" />
          Face Recognition
        </h2>
        <p className="text-[11px] text-[var(--text-muted)] mt-0.5 font-mono uppercase tracking-wider">
          DEMO DATASET &mdash; PROTOTYPE TESTING ONLY
        </p>
      </div>

      {/* Demo banner */}
      <div className="flex items-start gap-3 p-3 bg-[var(--accent-purple-subtle)] border border-[var(--accent-purple)]/20 rounded-xl">
        <FlaskConical className="w-4 h-4 text-[var(--accent-purple)] shrink-0 mt-0.5" />
        <div>
          <p className="text-[10px] font-bold uppercase text-[var(--text-primary)] mb-0.5">Synthetic Demo Dataset</p>
          <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">
            This feature uses a synthetic demo dataset of 5 consented test identities. It is for prototype testing only and must not be used for real-world identification.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Left: Upload + Result */}
        <div className="space-y-4">
          {/* Upload area */}
          <div
            onDragOver={e => e.preventDefault()}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`relative p-6 rounded-xl border-2 border-dashed cursor-pointer transition-all ${
              preview
                ? 'border-[var(--accent-purple)]/40 bg-[var(--accent-purple-subtle)]'
                : 'border-[var(--border-primary)] bg-[var(--bg-secondary)] hover:border-[var(--accent-purple)]/30'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handleFileChange}
              className="hidden"
            />
            {preview ? (
              <div className="space-y-3">
                <img src={preview} alt="Uploaded" className="w-full max-h-64 object-contain rounded-lg" />
                <div className="flex items-center justify-between">
                  <p className="text-[11px] font-mono text-[var(--text-muted)] truncate max-w-[200px]">{file?.name}</p>
                  <button
                    onClick={e => { e.stopPropagation(); setFile(null); setPreview(null); setResult(null); }}
                    className="text-[11px] text-[var(--accent-coral)] hover:underline cursor-pointer"
                  >
                    Remove
                  </button>
                </div>
              </div>
            ) : (
              <div className="text-center space-y-2">
                <Upload className="w-8 h-8 text-[var(--text-disabled)] mx-auto" />
                <p className="text-[13px] text-[var(--text-secondary)]">Drop an image or click to upload</p>
                <p className="text-[10px] text-[var(--text-disabled)]">JPEG, PNG, WebP &middot; Max 10 MB</p>
              </div>
            )}
          </div>

          {/* Recognize button */}
          <button
            onClick={handleRecognize}
            disabled={!file || loading}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-[var(--accent-purple)] text-white text-[13px] font-semibold hover:opacity-90 disabled:opacity-50 transition-opacity cursor-pointer"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Eye className="w-4 h-4" />
                Run Face Recognition
              </>
            )}
          </button>

          {/* Error */}
          {error && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-red-950/20 border border-red-900/30">
              <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
              <p className="text-[12px] text-red-400">{error}</p>
            </div>
          )}

          {/* Result */}
          {result && <ResultCard result={result} />}
        </div>

        {/* Right: Demo Gallery */}
        <div>
          <DemoGallery
            samples={samples}
            identities={demoIdentities}
            onTestSample={handleTestSample}
            testing={testingSample}
          />
        </div>
      </div>

      {/* Security footer */}
      <div className="flex items-start gap-3 p-3 bg-[var(--bg-secondary)] border border-[var(--accent-blue)]/15 rounded-xl">
        <Shield className="w-4 h-4 text-[var(--accent-blue)] shrink-0 mt-0.5" />
        <div>
          <p className="text-[10px] font-bold uppercase text-[var(--text-primary)] mb-0.5">Privacy &amp; Security</p>
          <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">
            Uploaded images are processed in-memory and not stored. All recognition runs against a synthetic demo dataset.
            Internal storage paths are never exposed. Feature is behind existing authentication controls.
          </p>
        </div>
      </div>
    </div>
  );
};

export default FaceRecognition;
