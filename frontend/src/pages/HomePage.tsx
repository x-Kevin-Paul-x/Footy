import React, { useEffect } from 'react';
import { Link } from 'react-router-dom'; // Import Link
import { useSimulationStore } from '../store/simulationStore';

interface HomePageProps {
  showToast?: (message: string, type?: "success" | "error" | "info") => void;
}

const HomePage: React.FC<HomePageProps> = ({ showToast }) => {
  const {
    availableSeasons,
    selectedSeason,
    currentReport, // Add currentReport
    isSimulating,
    isLoading,
    error,
    simulationMessage,
    fetchAvailableSeasons,
    selectSeason,
    runSimulation,
  } = useSimulationStore();

  useEffect(() => {
    fetchAvailableSeasons();
  }, [fetchAvailableSeasons]);

  const handleRunSimulation = () => {
    runSimulation();
  };

  const handleSeasonChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const season = parseInt(event.target.value, 10);
    selectSeason(isNaN(season) ? null : season);
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6 text-center">Football Simulation Dashboard</h1>
      {showToast && (
        <button
          className="mb-4 bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded transition"
          onClick={() => showToast("This is a demo notification!", "success")}
        >
          Show Demo Toast
        </button>
      )}

      <div className="mb-8 p-6 bg-gray-800 rounded-lg shadow-xl">
        <h2 className="text-2xl font-semibold mb-4 text-blue-400">Simulation Control</h2>
        <button
          onClick={handleRunSimulation}
          disabled={isSimulating}
          className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg text-lg transition duration-150 ease-in-out disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSimulating ? 'Running Simulation...' : 'Run New Simulation'}
        </button>
        {isSimulating && <p className="mt-3 text-yellow-400">Please wait, this may take a few moments...</p>}
        {simulationMessage && <p className={`mt-3 ${error ? 'text-red-400' : 'text-green-400'}`}>{simulationMessage}</p>}
        {error && !isSimulating && <p className="mt-3 text-red-400">Error: {error}</p>}
      </div>

      <div className="mb-8 p-6 bg-gray-800 rounded-lg shadow-xl">
        <h2 className="text-2xl font-semibold mb-4 text-blue-400">View Season Data</h2>
        {availableSeasons.length > 0 ? (
          <div>
            <label htmlFor="season-select" className="block mb-2 text-lg">Select Season:</label>
            <select
              id="season-select"
              value={selectedSeason || ''}
              onChange={handleSeasonChange}
              disabled={isLoading || isSimulating}
              className="bg-gray-700 border border-gray-600 text-white text-lg rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-3.5 disabled:opacity-70"
            >
              <option value="" disabled>-- Select a Season --</option>
              {availableSeasons.map((season) => (
                <option key={season} value={season}>
                  Season {season}
                </option>
              ))}
            </select>
            {isLoading && <p className="mt-3 text-yellow-400">Loading season data...</p>}
          </div>
        ) : (
          <p className="text-lg">
            {isLoading ? 'Loading available seasons...' : 'No simulation data found. Please run a new simulation.'}
          </p>
        )}
      </div>

      {selectedSeason && !isLoading && (
        <div className="mt-8 p-6 bg-gray-800 rounded-lg shadow-xl">
          <h2 className="text-2xl font-semibold mb-4 text-blue-400">
            Season {selectedSeason} Summary
          </h2>
          {currentReport ? (
            <div className="space-y-6">
              {/* Champions and Manager */}
              <div>
                <h3 className="text-xl font-semibold text-green-400 mb-2">League Champions: {currentReport.champions}</h3>
                {currentReport.champions_manager && (
                  <div className="pl-4 border-l-2 border-green-500">
                    <p className="text-lg"><strong>Manager:</strong> {currentReport.champions_manager.name}</p>
                    <p><strong>Experience:</strong> {currentReport.champions_manager.experience}</p>
                    <p><strong>Preferred Formation:</strong> {currentReport.champions_manager.formation}</p>
                    <p><strong>Transfer Success:</strong> {(currentReport.champions_manager.transfer_success_rate * 100).toFixed(1)}%</p>
                  </div>
                )}
              </div>

              {/* Key League Stats */}
              {currentReport.season_stats && (
                <div>
                  <h3 className="text-xl font-semibold text-sky-400 mb-2">League Statistics</h3>
                  <div className="grid md:grid-cols-2 gap-x-4 gap-y-2 pl-4 border-l-2 border-sky-500">
                    <p><strong>Total Matches:</strong> {currentReport.season_stats.total_matches}</p>
                    <p><strong>Total Goals:</strong> {currentReport.season_stats.total_goals}</p>
                    <p><strong>Avg. Goals/Match:</strong> {currentReport.season_stats.average_goals_per_match?.toFixed(2)}</p>
                    <p><strong>Best Attack:</strong> {currentReport.season_stats.best_attack?.[0]} ({currentReport.season_stats.best_attack?.[1].gf} goals)</p>
                    <p><strong>Best Defence:</strong> {currentReport.season_stats.best_defense?.[0]} ({currentReport.season_stats.best_defense?.[1].ga} conceded)</p>
                  </div>
                </div>
              )}

              {/* Best Players */}
              {currentReport.best_players && currentReport.best_players.length > 0 && (
                <div>
                  <h3 className="text-xl font-semibold text-yellow-400 mb-2">Top Players</h3>
                  <ul className="pl-4 border-l-2 border-yellow-500 space-y-1">
                    {currentReport.best_players.slice(0, 5).map((player, index) => (
                      <li key={index} className="text-lg">
                        <Link to={`/player/${encodeURIComponent(player.name)}/${selectedSeason}`} className="hover:text-yellow-300">
                          {player.name}
                        </Link> ({player.position}) - {player.team} - Value: €{player.value?.toLocaleString()}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <p className="mt-6 text-center text-gray-400">Navigate using the links above to explore more detailed data for this season.</p>
            </div>
          ) : (
            <p className="text-lg text-center">Loading summary data...</p>
          )}
        </div>
      )}
    </div>
  );
};

export default HomePage;
