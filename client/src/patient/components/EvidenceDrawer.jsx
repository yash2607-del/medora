import React from 'react';
import {
  X,
  FileText,
  CheckCircle,
  AlertCircle,
  ShieldCheck,
  Info
} from 'lucide-react';

export default function EvidenceDrawer({
  isOpen,
  onClose,
  evidenceItem,
  reportMeta
}) {
  if (!isOpen || !evidenceItem) {
    return null;
  }

  const testName =
    evidenceItem.test_name ||
    evidenceItem.test_name_normalized ||
    evidenceItem.test_name_original ||
    'Unknown Test';

  const originalName =
    evidenceItem.test_name_original;

  const currentValue =
    evidenceItem.current_value ??
    evidenceItem.normalized_value ??
    evidenceItem.original_value;

  const currentUnit =
    evidenceItem.unit ||
    evidenceItem.normalized_unit ||
    evidenceItem.original_unit ||
    '';

  const previousValue =
    evidenceItem.previous_value;

  const previousUnit =
    evidenceItem.previous_unit ||
    currentUnit;

  const status =
    String(evidenceItem.status || 'UNKNOWN').toUpperCase();

  const referenceText =
    evidenceItem.reference_text ||
    (
      evidenceItem.reference_low !== null &&
      evidenceItem.reference_low !== undefined &&
      evidenceItem.reference_high !== null &&
      evidenceItem.reference_high !== undefined
        ? `${evidenceItem.reference_low} - ${evidenceItem.reference_high}`
        : null
    );

  const reportId =
    evidenceItem.report_id ||
    reportMeta?.report_id ||
    'Unknown Report';

  const reportDate =
    evidenceItem.report_date ||
    reportMeta?.report_date ||
    null;

  const sourcePage =
    evidenceItem.source_page ??
    evidenceItem.page_number ??
    null;

  const sourceText =
    evidenceItem.source_text ||
    evidenceItem.raw_text ||
    null;

  const getStatusClasses = () => {
    switch (status) {
      case 'HIGH':
        return {
          badge:
            'bg-red-100 text-red-700 border-red-200',
          icon: 'text-red-600'
        };

      case 'LOW':
        return {
          badge:
            'bg-amber-100 text-amber-700 border-amber-200',
          icon: 'text-amber-600'
        };

      case 'NORMAL':
        return {
          badge:
            'bg-emerald-100 text-emerald-700 border-emerald-200',
          icon: 'text-emerald-600'
        };

      default:
        return {
          badge:
            'bg-slate-100 text-slate-600 border-slate-200',
          icon: 'text-slate-500'
        };
    }
  };

  const statusClasses = getStatusClasses();

  const renderStatusIcon = () => {
    if (status === 'NORMAL') {
      return <CheckCircle size={13} />;
    }

    if (status === 'HIGH' || status === 'LOW') {
      return <AlertCircle size={13} />;
    }

    return <Info size={13} />;
  };

  return (
    <div
      className="fixed inset-0 z-50 overflow-hidden bg-black/40 backdrop-blur-sm flex justify-end animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-label="Data provenance and evidence"
    >
      {/* Backdrop */}
      <button
        type="button"
        aria-label="Close evidence drawer"
        onClick={onClose}
        className="absolute inset-0 cursor-default"
      />

      {/* Drawer */}
      <div className="relative w-full max-w-md bg-white h-full shadow-2xl flex flex-col border-l border-slate-200 animate-slide-up">

        {/* Header */}
        <div className="p-4 border-b border-slate-200 flex justify-between items-center bg-slate-50 shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-9 h-9 rounded-xl bg-primary/10 text-primary flex items-center justify-center shrink-0">
              <ShieldCheck size={19} />
            </div>

            <div className="min-w-0">
              <h3 className="font-bold text-slate-900 text-sm">
                Data Provenance & Evidence
              </h3>

              <p className="text-[10px] text-slate-500 mt-0.5">
                Source information for this result
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close provenance"
            className="p-2 rounded-lg hover:bg-slate-200 text-slate-500 hover:text-slate-700 transition-colors cursor-pointer"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4 text-sm text-slate-700">

          {/* Test identity */}
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Test Parameter
            </span>

            <div className="text-lg font-bold text-slate-900 mt-0.5">
              {testName}
            </div>

            {originalName &&
              evidenceItem.test_name_normalized &&
              originalName !==
                evidenceItem.test_name_normalized && (
                <div className="text-xs text-slate-500 mt-1">
                  Original in report:{' '}
                  <span className="font-medium text-slate-700">
                    {originalName}
                  </span>
                </div>
              )}

            <div className="flex flex-wrap gap-x-4 gap-y-1 mt-3 text-[11px] text-slate-500">
              <span>
                Report:{' '}
                <strong className="font-mono text-slate-700">
                  {reportId}
                </strong>
              </span>

              {reportDate && (
                <span>
                  Date:{' '}
                  <strong className="text-slate-700">
                    {reportDate}
                  </strong>
                </span>
              )}
            </div>
          </div>

          {/* Current + previous readings */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">

            {/* Current */}
            <div className="p-3 rounded-xl border border-slate-200 bg-white">
              <span className="text-xs text-slate-500">
                Current Value
              </span>

              <div className="text-base font-bold text-slate-900 mt-1">
                {currentValue !== null &&
                currentValue !== undefined &&
                currentValue !== ''
                  ? currentValue
                  : 'N/A'}

                {currentUnit && (
                  <span className="text-xs font-normal text-slate-500 ml-1">
                    {currentUnit}
                  </span>
                )}
              </div>

              <span
                className={`inline-flex items-center gap-1 mt-2 px-2 py-0.5 rounded border text-[11px] font-semibold ${statusClasses.badge}`}
              >
                {renderStatusIcon()}
                {status}
              </span>
            </div>

            {/* Previous */}
            <div className="p-3 rounded-xl border border-slate-200 bg-white">
              <span className="text-xs text-slate-500">
                Previous Reading
              </span>

              {previousValue !== null &&
              previousValue !== undefined ? (
                <>
                  <div className="text-base font-bold text-slate-900 mt-1">
                    {previousValue}

                    {previousUnit && (
                      <span className="text-xs font-normal text-slate-500 ml-1">
                        {previousUnit}
                      </span>
                    )}
                  </div>

                  {evidenceItem.previous_status && (
                    <span className="inline-flex mt-2 px-2 py-0.5 rounded border border-slate-200 bg-slate-100 text-slate-600 text-[11px] font-semibold">
                      {evidenceItem.previous_status}
                    </span>
                  )}
                </>
              ) : (
                <div className="text-xs text-slate-400 italic mt-2">
                  No prior record
                </div>
              )}
            </div>
          </div>

          {/* Reference interval */}
          <div className="p-3 rounded-xl border border-slate-200 bg-white">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">
                Reference Interval
              </span>

              {referenceText && (
                <span className="text-[10px] font-semibold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded">
                  Available
                </span>
              )}
            </div>

            <div className="font-semibold text-slate-800 mt-1">
              {referenceText || 'Not available'}
            </div>

            {evidenceItem.reference_source && (
              <div className="text-[11px] text-slate-500 mt-1">
                Source:{' '}
                <span className="font-medium text-slate-700">
                  {evidenceItem.reference_source}
                </span>
              </div>
            )}

            {!referenceText && (
              <div className="flex items-start gap-1.5 mt-2 text-[10px] text-slate-400">
                <Info
                  size={12}
                  className="shrink-0 mt-0.5"
                />
                <span>
                  No reference interval was supplied by the
                  structured evidence for this result.
                </span>
              </div>
            )}
          </div>

          {/* Source provenance */}
          <div className="p-3 rounded-xl border border-slate-200 bg-white space-y-3">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
              <FileText
                size={15}
                className="text-primary"
              />
              Source OCR Provenance
            </div>

            {sourcePage !== null &&
            sourcePage !== undefined ? (
              <div className="text-xs text-slate-600">
                Page Number:{' '}
                <span className="font-semibold text-slate-800">
                  {sourcePage}
                </span>
              </div>
            ) : (
              <div className="text-xs text-slate-400">
                Page number not available.
              </div>
            )}

            {sourceText ? (
              <div>
                <span className="text-xs text-slate-500">
                  Raw OCR Extracted Text:
                </span>

                <pre className="mt-1 p-3 bg-slate-900 text-emerald-400 text-xs font-mono rounded-lg overflow-x-auto whitespace-pre-wrap break-words max-h-48 overflow-y-auto">
                  {sourceText}
                </pre>
              </div>
            ) : (
              <div className="flex items-start gap-2 p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-400 italic">
                <Info
                  size={13}
                  className="shrink-0 mt-0.5"
                />
                <span>
                  Source OCR text is not available for this
                  evidence item.
                </span>
              </div>
            )}
          </div>

          {/* Extraction metadata */}
          {(evidenceItem.extraction_confidence !==
            undefined ||
            evidenceItem.confidence !== undefined ||
            evidenceItem.source_page !==
              undefined) && (
            <div className="p-3 rounded-xl border border-slate-200 bg-white">
              <div className="text-xs font-semibold text-slate-700 mb-2">
                Extraction Metadata
              </div>

              <div className="grid grid-cols-2 gap-2 text-[11px]">
                {(
                  evidenceItem.extraction_confidence ??
                  evidenceItem.confidence
                ) !== undefined && (
                  <div className="bg-slate-50 rounded-lg p-2">
                    <div className="text-slate-400">
                      Extraction Confidence
                    </div>

                    <div className="font-semibold text-slate-700 mt-0.5">
                      {(
                        Number(
                          evidenceItem.extraction_confidence ??
                            evidenceItem.confidence
                        ) * 100
                      ).toFixed(0)}
                      %
                    </div>
                  </div>
                )}

                {sourcePage !== null &&
                  sourcePage !== undefined && (
                    <div className="bg-slate-50 rounded-lg p-2">
                      <div className="text-slate-400">
                        Source Page
                      </div>

                      <div className="font-semibold text-slate-700 mt-0.5">
                        {sourcePage}
                      </div>
                    </div>
                  )}
              </div>
            </div>
          )}

          {/* Isolation note */}
          <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 flex gap-2.5">
            <CheckCircle
              size={18}
              className="text-emerald-600 shrink-0 mt-0.5"
            />

            <div className="text-xs text-emerald-900 leading-relaxed">
              <strong>Patient data isolation:</strong>{' '}
              This evidence belongs to the patient report
              processing layer. It is not sourced from the
              company knowledge-base RAG collection.
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="w-full py-2.5 bg-primary hover:bg-primary-hover text-white font-medium rounded-xl transition-colors cursor-pointer"
          >
            Close Provenance
          </button>
        </div>
      </div>
    </div>
  );
}