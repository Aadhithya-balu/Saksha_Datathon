import React, { useState, useRef } from "react";
import { type FIRDetailRecord, updateFIR } from "../../services/api";
import { FileText, UploadCloud, Trash2, ShieldAlert } from "lucide-react";
import { useAuthStore } from "../../store/authStore";
import { useAuditStore } from "../../store/auditStore";
import { downloadSecureDossier } from "../../utils/downloader";
import { ExportMenu } from "../reports";
interface FIRAttachmentsProps {
  fir: FIRDetailRecord;
  onAttachmentAdded: (updatedAttachments: any[]) => void;
}

export const FIRAttachments: React.FC<FIRAttachmentsProps> = ({
  fir,
  onAttachmentAdded,
}) => {
  const { user } = useAuthStore();
  const { addLog } = useAuditStore();
  const [attachments, setAttachments] = useState<any[]>(fir.attachments || []);
  const [uploadingFile, setUploadingFile] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const formatSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      void simulateUpload(e.target.files[0]);
    }
  };

  const simulateUpload = async (file: File) => {
    setUploadingFile(file.name);
    setUploadProgress(0);

    // Simulate progress
    const interval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          return 100;
        }
        return prev + 10;
      });
    }, 150);

    // Wait for simulate progress to finish
    await new Promise((resolve) => setTimeout(resolve, 1800));

    // Prepare updated attachments list
    const newAttachment = {
      name: file.name,
      size: file.size,
      uploadedAt: new Date().toISOString(),
    };

    const updated = [...attachments, newAttachment];

    try {
      // Save to database
      await updateFIR(fir.id, { attachments: updated });
      setAttachments(updated);
      onAttachmentAdded(updated);

      if (user) {
        addLog(
          user.name,
          user.badgeId,
          "UPLOAD",
          `Attached investigative document [${file.name}] to FIR registry [${fir.fir_number}]`,
        );
      }
    } catch (err) {
      alert("Failed to save attachment metadata to backend database.");
    } finally {
      setUploadingFile(null);
      setUploadProgress(0);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleDelete = async (indexToDelete: number) => {
    const fileToDelete = attachments[indexToDelete];
    const updated = attachments.filter((_, idx) => idx !== indexToDelete);

    if (
      !window.confirm(`Are you sure you want to remove ${fileToDelete.name}?`)
    ) {
      return;
    }

    try {
      await updateFIR(fir.id, { attachments: updated });
      setAttachments(updated);
      onAttachmentAdded(updated);

      if (user) {
        addLog(
          user.name,
          user.badgeId,
          "DELETE",
          `Deleted document attachment [${fileToDelete.name}] from FIR registry [${fir.fir_number}]`,
        );
      }
    } catch (err) {
      alert("Failed to remove attachment metadata from database.");
    }
  };

  const handleDownload = (
    filename: string,
    format: "pdf" | "docx" | "txt" | "csv" | "xlsx" = "pdf",
  ) => {
    downloadSecureDossier(
      `ATTACHMENT_${filename.replace(/[^a-zA-Z0-9]/g, "_")}`,
      {
        "FIR ID": fir.fir_number,
        "File Name": filename,
        Classification: "SAKSHA CASE RECON DATA - CLASSIFIED SYSTEM",
        Timestamp: new Date().toISOString(),
      },
      `CONFIDENTIAL - ${user?.badgeId || "SYSTEM"}`,
      format,
    );

    if (user) {
      addLog(
        user.name,
        user.badgeId,
        "DOWNLOAD",
        `Downloaded classified attachment [${filename}] for case [${fir.fir_number}]`,
      );
    }
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const onDragLeave = () => {
    setIsDragOver(false);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      void simulateUpload(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="bg-[var(--bg-tertiary)]/30 border border-border-color p-5 rounded-card flex flex-col justify-between overflow-hidden">
      <div className="flex items-center gap-2 border-b border-[var(--border-primary)] pb-3 mb-4">
        <UploadCloud className="w-4 h-4 text-[var(--accent-teal)]" />
        <span className="text-[10px] font-bold text-[var(--text-primary)] uppercase tracking-wider">
          Classification & FIR Attachments
        </span>
      </div>

      <div className="space-y-4 text-xs font-mono">
        {/* Drop zone */}
        <div
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-lg p-5 flex flex-col items-center justify-center gap-2 cursor-pointer transition-all duration-200 ${
            isDragOver
              ? "border-[var(--accent-teal)] bg-[var(--accent-teal)]/10"
              : "border-[var(--border-primary)] hover:border-[var(--border-secondary)] bg-[var(--bg-secondary)]/40 hover:bg-[var(--bg-secondary)]/75"
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            className="hidden"
          />

          {uploadingFile ? (
            <div className="w-full text-center space-y-2">
              <p className="text-[9.5px] uppercase text-[var(--text-primary)] truncate">
                Uploading: {uploadingFile}
              </p>
              <div className="w-full h-1.5 bg-[var(--bg-tertiary)] rounded-full overflow-hidden border border-[var(--border-primary)]">
                <div
                  className="h-full bg-emerald-500 rounded-full transition-all duration-150"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <span className="text-[8px] text-[var(--text-muted)]">
                {uploadProgress}% Telemetry Synced
              </span>
            </div>
          ) : (
            <>
              <UploadCloud className="w-8 h-8 text-[var(--text-muted)] group-hover:text-[var(--text-primary)]" />
              <span className="text-[9px] uppercase tracking-wider text-[var(--text-muted)] text-center">
                Drag investigative reports or click to browse
              </span>
              <span className="text-[7.5px] text-[var(--text-muted)] uppercase">
                PDF, JPG, PNG â€¢ SECURE CHANNEL ONLY
              </span>
            </>
          )}
        </div>

        {/* Attachments List */}
        <div className="space-y-2 max-h-[180px] overflow-y-auto custom-scrollbar pr-1">
          {attachments.map((file, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-2.5 bg-[var(--bg-secondary)]/60 border border-[var(--border-primary)] rounded-md hover:border-[var(--border-primary)] transition-colors"
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <FileText className="w-4 h-4 text-[var(--text-secondary)] shrink-0" />
                <div className="truncate">
                  <p className="text-[10px] text-[var(--text-primary)] font-medium truncate select-all">
                    {file.name}
                  </p>
                  <p className="text-[8px] text-[var(--text-muted)] mt-0.5">
                    {formatSize(file.size || 0)}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1.5 shrink-0">
                <ExportMenu
                  onExport={(format) => handleDownload(file.name, format)}
                />
                <button
                  onClick={() => handleDelete(idx)}
                  className="p-1 text-[var(--text-muted)] hover:text-red-400 hover:bg-[var(--bg-tertiary)] rounded cursor-pointer transition-colors"
                  title="Remove Document"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}

          {attachments.length === 0 && !uploadingFile && (
            <div className="flex flex-col items-center justify-center p-6 border border-dashed border-[var(--border-primary)] rounded-lg text-[var(--text-muted)] text-center gap-1">
              <ShieldAlert className="w-4 h-4 text-amber-500/60" />
              <span className="text-[9px] uppercase tracking-wide">
                No dossiers attached
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
export default FIRAttachments;
