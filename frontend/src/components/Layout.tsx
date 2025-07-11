import React, { useEffect } from 'react';
import { useSimulationStore } from '../store/simulationStore';
import { Link, Outlet } from 'react-router-dom';

const Layout: React.FC = () => {
  const { availableSeasons, selectedSeason, fetchAvailableSeasons, selectSeason } = useSimulationStore();
  
  useEffect(() => {
    if (availableSeasons.length === 0) {
      fetchAvailableSeasons();
    }
  }, [fetchAvailableSeasons, availableSeasons.length]);

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
          {/* Enhanced navigation */}
          <nav className="py-6 px-10" aria-label="Main navigation">
            <ul className="flex items-center justify-center flex-wrap list-none " role="menubar">
              {/* FOOTY text at beginning */}
              <li className="mx-2" role="none">
                <div className="group relative font-bold text-lg px-8 py-4 rounded-2xl backdrop-blur-sm">
                  <span className="relative z-10 text-white flex items-center space-x-3">
                    <span className="text-2xl">FOOTY</span>
                  </span>
                </div>
              </li>
              
              <li className="mx-2" role="none">
                <Link 
                  to="/" 
                  className="group relative font-bold text-lg px-8 py-4 rounded-2xl transition-all duration-500 hover:bg-cyan-500/20 hover:scale-105 hover:shadow-2xl border border-transparent hover:border-cyan-400/50 backdrop-blur-sm"
                >
                  <span className="relative z-10 text-white group-hover:text-cyan-300 transition-all duration-300 flex items-center space-x-3">
                    <span className="text-2xl">🏠</span>
                    <span>Home</span>
                  </span>
                  <div className="absolute bottom-3 left-1/2 w-0 h-1 bg-gradient-to-r from-cyan-400 to-blue-400 transition-all duration-300 group-hover:w-4/5 group-hover:left-[10%] rounded-full shadow-lg"></div>
                </Link>
              </li>
              <li className="mx-2" role="none">
                <Link 
                  to="/league-table" 
                  className="group relative font-bold text-lg px-8 py-4 rounded-2xl transition-all duration-500 hover:bg-blue-500/20 hover:scale-105 hover:shadow-2xl border border-transparent hover:border-blue-400/50 backdrop-blur-sm"
                >
                  <span className="relative z-10 text-white group-hover:text-blue-300 transition-all duration-300 flex items-center space-x-3">
                    <span className="text-2xl">📊</span>
                    <span>League Table</span>
                  </span>
                  <div className="absolute bottom-3 left-1/2 w-0 h-1 bg-gradient-to-r from-blue-400 to-indigo-400 transition-all duration-300 group-hover:w-4/5 group-hover:left-[10%] rounded-full shadow-lg"></div>
                </Link>
              </li>
              <li className="mx-2" role="none">
                <Link 
                  to="/transfers" 
                  className="group relative font-bold text-lg px-8 py-4 rounded-2xl transition-all duration-500 hover:bg-emerald-500/20 hover:scale-105 hover:shadow-2xl border border-transparent hover:border-emerald-400/50 backdrop-blur-sm"
                >
                  <span className="relative z-10 text-white group-hover:text-emerald-300 transition-all duration-300 flex items-center space-x-3">
                    <span className="text-2xl">💰</span>
                    <span>Transfers</span>
                  </span>
                  <div className="absolute bottom-3 left-1/2 w-0 h-1 bg-gradient-to-r from-emerald-400 to-teal-400 transition-all duration-300 group-hover:w-4/5 group-hover:left-[10%] rounded-full shadow-lg"></div>
                </Link>
              </li>
              <li className="mx-2" role="none">
                <Link 
                  to="/matches" 
                  className="group relative font-bold text-lg px-8 py-4 rounded-2xl transition-all duration-500 hover:bg-purple-500/20 hover:scale-105 hover:shadow-2xl border border-transparent hover:border-purple-400/50 backdrop-blur-sm"
                >
                  <span className="relative z-10 text-white group-hover:text-purple-300 transition-all duration-300 flex items-center space-x-3">
                    <span className="text-2xl">⚽</span>
                    <span>Matches</span>
                  </span>
                  <div className="absolute bottom-3 left-1/2 w-0 h-1 bg-gradient-to-r from-purple-400 to-pink-400 transition-all duration-300 group-hover:w-4/5 group-hover:left-[10%] rounded-full shadow-lg"></div>
                </Link>
              </li>
              
              {/* Season selector at end */}
              <li className="mx-2">
                <div className="group relative font-bold text-lg px-8 py-4 rounded-2xl transition-all duration-500 hover:bg-cyan-500/20 hover:scale-105 hover:shadow-2xl border border-transparent hover:border-cyan-400/50 backdrop-blur-sm">
                  <div className="flex items-center space-x-2">
                    <span className="text-cyan-300">Season:</span>
                    <div className="relative">
                      <select
                        value={selectedSeason ?? ''}
                        onChange={(e) => selectSeason(Number(e.target.value))}
                        className="bg-slate-800/80 border border-cyan-500/30 rounded-lg py-1 px-3 text-white appearance-none focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
                      >
                        {availableSeasons.map(season => (
                          <option key={season} value={season}>{season}</option>
                        ))}
                      </select>
                      <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-cyan-300">
                        <svg className="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
                          <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" />
                        </svg>
                      </div>
                    </div>
                  </div>
                </div>
              </li>
            </ul>
          </nav>
        </div>
      </header>

      {/* Main content with enhanced backdrop */}
      <main className="container mx-auto px-6 py-12 min-h-[calc(100vh-200px)] relative z-10" role="main">
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
