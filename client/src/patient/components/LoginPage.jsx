
import React, { useState } from 'react';

import {
  LockKeyhole,
  User,
  Loader2,
  ShieldCheck,
  Eye,
  EyeOff,
} from 'lucide-react';

import authApi from '../api/authApi';

export default function LoginPage({ onLogin, onSignup }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();

    setError('');

    if (!username.trim()) {
      setError('Please enter your username.');
      return;
    }

    if (!password) {
      setError('Please enter your password.');
      return;
    }

    try {
      setLoading(true);

      const result = await authApi.login(
        username.trim(),
        password
      );

      if (!result?.authenticated) {
        throw new Error('Authentication failed.');
      }

      if (onLogin) {
        onLogin(result);
      }

    } catch (err) {
      const message =
        err?.response?.data?.detail ||
        err?.message ||
        'Invalid username or password.';

      setError(message);

    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">

      <div className="w-full max-w-md">

        <div className="bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">

          {/* Header */}
          <div className="px-8 pt-8 pb-6 text-center">

            <div className="mx-auto mb-4 w-14 h-14 rounded-2xl bg-blue-600 flex items-center justify-center">

              <ShieldCheck className="w-7 h-7 text-white" />

            </div>

            <h1 className="text-2xl font-bold text-slate-900">
              Patient Portal
            </h1>

            <p className="mt-2 text-sm text-slate-500">
              Sign in to securely access your medical reports
              and patient insights.
            </p>

          </div>


          {/* Form */}
          <form
            onSubmit={handleSubmit}
            className="px-8 pb-8"
          >

            {/* Error */}
            {error && (
              <div
                role="alert"
                className="mb-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
              >
                {error}
              </div>
            )}


            {/* Username */}
            <div className="mb-5">

              <label
                htmlFor="patient-username"
                className="block text-sm font-medium text-slate-700 mb-2"
              >
                Username
              </label>

              <div className="relative">

                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />

                <input
                  id="patient-username"
                  type="text"
                  autoComplete="username"
                  value={username}
                  onChange={(event) =>
                    setUsername(event.target.value)
                  }
                  placeholder="Enter your username"
                  disabled={loading}
                  required
                  className="w-full rounded-lg border border-slate-300 bg-white pl-10 pr-4 py-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:bg-slate-100"
                />

              </div>

            </div>


            {/* Password */}
            <div className="mb-6">

              <label
                htmlFor="patient-password"
                className="block text-sm font-medium text-slate-700 mb-2"
              >
                Password
              </label>

              <div className="relative">

                <LockKeyhole className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />

                <input
                  id="patient-password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) =>
                    setPassword(event.target.value)
                  }
                  placeholder="Enter your password"
                  disabled={loading}
                  required
                  className="w-full rounded-lg border border-slate-300 bg-white pl-10 pr-12 py-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:bg-slate-100"
                />

                <button
                  type="button"
                  onClick={() =>
                    setShowPassword((value) => !value)
                  }
                  disabled={loading}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  aria-label={
                    showPassword
                      ? 'Hide password'
                      : 'Show password'
                  }
                >

                  {showPassword ? (
                    <EyeOff className="w-5 h-5" />
                  ) : (
                    <Eye className="w-5 h-5" />
                  )}

                </button>

              </div>

            </div>


            {/* Sign In Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium py-3 transition flex items-center justify-center gap-2"
            >

              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Signing in...
                </>
              ) : (
                'Sign In'
              )}

            </button>


            {/* Signup Link */}
            <div className="mt-6 text-center">

              <p className="text-sm text-slate-600">

                Don't have an account?{' '}

                <button
                  type="button"
                  onClick={onSignup}
                  disabled={loading}
                  className="text-blue-600 font-semibold hover:text-blue-800 hover:underline disabled:opacity-50"
                >
                  Create Account
                </button>

              </p>

            </div>

            {/* Security Message */}
            <div className="mt-6 flex items-center justify-center gap-2 text-xs text-slate-400">

              <LockKeyhole className="w-3.5 h-3.5" />

              <span>
                Your session is protected by secure authentication.
              </span>

            </div>

          </form>

        </div>

      </div>

    </div>
  );
}
