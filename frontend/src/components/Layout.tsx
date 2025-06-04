import React from 'react';
import { Link, Outlet } from 'react-router-dom';

const Layout: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-gray-900 to-slate-800 text-white font-sans relative overflow-hidden">
      {/* Enhanced backdrop blur effects spanning entire screen */}
      <div className="fixed inset-0 pointer-events-none z-0">
        {/* Primary animated orbs */}
        <div className="absolute -top-20 -left-20 w-96 h-96 bg-cyan-500/8 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute top-1/4 right-1/4 w-80 h-80 bg-blue-500/6 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }}></div>
        <div className="absolute bottom-1/3 left-1/3 w-72 h-72 bg-purple-500/7 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '2s' }}></div>
        <div className="absolute -bottom-16 -right-16 w-88 h-88 bg-emerald-500/6 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '3s' }}></div>
        
        
        {/* Subtle grid overlay */}
        <div className="absolute inset-0 opacity-[0.02]" style={{
          backgroundImage: `radial-gradient(circle at 1px 1px, rgba(255,255,255,0.3) 1px, transparent 0)`,
          backgroundSize: '40px 40px'
        }}></div>
      </div>

      {/* Header with glassmorphism effect */}
      <header className="relative backdrop-blur-xl bg-slate-900/60 border-b border-cyan-500/20 shadow-2xl z-20">
        <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/5 via-blue-500/3 to-purple-500/5"></div>
        <div className="container mx-auto px-6 relative z-30">
          {/* Enhanced brand section */}
          <div className="flex items-center justify-between py-8 border-b border-cyan-500/20">
            <div className="flex items-center space-x-6">
              <div className="relative group">
                <div className="w-16 h-16 bg-gradient-to-br from-cyan-400 via-blue-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-2xl transform group-hover:scale-110 transition-all duration-500 cursor-pointer">
                  <span className="text-white font-bold text-4xl drop-shadow-lg">⚽</span>
                  <div className="absolute inset-0 bg-gradient-to-br from-white/30 to-transparent rounded-2xl"></div>
                  <div className="absolute inset-0 border border-white/20 rounded-2xl"></div>
                </div>
                <div className="absolute -inset-2 bg-gradient-to-r from-cyan-400/20 to-purple-600/20 rounded-3xl blur-lg opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
              </div>
              <div>
                <h1 className="font-bold text-5xl bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text  drop-shadow-2xl">
                  Football Simulation
                </h1>
                <p className="text-cyan-300 text-base font-medium tracking-wider mt-2 opacity-90">Premier League Dashboard</p>
              </div>
            </div>
            
            {/* Enhanced live status indicator */}
            <div className="flex items-center space-x-3 bg-emerald-500/20 backdrop-blur-sm px-5 py-3 rounded-2xl border border-emerald-400/40 shadow-xl">
              <div className="relative">
                <div className="w-3 h-3 bg-emerald-400 rounded-full animate-pulse shadow-lg"></div>
                <div className="absolute inset-0 w-3 h-3 bg-emerald-400 rounded-full animate-ping"></div>
              </div>
            </div>
          </div>

          {/* Enhanced navigation */}
          <nav className="py-8">
            <ul className="flex items-center justify-center space-x-4">
              <li>
                <Link 
                  to="/" 
                  className="group relative font-bold text-lg px-10 py-5 rounded-2xl transition-all duration-500 hover:bg-cyan-500/20 hover:scale-105 hover:shadow-2xl border border-transparent hover:border-cyan-400/50 backdrop-blur-sm"
                >
                  <span className="relative z-10 text-white group-hover:text-cyan-300 transition-all duration-300 flex items-center space-x-3">
                    <span className="text-2xl">🏠</span>
                    <span>Home</span>
                  </span>
                  <div className="absolute bottom-3 left-1/2 w-0 h-1 bg-gradient-to-r from-cyan-400 to-blue-400 transition-all duration-300 group-hover:w-4/5 group-hover:left-[10%] rounded-full shadow-lg"></div>
                </Link>
              </li>
              <li>
                <Link 
                  to="/league-table" 
                  className="group relative font-bold text-lg px-10 py-5 rounded-2xl transition-all duration-500 hover:bg-blue-500/20 hover:scale-105 hover:shadow-2xl border border-transparent hover:border-blue-400/50 backdrop-blur-sm"
                >
                  <span className="relative z-10 text-white group-hover:text-blue-300 transition-all duration-300 flex items-center space-x-3">
                    <span className="text-2xl">📊</span>
                    <span>League Table</span>
                  </span>
                  <div className="absolute bottom-3 left-1/2 w-0 h-1 bg-gradient-to-r from-blue-400 to-indigo-400 transition-all duration-300 group-hover:w-4/5 group-hover:left-[10%] rounded-full shadow-lg"></div>
                </Link>
              </li>
              <li>
                <Link 
                  to="/transfers" 
                  className="group relative font-bold text-lg px-10 py-5 rounded-2xl transition-all duration-500 hover:bg-emerald-500/20 hover:scale-105 hover:shadow-2xl border border-transparent hover:border-emerald-400/50 backdrop-blur-sm"
                >
                  <span className="relative z-10 text-white group-hover:text-emerald-300 transition-all duration-300 flex items-center space-x-3">
                    <span className="text-2xl">💰</span>
                    <span>Transfers</span>
                  </span>
                  <div className="absolute bottom-3 left-1/2 w-0 h-1 bg-gradient-to-r from-emerald-400 to-teal-400 transition-all duration-300 group-hover:w-4/5 group-hover:left-[10%] rounded-full shadow-lg"></div>
                </Link>
              </li>
              <li>
                <Link 
                  to="/matches" 
                  className="group relative font-bold text-lg px-10 py-5 rounded-2xl transition-all duration-500 hover:bg-purple-500/20 hover:scale-105 hover:shadow-2xl border border-transparent hover:border-purple-400/50 backdrop-blur-sm"
                >
                  <span className="relative z-10 text-white group-hover:text-purple-300 transition-all duration-300 flex items-center space-x-3">
                    <span className="text-2xl">⚽</span>
                    <span>Matches</span>
                  </span>
                  <div className="absolute bottom-3 left-1/2 w-0 h-1 bg-gradient-to-r from-purple-400 to-pink-400 transition-all duration-300 group-hover:w-4/5 group-hover:left-[10%] rounded-full shadow-lg"></div>
                </Link>
              </li>
            </ul>
          </nav>
        </div>
      </header>

      {/* Main content with enhanced backdrop */}
      <main className="container mx-auto px-6 py-12 min-h-[calc(100vh-200px)] relative z-10">
        <div className="relative">
          {/* Enhanced background decorations */}
          <div className="absolute -top-8 -right-8 w-96 h-96 bg-gradient-to-br from-cyan-500/8 to-blue-500/6 rounded-full blur-3xl -z-10 animate-pulse" style={{ animationDelay: '1s' }}></div>
          <div className="absolute -bottom-8 -left-8 w-80 h-80 bg-gradient-to-tr from-emerald-500/8 to-purple-500/6 rounded-full blur-3xl -z-10 animate-pulse" style={{ animationDelay: '3s' }}></div>
          <div className="absolute top-1/2 right-1/4 w-64 h-64 bg-gradient-to-bl from-indigo-500/6 to-teal-500/6 rounded-full blur-2xl -z-10 animate-pulse" style={{ animationDelay: '5s' }}></div>
          
          <Outlet />
        </div>
      </main>

      {/* Enhanced footer with glassmorphism */}
      <footer className="backdrop-blur-xl bg-slate-900/60 border-t border-cyan-500/20 mt-auto relative z-20">
        <div className="container mx-auto px-6 py-10">
          <div className="flex flex-col md:flex-row justify-between items-center space-y-6 md:space-y-0">
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 bg-gradient-to-br from-cyan-400 to-blue-500 rounded-xl flex items-center justify-center shadow-xl">
                <span className="text-white font-bold text-2xl">⚽</span>
              </div>
              <div>
                <p className="font-bold text-xl text-white">Football Simulation Dashboard</p>
                <p className="text-cyan-300 text-sm opacity-90">Advanced League Management System</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-8">
              <div className="text-center backdrop-blur-sm bg-white/5 px-4 py-3 rounded-xl border border-cyan-500/20">
                <p className="text-cyan-300 text-sm font-medium">Current Season</p>
                <p className="text-cyan-200 font-bold text-lg">{new Date().getFullYear()}</p>
              </div>
              <div className="text-center backdrop-blur-sm bg-white/5 px-4 py-3 rounded-xl border border-emerald-500/20">
                <p className="text-emerald-300 text-sm font-medium">Version</p>
                <p className="text-emerald-200 font-bold text-lg">v2.0</p>
              </div>
            </div>
          </div>
          
          <div className="mt-8 pt-6 border-t border-cyan-500/20 text-center">
            <p className="text-cyan-300 text-sm opacity-80">
              &copy; {new Date().getFullYear()} Football Simulation Dashboard. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Layout;