
import React, { useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import { authApi } from '../api/authApi';

export default function SignupPage({ onSignup, onLogin, onBackToLogin, onBackToHome }) {
  const [form, setForm] = useState({
    name: '',
    age: '',
    gender: '',
    city: '',
    state: '',
    country: 'India',
    email: '',
    username: '',
    password: '',
    confirmPassword: '',
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const inputClass =
    'w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100';

  const handleChange = (e) => {
    const { name, value } = e.target;

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    if (form.password.length < 8) {
      setError('Password must contain at least 8 characters.');
      return;
    }

    if (new TextEncoder().encode(form.password).length > 72) {
      setError('Password must not exceed 72 UTF-8 bytes.');
      return;
    }

    if (!form.age || Number(form.age) < 1 || Number(form.age) > 120) {
      setError('Please enter a valid age.');
      return;
    }

    try {
      setLoading(true);

      const payload = {
        name: form.name.trim(),
        age: Number(form.age),
        gender: form.gender,
        city: form.city.trim(),
        state: form.state.trim() || null,
        country: form.country.trim() || null,
        email: form.email.trim() || null,
        username: form.username.trim(),
        password: form.password,
      };

      await authApi.signup(payload);

      // Verify that the backend created the session cookie.
      const user = await authApi.me();

      if (!user?.authenticated) {
        throw new Error(
          'Account created, but automatic login failed. Please log in.'
        );
      }

      onSignup(user);

    } catch (err) {
      const detail = err.response?.data?.detail;

      setError(
        typeof detail === 'string'
          ? detail
          : err.message || 'Unable to create your account.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4 py-8">
      <div className="w-full max-w-xl">

        {(onBackToLogin || onLogin || onBackToHome) && (
          <button
            type="button"
            onClick={onBackToLogin || onLogin || onBackToHome}
            className="mb-4 inline-flex items-center gap-2 text-xs font-bold text-slate-600 hover:text-blue-600 transition-all duration-200 group cursor-pointer"
          >
            <div className="w-8 h-8 rounded-xl bg-white border border-slate-200 flex items-center justify-center shadow-sm group-hover:border-blue-300 group-hover:bg-blue-50/50 group-hover:shadow transition-all">
              <ArrowLeft
                size={16}
                className="text-slate-500 group-hover:text-blue-600 group-hover:-translate-x-0.5 transition-all duration-200"
              />
            </div>
            <span>{onBackToLogin || onLogin ? 'Back to Sign In' : 'Back to Home'}</span>
          </button>
        )}

        <div className="w-full bg-white rounded-2xl shadow-lg border border-slate-200 p-7">

        <div className="text-center mb-7">
          <h1 className="text-2xl font-bold text-slate-900">
            Create Patient Account
          </h1>

          <p className="text-sm text-slate-500 mt-2">
            Register to securely access your medical reports.
          </p>
        </div>

        {error && (
          <div
            role="alert"
            className="mb-5 p-3 rounded-lg bg-red-50 text-red-700 text-sm"
          >
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">

          <div>
            <label className="block text-sm font-medium mb-1">
              Full Name
            </label>

            <input
              className={inputClass}
              name="name"
              value={form.name}
              onChange={handleChange}
              required
              minLength={2}
              autoComplete="name"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">
                Age
              </label>

              <input
                className={inputClass}
                type="number"
                name="age"
                value={form.age}
                onChange={handleChange}
                min="1"
                max="120"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                Gender
              </label>

              <select
                className={inputClass}
                name="gender"
                value={form.gender}
                onChange={handleChange}
                required
              >
                <option value="">Select</option>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Other">Other</option>
                <option value="Prefer not to say">
                  Prefer not to say
                </option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">
                City
              </label>

              <input
                className={inputClass}
                name="city"
                value={form.city}
                onChange={handleChange}
                required
                autoComplete="address-level2"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">
                State
              </label>

              <input
                className={inputClass}
                name="state"
                value={form.state}
                onChange={handleChange}
                autoComplete="address-level1"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Country
            </label>

            <input
              className={inputClass}
              name="country"
              value={form.country}
              onChange={handleChange}
              autoComplete="country-name"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Email
            </label>

            <input
              className={inputClass}
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              autoComplete="email"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Username
            </label>

            <input
              className={inputClass}
              name="username"
              value={form.username}
              onChange={handleChange}
              minLength={4}
              required
              autoComplete="username"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Password
            </label>

            <input
              className={inputClass}
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              minLength={8}
              required
              autoComplete="new-password"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Confirm Password
            </label>

            <input
              className={inputClass}
              type="password"
              name="confirmPassword"
              value={form.confirmPassword}
              onChange={handleChange}
              required
              autoComplete="new-password"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-blue-700 hover:bg-blue-800 text-white py-3 font-semibold disabled:opacity-50"
          >
            {loading ? 'Creating Account...' : 'Create Account'}
          </button>

        </form>

        <p className="text-center text-sm text-slate-600 mt-6">
          Already registered?{' '}

          <button
            type="button"
            onClick={onBackToLogin}
            disabled={loading}
            className="text-blue-700 font-semibold hover:underline"
          >
            Login
          </button>
        </p>

        </div>
      </div>
    </div>
  );
}
