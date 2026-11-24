
import React, { useEffect, useState } from 'react';

import authApi from './patient/api/authApi';
import LoginPage from './patient/components/LoginPage';
import SignupPage from './patient/components/SignupPage';
import AssistantPage from './pages/AssistantPage';
import PatientDashboard from './patient/pages/PatientDashboard';

import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import { X, FileText } from 'lucide-react';

import {
  FaFlask,
  FaMapMarkerAlt,
  FaHome,
  FaArrowRight,
} from 'react-icons/fa';


function App() {
  // Main application navigation
  const [view, setView] = useState('home');

  // Healthcare assistant state
  const [isOpen, setIsOpen] = useState(false);
  const [initialQuery, setInitialQuery] = useState('');

  // Authentication state
  const [authLoading, setAuthLoading] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);

  // Login / signup navigation
  const [authView, setAuthView] = useState('login');


  // --------------------------------------------------
  // CHECK EXISTING PATIENT SESSION
  // --------------------------------------------------

  useEffect(() => {
    let mounted = true;

    const checkAuthentication = async () => {
      try {
        const result = await authApi.me();

        if (!mounted) return;

        if (result?.authenticated) {
          setAuthenticated(true);
          setCurrentUser(result);
        } else {
          setAuthenticated(false);
          setCurrentUser(null);
        }
      } catch (error) {
        console.error('Authentication check failed:', error);

        if (mounted) {
          setAuthenticated(false);
          setCurrentUser(null);
        }
      } finally {
        if (mounted) {
          setAuthLoading(false);
        }
      }
    };

    checkAuthentication();

    return () => {
      mounted = false;
    };
  }, []);


  // --------------------------------------------------
  // NAVIGATION
  // --------------------------------------------------

  const openPatientPortal = () => {
    setIsOpen(false);
    setAuthView('login');
    setView('patient');
  };

  const openHealthcareAssistant = () => {
    setView('home');
    setIsOpen(false);
  };


  // --------------------------------------------------
  // LOGIN
  // --------------------------------------------------

  const handleLogin = (user) => {
    setAuthenticated(true);
    setCurrentUser(user);
    setAuthView('login');
    setView('patient');
  };


  // --------------------------------------------------
  // SIGNUP
  // --------------------------------------------------

  const handleSignup = (user) => {
    setAuthenticated(true);
    setCurrentUser(user);
    setAuthView('login');
    setView('patient');
  };


  // --------------------------------------------------
  // LOGOUT
  // --------------------------------------------------

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      setAuthenticated(false);
      setCurrentUser(null);
      setAuthView('login');
      setView('home');
    }
  };


  // --------------------------------------------------
  // AUTHENTICATION LOADING SCREEN
  // --------------------------------------------------

  if (authLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">

          <div className="w-9 h-9 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />

          <p className="text-sm text-gray-500">
            Checking your session...
          </p>

        </div>
      </div>
    );
  }


  // --------------------------------------------------
  // PATIENT PORTAL
  // --------------------------------------------------

  if (view === 'patient') {

    // Not authenticated: show login or signup
    if (!authenticated) {
      return (
        <>
          {authView === 'signup' ? (
            <SignupPage
              onSignup={handleSignup}
              onLogin={() => setAuthView('login')}
              onBackToLogin={() => setAuthView('login')}
              onBackToHome={openHealthcareAssistant}
            />
          ) : (
            <LoginPage
              onLogin={handleLogin}
              onSignup={() => setAuthView('signup')}
              onBackToHome={openHealthcareAssistant}
            />
          )}

          <ToastContainer
            position="top-right"
            theme="colored"
            autoClose={3000}
            hideProgressBar={false}
          />
        </>
      );
    }

    // Authenticated: show patient dashboard
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col font-sans">

        <PatientDashboard
          onBackToHome={openHealthcareAssistant}
          onLogout={handleLogout}
          currentUser={currentUser}
        />

        <ToastContainer
          position="top-right"
          theme="colored"
          autoClose={3000}
          hideProgressBar={false}
        />

      </div>
    );
  }


  // --------------------------------------------------
  // PUBLIC HOMEPAGE
  // --------------------------------------------------

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col font-sans">

      {/* HEADER */}
      <header className="bg-white shadow-sm py-4 px-8 flex justify-between items-center z-10 relative">

        <div className="flex items-center gap-3">

          <img
            src="/lords-path-logo.png"
            alt="Lord's Pathology Logo"
            className="w-12 h-12 object-contain"
          />

          <h1 className="text-2xl font-extrabold text-black">
            Lord's Pathology
          </h1>

        </div>


        {/* DESKTOP NAVIGATION */}
        <nav className="hidden md:flex gap-8 text-gray-600 font-medium items-center">

          <button
            onClick={openHealthcareAssistant}
            className={`hover:text-black transition-colors cursor-pointer ${
              view === 'home' ? 'font-bold text-black' : ''
            }`}
          >
            Home
          </button>


          <button
            onClick={openPatientPortal}
            className="px-4 py-2 rounded-full text-xs font-bold bg-primary text-white hover:bg-primary-hover shadow-sm transition-all flex items-center gap-1.5 cursor-pointer"
          >
            <FileText size={14} />

            <span>
              My Reports / Patient Portal
            </span>
          </button>


          <a
            href="#"
            className="hover:text-black transition-colors"
          >
            Book a Test
          </a>


          <a
            href="#"
            className="hover:text-black transition-colors"
          >
            Locate Centre
          </a>


          <a
            href="#"
            className="hover:text-black transition-colors"
          >
            Contact Us
          </a>

        </nav>


        {/* MOBILE NAVIGATION */}
        <div className="md:hidden">

          <button
            onClick={openPatientPortal}
            className="px-3 py-1.5 rounded-full text-xs font-bold bg-primary text-white flex items-center gap-1 cursor-pointer"
          >
            <FileText size={13} />

            <span>
              My Reports
            </span>
          </button>

        </div>

      </header>


      {/* MAIN HOMEPAGE CONTENT */}
      <main className="flex-1 flex flex-col md:flex-row relative">

        <div className="flex-1 px-8 md:px-16 py-12 md:py-24 flex flex-col justify-center max-w-4xl">

          <h2 className="text-4xl lg:text-5xl font-extrabold text-black leading-tight mb-6 tracking-tight">

            Accurate Diagnostics,{' '}

            <br className="hidden sm:block" />

            Delivered <span>Right to You.</span>

          </h2>


          <p className="text-base md:text-lg text-gray-600 mb-10 leading-relaxed max-w-2xl pr-4">

            Experience world-class care with Lord's Pathology.
            Book home collections, locate 70+ centres, track
            longitudinal health trends, and check pricing instantly
            with our 24/7 AI Assistant.

          </p>


          {/* FEATURES */}
          <div className="flex flex-wrap gap-6 mb-12">

            <div className="flex items-center gap-3 bg-white p-4 rounded-xl shadow-sm border border-gray-100">

              <div className="bg-blue-50 p-3 rounded-full text-blue-600">
                <FaFlask size={24} />
              </div>

              <span className="font-semibold text-gray-700">
                100+ Tests
              </span>

            </div>


            <div className="flex items-center gap-3 bg-white p-4 rounded-xl shadow-sm border border-gray-100">

              <div className="bg-green-50 p-3 rounded-full text-green-600">
                <FaMapMarkerAlt size={24} />
              </div>

              <span className="font-semibold text-gray-700">
                72 Centres
              </span>

            </div>


            <div className="flex items-center gap-3 bg-white p-4 rounded-xl shadow-sm border border-gray-100">

              <div className="bg-purple-50 p-3 rounded-full text-purple-600">
                <FaHome size={24} />
              </div>

              <span className="font-semibold text-gray-700">
                Home Collection
              </span>

            </div>

          </div>


          {/* HOMEPAGE ACTION BUTTONS */}
          <div className="flex flex-wrap items-center gap-4">

            <button
              onClick={openPatientPortal}
              className="bg-primary hover:bg-primary-hover text-white font-bold py-4 px-8 rounded-full shadow-lg transition-transform hover:-translate-y-1 w-fit flex items-center gap-2 cursor-pointer"
            >

              <FileText size={18} />

              <span>
                View Patient Reports
              </span>

              <FaArrowRight />

            </button>


            <button
              className="bg-white hover:bg-gray-100 text-slate-800 font-bold py-4 px-8 rounded-full shadow border border-gray-200 transition-transform hover:-translate-y-1 w-fit flex items-center gap-2 cursor-pointer"
            >
              Book Home Collection
            </button>

          </div>

        </div>


        {/* RIGHT SIDE DECORATIVE AREA */}
        <div className="hidden md:flex flex-1 items-center justify-center p-12 relative overflow-hidden">

          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-blue-100 rounded-full blur-3xl opacity-50" />

          <div className="absolute top-1/4 right-1/4 w-64 h-64 bg-purple-100 rounded-full blur-3xl opacity-50" />

        </div>

      </main>


      {/* HEALTHCARE ASSISTANT FLOATING CHAT */}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col items-end">

        {isOpen && (
          <div className="w-100 h-187.5 max-h-[calc(100vh-180px)] max-w-[95vw] mb-4 bg-background border border-border rounded-2xl shadow-2xl overflow-hidden flex flex-col animate-slide-up">

            <AssistantPage
              initialQuery={initialQuery}
              setInitialQuery={setInitialQuery}
            />

          </div>
        )}


        <div className="flex items-center gap-3 relative">

          {!isOpen && (
            <div className="flex items-center animate-bounce mr-2">

              <div className="bg-white text-primary text-sm font-bold px-4 py-2 rounded-2xl shadow-lg border border-border relative">

                Chat with us!

                <div className="absolute top-1/2 -right-2 -translate-y-1/2 w-0 h-0 border-y-8 border-y-transparent border-l-8 border-l-border" />

                <div className="absolute top-1/2 -right-1.75 -translate-y-1/2 w-0 h-0 border-y-[7px] border-y-transparent border-l-[7px] border-l-white" />

              </div>

            </div>
          )}


          <button
            onClick={() => setIsOpen(!isOpen)}
            aria-label={
              isOpen
                ? 'Close healthcare assistant'
                : 'Open healthcare assistant'
            }
            className="w-14 h-14 bg-primary hover:bg-primary-hover text-white rounded-full flex items-center justify-center shadow-lg transition-transform hover:scale-105 cursor-pointer relative z-10"
          >

            {isOpen ? (
              <X size={24} />
            ) : (
              <div className="w-full h-full rounded-full bg-white flex items-center justify-center overflow-hidden border-2 border-primary shadow-sm p-1">

                <img
                  src="/lords-path-logo.png"
                  alt="Chat"
                  className="w-10 h-10 object-contain"
                />

              </div>
            )}

          </button>

        </div>

      </div>


      {/* GLOBAL TOAST NOTIFICATIONS */}
      <ToastContainer
        position="top-right"
        theme="colored"
        autoClose={3000}
        hideProgressBar={false}
      />

    </div>
  );
}


export default App;
