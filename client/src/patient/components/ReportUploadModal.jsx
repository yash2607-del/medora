import React, { useEffect, useRef, useState } from 'react';
import {
  UploadCloud,
  File,
  CheckCircle2,
  AlertTriangle,
  X,
  Loader2,
  ArrowRight
} from 'lucide-react';
import { patientApi } from '../api/patientApi';

const MAX_FILE_SIZE = 15 * 1024 * 1024;

const PROCESSING_STEPS = [
  { key: 'UPLOADED', label: 'File Uploaded' },
  { key: 'PROCESSING', label: 'Processing Document' },
  { key: 'OCR_COMPLETE', label: 'OCR & Layout Complete' },
  { key: 'EXTRACTION_COMPLETE', label: 'Test Results Extracted' },
  { key: 'VALIDATED', label: 'Deterministic Normalization' },
  { key: 'ANALYZED', label: 'Longitudinal Trends Updated' },
  { key: 'REPORT_READY', label: 'Report Ready' }
];

const VALID_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png'];

function getExtension(filename = '') {
  const index = filename.lastIndexOf('.');
  return index >= 0 ? filename.substring(index).toLowerCase() : '';
}

function getProcessingStep(status) {
  const normalized = String(status || '').toUpperCase();

  if (normalized === 'REPORT_READY') return 'REPORT_READY';
  if (normalized === 'ANALYZED') return 'ANALYZED';
  if (normalized === 'VALIDATED') return 'VALIDATED';
  if (normalized === 'EXTRACTION_COMPLETE') return 'EXTRACTION_COMPLETE';
  if (normalized === 'OCR_COMPLETE') return 'OCR_COMPLETE';
  if (
    normalized === 'PROCESSING' ||
    normalized === 'PROCESSING_DOCUMENT' ||
    normalized === 'OCR_PROCESSING'
  ) {
    return 'PROCESSING';
  }

  return 'UPLOADED';
}

export default function ReportUploadModal({
  isOpen,
  onClose,
  patientId,
  onUploadSuccess
}) {
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [category, setCategory] = useState('Combined Panel');

  const [uploading, setUploading] = useState(false);
  const [currentStep, setCurrentStep] = useState(null);

  const [resultData, setResultData] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  const fileInputRef = useRef(null);

  /*
   * Reset modal state whenever it is opened.
   * This prevents the previous upload result from appearing
   * when the modal is opened again.
   */
  useEffect(() => {
    if (isOpen) {
      setFile(null);
      setIsDragging(false);
      setCategory('Combined Panel');
      setUploading(false);
      setCurrentStep(null);
      setResultData(null);
      setErrorMsg(null);

      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  }, [isOpen]);

  if (!isOpen) {
    return null;
  }

  const handleDragOver = (event) => {
    event.preventDefault();

    if (!uploading) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (event) => {
    event.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setIsDragging(false);

    if (uploading) {
      return;
    }

    const droppedFile = event.dataTransfer.files?.[0];

    if (droppedFile) {
      handleFileSelected(droppedFile);
    }
  };

  const handleFileSelected = (selectedFile) => {
    if (!selectedFile) {
      return;
    }

    setErrorMsg(null);

    const extension = getExtension(selectedFile.name);

    const validMimeTypes = [
      'application/pdf',
      'image/jpeg',
      'image/png'
    ];

    const isValidType =
      validMimeTypes.includes(selectedFile.type) ||
      VALID_EXTENSIONS.includes(extension);

    if (!isValidType) {
      setFile(null);
      setErrorMsg(
        'Please upload a PDF document or JPG/JPEG/PNG image file.'
      );
      return;
    }

    if (selectedFile.size > MAX_FILE_SIZE) {
      setFile(null);
      setErrorMsg(
        'The selected file is larger than 15 MB. Please upload a smaller report.'
      );
      return;
    }

    setFile(selectedFile);
    setCurrentStep(null);
    setResultData(null);
  };

  const handleUpload = async () => {
    if (!file) {
      setErrorMsg('Please select a report file first.');
      return;
    }

    if (!patientId) {
      setErrorMsg('No patient is currently selected.');
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setErrorMsg(
        'The selected file is larger than 15 MB. Please upload a smaller report.'
      );
      return;
    }

    setUploading(true);
    setErrorMsg(null);
    setResultData(null);
    setCurrentStep('UPLOADED');

    try {
      /*
       * The backend performs the real processing pipeline:
       *
       * upload
       * → validation
       * → PDF/image processing
       * → OCR
       * → extraction
       * → normalization
       * → reference resolution
       * → deterministic status
       * → longitudinal analysis
       */
      setCurrentStep('PROCESSING');

      const response = await patientApi.uploadReport(
        patientId,
        file,
        category
      );

      /*
       * Backend response is the source of truth.
       * Do not simulate backend processing with arbitrary timers.
       */
      const backendStep = getProcessingStep(
        response?.processing_status
      );

      setCurrentStep(
        backendStep === 'UPLOADED'
          ? 'REPORT_READY'
          : backendStep
      );

      setResultData(response);
      setUploading(false);
    } catch (error) {
      console.error('Upload failed:', error);

      const backendDetail =
        error?.response?.data?.detail ||
        error?.response?.data?.message;

      let message = backendDetail;

      if (!message && error?.response?.status === 413) {
        message = 'The uploaded file is too large.';
      }

      if (!message && error?.response?.status === 400) {
        message = 'The report could not be processed. Please check the file and try again.';
      }

      if (!message) {
        message =
          error?.message ||
          'Failed to process the report. Please ensure the server is running.';
      }

      setErrorMsg(message);
      setCurrentStep('FAILED');
      setUploading(false);
      setResultData(null);
    }
  };

  const handleReset = () => {
    if (uploading) {
      return;
    }

    setFile(null);
    setIsDragging(false);
    setCurrentStep(null);
    setResultData(null);
    setErrorMsg(null);

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleClose = () => {
    if (uploading) {
      return;
    }

    handleReset();
    onClose();
  };

  const handleFinish = () => {
    if (resultData && onUploadSuccess) {
      onUploadSuccess(resultData);
    }

    handleReset();
    onClose();
  };

  const currentStepIndex = PROCESSING_STEPS.findIndex(
    (step) => step.key === currentStep
  );

  const extractedTests =
    Number.isFinite(Number(resultData?.total_extracted_tests))
      ? Number(resultData.total_extracted_tests)
      : 0;

  const ocrScore =
    typeof resultData?.ocr_quality?.score === 'number'
      ? resultData.ocr_quality.score
      : null;

  const processingStatus =
    String(resultData?.processing_status || '').toUpperCase();

  const isReportReady =
    processingStatus === 'REPORT_READY' ||
    currentStep === 'REPORT_READY';

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 animate-fade-in">
      <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 max-w-lg w-full overflow-hidden animate-slide-up">

        {/* Header */}
        <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center">
          <div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">
              Upload Diagnostic Report
            </h3>

            <p className="text-xs text-slate-500 mt-0.5">
              Secure OCR extraction & longitudinal analysis for Patient:{' '}
              <span className="font-semibold text-primary">
                {patientId || 'Not selected'}
              </span>
            </p>
          </div>

          <button
            onClick={handleClose}
            disabled={uploading}
            aria-label="Close upload dialog"
            className="p-1.5 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5">

          {!resultData ? (
            <>
              {/* Category Picker */}
              <div>
                <label
                  htmlFor="report-category"
                  className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5"
                >
                  Report Category
                </label>

                <select
                  id="report-category"
                  value={category}
                  onChange={(event) =>
                    setCategory(event.target.value)
                  }
                  disabled={uploading}
                  className="w-full text-xs p-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-none focus:border-primary disabled:opacity-60"
                >
                  <option value="Combined Panel">
                    Combined Diagnostic Panel
                  </option>

                  <option value="Complete Blood Count (CBC)">
                    Complete Blood Count (CBC)
                  </option>

                  <option value="Lipid Profile">
                    Lipid Profile
                  </option>

                  <option value="Liver Function Test (LFT)">
                    Liver Function Test (LFT)
                  </option>

                  <option value="Kidney Function Test (KFT)">
                    Kidney Function Test (KFT)
                  </option>

                  <option value="Thyroid Profile">
                    Thyroid Profile
                  </option>

                  <option value="Diabetes Panel">
                    Diabetes Panel
                  </option>
                </select>
              </div>

              {/* Drag & Drop */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() =>
                  !uploading &&
                  fileInputRef.current?.click()
                }
                className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all ${
                  uploading
                    ? 'pointer-events-none opacity-60'
                    : 'cursor-pointer'
                } ${
                  isDragging
                    ? 'border-primary bg-primary/5 dark:bg-primary/10'
                    : 'border-slate-200 dark:border-slate-700 hover:border-primary/50 bg-slate-50/50 dark:bg-slate-800/30'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
                  className="hidden"
                  disabled={uploading}
                  onChange={(event) => {
                    const selectedFile =
                      event.target.files?.[0];

                    if (selectedFile) {
                      handleFileSelected(selectedFile);
                    }
                  }}
                />

                <div className="w-14 h-14 rounded-full bg-primary/10 text-primary mx-auto flex items-center justify-center mb-3">
                  <UploadCloud size={28} />
                </div>

                <div className="text-sm font-semibold text-slate-800 dark:text-slate-200 break-all">
                  {file
                    ? file.name
                    : 'Choose a file or drag & drop here'}
                </div>

                <p className="text-xs text-slate-400 mt-1">
                  Supported formats: PDF, JPG, JPEG, PNG · Max 15MB
                </p>

                {file && (
                  <div className="mt-3 inline-flex items-center gap-1.5 px-3 py-1 bg-primary/10 text-primary rounded-full text-xs font-medium">
                    <File size={14} />

                    <span>
                      {(file.size / (1024 * 1024)).toFixed(2)} MB
                    </span>
                  </div>
                )}
              </div>

              {/* Selected file actions */}
              {file && !uploading && (
                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={handleReset}
                    className="text-xs font-semibold text-slate-500 hover:text-red-500 transition-colors"
                  >
                    Remove selected file
                  </button>
                </div>
              )}

              {/* Error */}
              {errorMsg && (
                <div className="p-3 rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/50 flex items-start gap-2 text-xs text-red-700 dark:text-red-300">
                  <AlertTriangle
                    size={16}
                    className="shrink-0 mt-0.5"
                  />

                  <span>{errorMsg}</span>
                </div>
              )}

              {/* Processing indicator */}
              {uploading && (
                <div className="space-y-2.5 p-4 bg-slate-50 dark:bg-slate-800/50 rounded-2xl border border-slate-200 dark:border-slate-700">
                  <div className="flex items-center justify-between text-xs font-semibold text-slate-700 dark:text-slate-300">
                    <span className="flex items-center gap-2">
                      <Loader2
                        size={16}
                        className="animate-spin text-primary"
                      />

                      Analyzing Medical Report...
                    </span>

                    <span className="text-primary font-mono">
                      {currentStep || 'PROCESSING'}
                    </span>
                  </div>

                  <div className="space-y-1.5 pt-2">
                    {PROCESSING_STEPS.map((step, index) => {
                      const isDone =
                        currentStepIndex >= 0 &&
                        currentStepIndex > index;

                      const isCurrent =
                        step.key === currentStep;

                      return (
                        <div
                          key={step.key}
                          className="flex items-center gap-2 text-[11px]"
                        >
                          {isDone ? (
                            <CheckCircle2
                              size={13}
                              className="text-emerald-500"
                            />
                          ) : isCurrent ? (
                            <Loader2
                              size={13}
                              className="text-primary animate-spin"
                            />
                          ) : (
                            <div className="w-3.5 h-3.5 rounded-full border border-slate-300 dark:border-slate-600" />
                          )}

                          <span
                            className={
                              isCurrent
                                ? 'font-bold text-primary'
                                : isDone
                                  ? 'text-slate-600 dark:text-slate-400'
                                  : 'text-slate-400'
                            }
                          >
                            {step.label}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </>
          ) : (
            /* Success State */
            <div className="space-y-4 text-center py-2">

              <div className="w-16 h-16 rounded-full bg-emerald-100 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400 mx-auto flex items-center justify-center">
                <CheckCircle2 size={36} />
              </div>

              <div>
                <h4 className="text-base font-bold text-slate-900 dark:text-white">
                  {isReportReady
                    ? 'Report Successfully Analyzed!'
                    : 'Report Processing Complete'}
                </h4>

                <p className="text-xs text-slate-500 mt-1">
                  Report ID:{' '}
                  <span className="font-mono text-slate-700 dark:text-slate-300">
                    {resultData.report_id || 'N/A'}
                  </span>
                </p>
              </div>

              {/* Processing status */}
              {resultData.processing_status && (
                <div className="inline-flex items-center px-3 py-1 rounded-full bg-primary/10 text-primary text-[11px] font-bold">
                  {resultData.processing_status}
                </div>
              )}

              {/* Warning */}
              {resultData.warning && (
                <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/50 flex items-start gap-2 text-left text-xs text-amber-800 dark:text-amber-300">
                  <AlertTriangle
                    size={16}
                    className="shrink-0 mt-0.5 text-amber-600"
                  />

                  <span>{resultData.warning}</span>
                </div>
              )}

              {/* Summary */}
              <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700 text-xs text-left">

                <div>
                  <span className="text-slate-500">
                    Extracted Tests:
                  </span>

                  <div className="text-base font-bold text-slate-900 dark:text-white mt-0.5">
                    {extractedTests} Parameters
                  </div>
                </div>

                <div>
                  <span className="text-slate-500">
                    OCR Quality Score:
                  </span>

                  <div className="text-base font-bold text-slate-900 dark:text-white mt-0.5">
                    {ocrScore !== null
                      ? `${Math.round(ocrScore * 100)}%`
                      : 'N/A'}
                  </div>
                </div>

              </div>

              {/* Low OCR warning */}
              {resultData.ocr_quality?.is_low_quality && (
                <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/50 text-left text-xs text-amber-800 dark:text-amber-300">
                  OCR quality is below the preferred threshold.
                  Please verify extracted values against the
                  original report.
                </div>
              )}

              {/* File hash / provenance */}
              {resultData.file_hash && (
                <div className="text-[10px] text-slate-400 break-all text-left">
                  File fingerprint:{' '}
                  <span className="font-mono">
                    {resultData.file_hash}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 flex justify-end gap-3">

          {!resultData ? (
            <>
              <button
                onClick={handleClose}
                disabled={uploading}
                className="px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>

              <button
                onClick={handleUpload}
                disabled={!file || uploading || !patientId}
                className="px-5 py-2.5 rounded-xl bg-primary hover:bg-primary-hover text-white text-xs font-bold transition-all shadow-md shadow-primary/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {uploading ? (
                  <>
                    <Loader2
                      size={16}
                      className="animate-spin"
                    />

                    <span>Processing...</span>
                  </>
                ) : (
                  <>
                    <span>Extract & Analyze</span>
                    <ArrowRight size={15} />
                  </>
                )}
              </button>
            </>
          ) : (
            <button
              onClick={handleFinish}
              className="w-full py-2.5 rounded-xl bg-primary hover:bg-primary-hover text-white text-xs font-bold transition-all shadow-md shadow-primary/20 cursor-pointer"
            >
              View Analyzed Report
            </button>
          )}
        </div>
      </div>
    </div>
  );
}