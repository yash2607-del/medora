import React from 'react';
import {
  Calendar,
  Building2,
  AlertCircle,
  CheckCircle,
  ChevronRight
} from 'lucide-react';

export default function ReportCard({
  report,
  isSelected,
  onSelect,
  onGenerateAI
}) {
  const abnormalCount = Number(report?.abnormal_count) || 0;
  const totalTests = Number(report?.total_tests) || 0;

  const hasAbnormals = abnormalCount > 0;

  const reportDate = report?.report_date
    ? new Date(report.report_date).toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
      })
    : 'Date unavailable';

  const laboratory = report?.laboratory || "Lord's Pathology";
  const category = report?.report_category || 'Diagnostic';
  const reportId = report?.report_id || 'Unknown Report';

  return (
    <div
      onClick={() => onSelect(report)}
      className={`p-4 rounded-2xl border transition-all cursor-pointer ${
        isSelected
          ? 'bg-primary/5 border-primary shadow-md'
          : 'bg-white border-slate-200 hover:border-primary/40 hover:shadow-sm'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        {/* Report information */}
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-xs font-bold text-slate-900">
              {reportId}
            </span>

            <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
              {category}
            </span>
          </div>

          <div className="flex items-center gap-3 flex-wrap text-xs text-slate-500 mt-2">
            <span className="flex items-center gap-1">
              <Calendar
                size={13}
                className="text-slate-400 shrink-0"
              />
              {reportDate}
            </span>

            <span className="flex items-center gap-1">
              <Building2
                size={13}
                className="text-slate-400 shrink-0"
              />
              {laboratory}
            </span>
          </div>
        </div>

        {/* Abnormal status */}
        <div className="text-right shrink-0">
          {hasAbnormals ? (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-red-50 text-red-700 border border-red-200/60">
              <AlertCircle size={13} />
              {abnormalCount}{' '}
              {abnormalCount === 1 ? 'Abnormal' : 'Abnormal'}
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/60">
              <CheckCircle size={13} />
              {totalTests > 0 ? 'All Normal' : 'No Results'}
            </span>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
        <span className="text-slate-500">
          <strong className="text-slate-800">
            {totalTests}
          </strong>{' '}
          {totalTests === 1 ? 'test' : 'tests'} evaluated
        </span>

        <div className="flex items-center gap-2 text-primary font-semibold">
          <span>View Details</span>
          <ChevronRight size={14} />
        </div>
      </div>
    </div>
  );
}