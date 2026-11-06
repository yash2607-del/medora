import React from 'react';
import {
  Sparkles,
  ShieldCheck,
  AlertCircle,
  RefreshCw,
  Printer,
  FileText,
  Info
} from 'lucide-react';

export default function AIReportView({
  aiReport,
  onRefresh,
  loading,
  onOpenEvidence
}) {
  const formatDateTime = (value) => {
    if (!value) {
      return 'Recent';
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return String(value);
    }

    return date.toLocaleString('en-IN', {
      dateStyle: 'medium',
      timeStyle: 'short'
    });
  };

  const renderInlineMarkdown = (text) => {
    const parts = String(text || '').split(
      /(\*\*.*?\*\*)/g
    );

    return parts.map((part, index) => {
      if (
        part.startsWith('**') &&
        part.endsWith('**')
      ) {
        return (
          <strong
            key={index}
            className="font-bold text-slate-900"
          >
            {part.slice(2, -2)}
          </strong>
        );
      }

      return (
        <React.Fragment key={index}>
          {part}
        </React.Fragment>
      );
    });
  };

  const renderFindings = (findings) => {
    if (!findings) {
      return (
        <div className="flex items-start gap-2 p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-500">
          <Info
            size={15}
            className="shrink-0 mt-0.5"
          />
          <span>
            No detailed findings were returned by the
            report generation service.
          </span>
        </div>
      );
    }

    const blocks = String(findings)
      .split(/\n\s*\n/)
      .map((block) => block.trim())
      .filter(Boolean);

    return blocks.map((block, blockIndex) => {
      const lines = block
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean);

      if (
        lines.length > 0 &&
        lines.every((line) =>
          line.startsWith('- ')
        )
      ) {
        return (
          <ul
            key={blockIndex}
            className="list-disc pl-5 space-y-1.5"
          >
            {lines.map((line, lineIndex) => (
              <li key={lineIndex}>
                {renderInlineMarkdown(
                  line.replace(/^- /, '')
                )}
              </li>
            ))}
          </ul>
        );
      }

      if (block.startsWith('### ')) {
        return (
          <h4
            key={blockIndex}
            className="text-base font-bold text-slate-900 pt-3 border-t border-slate-100"
          >
            {renderInlineMarkdown(
              block.replace(/^### /, '')
            )}
          </h4>
        );
      }

      if (block.startsWith('## ')) {
        return (
          <h4
            key={blockIndex}
            className="text-lg font-bold text-slate-900 pt-3 border-t border-slate-100"
          >
            {renderInlineMarkdown(
              block.replace(/^## /, '')
            )}
          </h4>
        );
      }

      return (
        <p key={blockIndex}>
          {renderInlineMarkdown(block)}
        </p>
      );
    });
  };

  if (!aiReport) {
    return (
      <div className="p-12 text-center bg-white rounded-3xl border border-slate-200 shadow-sm space-y-4">
        <div className="w-14 h-14 rounded-full bg-primary/10 text-primary mx-auto flex items-center justify-center">
          <Sparkles size={28} />
        </div>

        <h4 className="text-lg font-bold text-slate-800">
          No AI Explanation Generated Yet
        </h4>

        <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
          Generate an evidence-grounded explanation for
          this patient report. Numerical values, status
          classifications, and trend calculations are
          determined by the report processing pipeline.
        </p>

        <button
          type="button"
          onClick={onRefresh}
          disabled={loading || !onRefresh}
          className="px-6 py-2.5 bg-primary hover:bg-primary-hover text-white text-xs font-bold rounded-2xl shadow-lg shadow-primary/20 transition-all inline-flex items-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Sparkles
            size={16}
            className={
              loading ? 'animate-spin' : ''
            }
          />

          <span>
            {loading
              ? 'Generating...'
              : 'Generate AI Report'}
          </span>
        </button>
      </div>
    );
  }

  const disclaimer =
    aiReport.disclaimer ||
    'This explanation is for informational purposes only and does not replace advice from a qualified healthcare professional.';

  return (
    <div className="space-y-6">

      {/* Action Header */}
      <div className="p-6 bg-white rounded-3xl border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">

        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold uppercase tracking-wider text-primary px-2.5 py-0.5 rounded-full bg-primary/10">
              AI Report Explanation
            </span>

            <span className="text-xs text-slate-400 font-mono">
              Version:{' '}
              {aiReport.prompt_version ||
                'patient_report_v1'}
            </span>
          </div>

          <h3 className="text-xl font-extrabold text-slate-900 mt-1">
            Personal Report Explanation
          </h3>

          <p className="text-xs text-slate-500 mt-1">
            Grounded in structured patient-report evidence
            {' • '}
            Generated on{' '}
            {formatDateTime(
              aiReport.generated_at
            )}
          </p>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">

          {/* Print */}
          <button
            type="button"
            onClick={() => window.print()}
            className="p-2.5 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-600 transition-colors cursor-pointer"
            title="Print report"
            aria-label="Print report"
          >
            <Printer size={16} />
          </button>

          {/* Regenerate */}
          <button
            type="button"
            onClick={onRefresh}
            disabled={loading || !onRefresh}
            className="p-2.5 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-600 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            title="Regenerate report"
            aria-label="Regenerate report"
          >
            <RefreshCw
              size={16}
              className={
                loading
                  ? 'animate-spin text-primary'
                  : ''
              }
            />
          </button>

          {/* Evidence */}
          <button
            type="button"
            onClick={onOpenEvidence}
            disabled={!onOpenEvidence}
            className="px-4 py-2.5 rounded-xl bg-slate-900 text-white text-xs font-semibold hover:bg-slate-800 transition-all flex items-center gap-1.5 cursor-pointer shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ShieldCheck
              size={16}
              className="text-emerald-400"
            />
            <span>Verify Evidence</span>
          </button>
        </div>
      </div>

      {/* Report document */}
      <div className="p-8 bg-white rounded-3xl border border-slate-200 shadow-sm space-y-6">

        {/* Summary */}
        {aiReport.summary && (
          <div className="p-4 bg-primary/5 rounded-2xl border border-primary/20 text-xs text-slate-700 leading-relaxed">
            <div className="flex items-start gap-2">
              <Sparkles
                size={15}
                className="text-primary shrink-0 mt-0.5"
              />

              <div>
                <strong className="text-primary font-bold">
                  Executive Summary:
                </strong>{' '}
                {aiReport.summary}
              </div>
            </div>
          </div>
        )}

        {/* Findings */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <FileText
              size={17}
              className="text-primary"
            />

            <h4 className="font-bold text-slate-900">
              Findings & Explanation
            </h4>
          </div>

          <div className="max-w-none text-xs sm:text-sm text-slate-700 space-y-4 leading-relaxed font-sans">
            {renderFindings(
              aiReport.findings
            )}
          </div>
        </div>

        {/* Evidence reminder */}
        <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 flex items-start gap-3">
          <ShieldCheck
            size={18}
            className="text-primary shrink-0 mt-0.5"
          />

          <div className="text-[11px] text-slate-600 leading-relaxed">
            <strong className="text-slate-800">
              Evidence-grounded explanation:
            </strong>{' '}
            This explanation is intended to describe the
            structured patient-report evidence available to
            the application. It should not be treated as a
            diagnosis or as a substitute for professional
            medical review.
          </div>
        </div>

        {/* Safety disclaimer */}
        <div className="p-4 bg-amber-50 rounded-2xl border border-amber-200 flex items-start gap-3">
          <AlertCircle
            size={18}
            className="text-amber-600 shrink-0 mt-0.5"
          />

          <div className="text-[11px] text-amber-900 leading-relaxed">
            <strong>Medical Notice:</strong>{' '}
            {disclaimer}
          </div>
        </div>
      </div>
    </div>
  );
}