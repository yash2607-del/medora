
import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import {
  Send,
  User,
  Stethoscope,
  Sparkles,
  ShieldCheck,
  AlertCircle,
} from 'lucide-react';

import { patientApi } from '../api/patientApi';

const QUICK_QUESTIONS = [
  'What changed in my latest report?',
  'Which results are abnormal?',
  'Has my hemoglobin improved?',
  'What has remained abnormal?',
  'Explain my latest report.',
];

// Convert simple React children into text for status detection.
const getChildrenText = (children) =>
  React.Children.toArray(children)
    .map((child) =>
      typeof child === 'string' || typeof child === 'number'
        ? String(child)
        : ''
    )
    .join('')
    .trim();

// Markdown renderer for assistant responses.
function AssistantMarkdown({ content }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children }) => (
          <p className="mb-3 last:mb-0 leading-7">
            {children}
          </p>
        ),

        strong: ({ children }) => {
          const value = getChildrenText(children).toUpperCase();

          if (
            ['LOW', 'HIGH', 'NORMAL', 'CRITICAL', 'ABNORMAL']
              .includes(value)
          ) {
            const styles = {
              LOW: 'bg-amber-100 text-amber-800 border-amber-200',
              HIGH: 'bg-red-100 text-red-800 border-red-200',
              NORMAL: 'bg-emerald-100 text-emerald-800 border-emerald-200',
              CRITICAL: 'bg-red-100 text-red-800 border-red-200',
              ABNORMAL: 'bg-orange-100 text-orange-800 border-orange-200',
            };

            return (
              <span
                className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-bold ${styles[value]}`}
              >
                {value}
              </span>
            );
          }

          return (
            <strong className="font-bold text-slate-900">
              {children}
            </strong>
          );
        },

        em: ({ children }) => (
          <em className="italic text-slate-700">
            {children}
          </em>
        ),

        h1: ({ children }) => (
          <h1 className="text-lg font-bold text-slate-900 mt-4 mb-2">
            {children}
          </h1>
        ),

        h2: ({ children }) => (
          <h2 className="text-base font-bold text-slate-900 mt-4 mb-2">
            {children}
          </h2>
        ),

        h3: ({ children }) => (
          <h3 className="text-sm font-bold text-slate-900 mt-3 mb-2">
            {children}
          </h3>
        ),

        ol: ({ children }) => (
          <ol className="list-decimal pl-6 space-y-2 mb-3 marker:font-semibold marker:text-slate-500">
            {children}
          </ol>
        ),

        ul: ({ children }) => (
          <ul className="list-disc pl-6 space-y-2 mb-3 marker:text-slate-500">
            {children}
          </ul>
        ),

        li: ({ children }) => (
          <li className="pl-1 leading-7">
            {children}
          </li>
        ),

        blockquote: ({ children }) => (
          <blockquote className="border-l-4 border-blue-300 pl-4 py-1 my-3 text-slate-600 bg-blue-50/50 rounded-r-lg">
            {children}
          </blockquote>
        ),

        hr: () => (
          <hr className="my-4 border-slate-200" />
        ),

        table: ({ children }) => (
          <div className="overflow-x-auto my-4 rounded-lg border border-slate-200">
            <table className="w-full text-left text-sm border-collapse">
              {children}
            </table>
          </div>
        ),

        thead: ({ children }) => (
          <thead className="bg-slate-100">
            {children}
          </thead>
        ),

        th: ({ children }) => (
          <th className="px-3 py-2 border-b border-slate-200 font-bold text-slate-800">
            {children}
          </th>
        ),

        td: ({ children }) => (
          <td className="px-3 py-2 border-b border-slate-100">
            {children}
          </td>
        ),

        code: ({ children }) => (
          <code className="bg-slate-200 text-slate-800 px-1.5 py-0.5 rounded text-xs font-mono">
            {children}
          </code>
        ),

        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 underline underline-offset-2"
          >
            {children}
          </a>
        ),
      }}
    >
      {content || ''}
    </ReactMarkdown>
  );
}

export default function PatientChatBox({
  patientId,
  reportId,
  onOpenEvidence,
}) {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      sender: 'bot',
      text:
        'Hello! I am your personal report assistant. I can help explain your personal test results, answer questions about recent changes, or identify what remained abnormal across your reports. What would you like to know?',
      evidence: [],
      timestamp: new Date(),
    },
  ]);

  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Automatically scroll to the newest message.
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: 'smooth',
      block: 'end',
    });
  }, [messages, loading]);

  // Send a patient-specific question.
  const handleSend = async (textToSend) => {
    const query = String(textToSend ?? input).trim();

    if (!query || !patientId || loading) {
      return;
    }

    const userMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: query,
      evidence: [],
      timestamp: new Date(),
    };

    setMessages((previous) => [
      ...previous,
      userMessage,
    ]);

    setInput('');
    setLoading(true);

    try {
      const response = await patientApi.chat(
        patientId,
        query,
        reportId || null
      );

      const answer =
        response?.answer ||
        'I could not generate an answer from the available patient records.';

      const botMessage = {
        id: `bot-${Date.now()}`,
        sender: 'bot',
        text: answer,
        evidence: Array.isArray(response?.evidence)
          ? response.evidence
          : [],
        disclaimer: response?.disclaimer || null,
        timestamp: new Date(),
      };

      setMessages((previous) => [
        ...previous,
        botMessage,
      ]);
    } catch (error) {
      console.error('Patient chat failed:', error);

      const backendMessage =
        error?.response?.data?.detail;

      const errorMessage = {
        id: `error-${Date.now()}`,
        sender: 'bot',
        text:
          backendMessage ||
          'I was unable to retrieve your patient records at this moment. Please verify that the patient report service is available and try again.',
        evidence: [],
        isError: true,
        timestamp: new Date(),
      };

      setMessages((previous) => [
        ...previous,
        errorMessage,
      ]);
    } finally {
      setLoading(false);

      requestAnimationFrame(() => {
        inputRef.current?.focus();
      });
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();

      if (!loading) {
        handleSend();
      }
    }
  };

  const handleEvidenceClick = (evidence) => {
    if (typeof onOpenEvidence === 'function') {
      onOpenEvidence(evidence);
    }
  };

  return (
    <div className="flex flex-col h-[min(650px,calc(100vh-180px))] min-h-[420px] bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">

      {/* Header */}
      <div className="p-4 border-b border-slate-100 bg-slate-50/70 flex items-center justify-between gap-3 shrink-0">

        <div className="flex items-center gap-3 min-w-0">

          <div className="w-10 h-10 rounded-full bg-primary/10 text-primary flex items-center justify-center shrink-0">
            <Stethoscope size={20} />
          </div>

          <div className="min-w-0">

            <h4 className="font-bold text-slate-900 text-sm">
              Patient Report Assistant
            </h4>

            <span className="text-xs text-slate-500">
              Grounded exclusively in your records
              {patientId ? ` (${patientId})` : ''}
            </span>

          </div>
        </div>

        <div className="flex items-center gap-1.5 text-[10px] sm:text-xs text-emerald-700 bg-emerald-50 px-2.5 py-1.5 rounded-full font-medium border border-emerald-200/70 shrink-0">

          <ShieldCheck size={13} />

          <span>Private Patient Scope</span>

        </div>
      </div>


      {/* Messages */}
      <div
        className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-5 space-y-6"
        aria-live="polite"
      >

        {messages.map((message) => {
          const isUser = message.sender === 'user';

          return (
            <div
              key={message.id}
              className={`flex gap-3 ${
                isUser ? 'flex-row-reverse' : 'flex-row'
              } animate-slide-up`}
            >

              {/* Avatar */}
              <div
                className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 ${
                  isUser
                    ? 'bg-primary text-white'
                    : message.isError
                      ? 'bg-red-50 text-red-600'
                      : 'bg-slate-100 text-primary'
                }`}
              >

                {isUser ? (
                  <User size={17} />
                ) : message.isError ? (
                  <AlertCircle size={17} />
                ) : (
                  <Stethoscope size={17} />
                )}

              </div>


              <div
                className={`max-w-[92%] sm:max-w-[88%] min-w-0 flex flex-col gap-2 ${
                  isUser ? 'items-end' : 'items-start'
                }`}
              >

                {/* Message bubble */}
                <div
                  className={`px-4 py-3.5 sm:px-5 sm:py-4 rounded-2xl text-sm leading-7 break-words ${
                    isUser
                      ? 'bg-primary text-white rounded-tr-none'
                      : message.isError
                        ? 'bg-red-50 text-red-700 rounded-tl-none border border-red-200'
                        : 'bg-slate-50 text-slate-800 rounded-tl-none border border-slate-200/70'
                  }`}
                >

                  {isUser ? (
                    <p className="whitespace-pre-wrap">
                      {message.text}
                    </p>
                  ) : message.isError ? (
                    <p className="whitespace-pre-wrap">
                      {message.text}
                    </p>
                  ) : (
                    <AssistantMarkdown content={message.text} />
                  )}

                </div>


                {/* Disclaimer */}
                {!isUser && message.disclaimer && (
                  <div className="flex items-start gap-2 max-w-full text-xs text-slate-500 px-1">

                    <AlertCircle
                      size={14}
                      className="shrink-0 mt-0.5"
                    />

                    <span>
                      {message.disclaimer}
                    </span>

                  </div>
                )}


                {/* Evidence */}
                {!isUser &&
                  Array.isArray(message.evidence) &&
                  message.evidence.length > 0 && (

                    <div className="flex flex-wrap gap-2 pt-1">

                      <span className="w-full text-xs text-slate-500 flex items-center gap-1.5">

                        <ShieldCheck
                          size={13}
                          className="text-primary"
                        />

                        Verified Evidence

                      </span>

                      {message.evidence.map((evidence, index) => {
                        const testName =
                          evidence?.test_name || 'Test Result';

                        const value =
                          evidence?.current_value ??
                          evidence?.value ??
                          'N/A';

                        const unit = evidence?.unit || '';

                        const status =
                          evidence?.status || 'UNKNOWN';

                        const normalizedStatus =
                          String(status).toUpperCase();

                        const statusStyle =
                          normalizedStatus === 'LOW'
                            ? 'bg-amber-50 text-amber-800 border-amber-200'
                            : normalizedStatus === 'HIGH' ||
                                normalizedStatus === 'CRITICAL'
                              ? 'bg-red-50 text-red-800 border-red-200'
                              : normalizedStatus === 'NORMAL'
                                ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                                : 'bg-slate-50 text-slate-700 border-slate-200';

                        return (
                          <button
                            type="button"
                            key={`${testName}-${index}`}
                            onClick={() =>
                              handleEvidenceClick(evidence)
                            }
                            className="flex flex-wrap items-center gap-1.5 text-xs px-3 py-2 rounded-lg border bg-white hover:border-primary/50 hover:bg-primary/5 transition-colors cursor-pointer text-left"
                            title="View source evidence and provenance"
                          >

                            <span className="font-semibold text-slate-800">
                              {testName}:
                            </span>

                            <span className="text-slate-700">
                              {value} {unit}
                            </span>

                            <span
                              className={`px-1.5 py-0.5 rounded border text-[10px] font-bold ${statusStyle}`}
                            >
                              {status}
                            </span>

                          </button>
                        );
                      })}

                    </div>
                  )}


                {/* Timestamp */}
                <span
                  className={`text-[10px] text-slate-400 px-1 ${
                    isUser ? 'text-right' : 'text-left'
                  }`}
                >
                  {message.timestamp?.toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>

              </div>

            </div>
          );
        })}


        {/* Loading indicator */}
        {loading && (
          <div className="flex items-center gap-2 text-sm text-slate-500 p-2">

            <Sparkles
              size={16}
              className="text-primary animate-spin"
            />

            <span>
              Analyzing your personal records...
            </span>

          </div>
        )}

        <div ref={messagesEndRef} />

      </div>


      {/* Suggested questions */}
      {messages.length === 1 && !loading && (

        <div className="p-4 border-t border-slate-100 bg-slate-50/70 shrink-0">

          <div className="text-xs font-semibold text-slate-500 mb-3">
            Suggested Questions
          </div>

          <div className="flex flex-wrap gap-2">

            {QUICK_QUESTIONS.map((question) => (

              <button
                type="button"
                key={question}
                onClick={() => handleSend(question)}
                disabled={!patientId || loading}
                className="text-xs px-3 py-2 rounded-xl border border-slate-200 bg-white text-slate-700 hover:border-primary/50 hover:bg-primary/5 transition-all text-left cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {question}
              </button>

            ))}

          </div>

        </div>
      )}


      {/* Input */}
      <div className="p-3 sm:p-4 border-t border-slate-100 bg-white flex items-center gap-2 shrink-0">

        <input
          ref={inputRef}
          type="text"
          placeholder={
            patientId
              ? 'Ask a question about your reports...'
              : 'Select a patient first...'
          }
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={!patientId || loading}
          className="flex-1 min-w-0 text-sm p-3.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/10 disabled:opacity-60 disabled:cursor-not-allowed"
        />

        <button
          type="button"
          onClick={() => handleSend()}
          disabled={!input.trim() || !patientId || loading}
          aria-label="Send patient question"
          className="p-3.5 rounded-xl bg-primary hover:bg-primary-hover text-white transition-all shadow-md shadow-primary/20 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer shrink-0"
        >

          {loading ? (
            <Sparkles
              size={18}
              className="animate-spin"
            />
          ) : (
            <Send size={18} />
          )}

        </button>

      </div>

    </div>
  );
}
