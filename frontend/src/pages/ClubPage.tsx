import React, { useEffect, useMemo } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useSimulationStore } from '../store/simulationStore';
import type { TeamDetail, Player } from '../services/api'; // Import types

// Define a more specific type for team transfer history items
interface TeamTransferHistoryItem {
  type: 'buy' | 'sale' | 'purchase'; // Assuming 'purchase' is a type based on feedback
  player_name: string;
  price: number;
  success: boolean;
  day_of_window: number;
  // If the structure is an array/tuple, we'll adjust access below
  // For now, let's assume it *should* be an object with these keys.
  // The feedback suggests it might be an array or malformed.
}

const ClubPage: React.FC = () => {
  const { clubName, season: seasonParam } = useParams<{ clubName: string; season: string }>();
  const navigate = useNavigate();
  const {
    currentReport,
    isLoading,
    error,
    selectedSeason,
    selectSeason,
    fetchAvailableSeasons,
    availableSeasons,
  } = useSimulationStore();

  const numericSeasonParam = seasonParam ? parseInt(seasonParam, 10) : null;

  useEffect(() => {
    if (availableSeasons.length === 0) {
      fetchAvailableSeasons();
    }
  }, [fetchAvailableSeasons, availableSeasons.length]);

  useEffect(() => {
    if (numericSeasonParam && numericSeasonParam !== selectedSeason) {
      // If route season differs from store, or no season selected, update store
      // This also handles direct navigation to this page
      selectSeason(numericSeasonParam);
    }
  }, [numericSeasonParam, selectedSeason, selectSeason]);

  const clubData: TeamDetail | undefined = useMemo(() => {
    if (!currentReport || !clubName) return undefined;
    return currentReport.all_teams_details.find(
      (team) => team.name.toLowerCase() === clubName.toLowerCase()
    );
  }, [currentReport, clubName]);

  if (isLoading && !currentReport) {
    return <p className="text-center text-xl mt-8">Loading club data...</p>;
  }

  if (error) {
    return <p className="text-center text-xl mt-8 text-red-500">Error loading data: {error}</p>;
  }
  
  if (!numericSeasonParam) {
    return <p className="text-center text-xl mt-8">Season parameter is missing or invalid.</p>;
  }

  if (!selectedSeason || selectedSeason !== numericSeasonParam) {
     // Still waiting for season data to load based on URL param
    return <p className="text-center text-xl mt-8">Loading data for season {numericSeasonParam}...</p>;
  }

  if (!clubData) {
    return (
      <div className="text-center text-xl mt-8">
        <p>Club data not found for "{clubName}" in season {selectedSeason}.</p>
        <Link to="/" className="text-blue-400 hover:text-blue-600 mt-4 inline-block">Go to Homepage</Link>
      </div>
    );
  }

  const { name, manager_formation, players, team_season_stats, team_transfer_history, budget, squad_strength } = clubData;

  return (
    <div className="container mx-auto p-4">
      <button onClick={() => navigate(-1)} className="mb-4 bg-gray-700 hover:bg-gray-600 text-white py-2 px-4 rounded">
        &larr; Back
      </button>
      <h1 className="text-4xl font-bold mb-2">{name}</h1>
      <p className="text-xl text-gray-400 mb-6">Season {selectedSeason}</p>

      {/* Club Overview */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-gray-800 p-6 rounded-lg shadow-xl">
          <h2 className="text-lg font-semibold text-blue-400 mb-1">Manager's Formation</h2>
          <p className="text-2xl">{manager_formation || 'N/A'}</p>
        </div>
        <div className="bg-gray-800 p-6 rounded-lg shadow-xl">
          <h2 className="text-lg font-semibold text-blue-400 mb-1">Budget</h2>
          <p className="text-2xl">€{budget?.toLocaleString() || 'N/A'}</p>
        </div>
        <div className="bg-gray-800 p-6 rounded-lg shadow-xl">
          <h2 className="text-lg font-semibold text-blue-400 mb-1">Squad Strength</h2>
          <p className="text-2xl">{squad_strength?.toFixed(2) || 'N/A'}</p>
        </div>
        <div className="bg-gray-800 p-6 rounded-lg shadow-xl">
          <h2 className="text-lg font-semibold text-blue-400 mb-1">League Points</h2>
          <p className="text-2xl">{team_season_stats?.points || 'N/A'}</p>
        </div>
      </div>
      
      {/* Squad List */}
      <div className="mb-8">
        <h2 className="text-2xl font-semibold mb-4">Squad List</h2>
        <div className="overflow-x-auto bg-gray-800 shadow-xl rounded-lg">
          <table className="min-w-full text-sm text-left text-gray-300">
            <thead className="text-xs text-gray-400 uppercase bg-gray-700">
              <tr>
                <th scope="col" className="px-6 py-3">Name</th>
                <th scope="col" className="px-6 py-3">Position</th>
                <th scope="col" className="px-6 py-3 text-center">Age</th>
                <th scope="col" className="px-6 py-3 text-center">Overall</th>
                <th scope="col" className="px-6 py-3 text-right">Value</th>
                <th scope="col" className="px-6 py-3">Role</th>
              </tr>
            </thead>
            <tbody>
              {players.map((player: Player) => (
                <tr key={player.name} className="border-b border-gray-700 hover:bg-gray-700/50">
                  <td className="px-6 py-4 font-medium whitespace-nowrap">
                     <Link to={`/player/${encodeURIComponent(player.name)}/${selectedSeason}`} className="hover:text-blue-400">
                        {player.name}
                     </Link>
                  </td>
                  <td className="px-6 py-4">{player.position}</td>
                  <td className="px-6 py-4 text-center">{player.age}</td>
                <td className="px-6 py-4 text-center">
                  {player.attributes ? (
                    (Object.values(player.attributes).reduce((sum, category) => {
                      if (typeof category === 'object') {
                        const values = Object.values(category).filter(val => typeof val === 'number');
                        return sum + values.reduce((catSum, val) => catSum + val, 0) / values.length;
                      }
                      return sum;
                    }, 0) / Object.keys(player.attributes).length).toFixed(1)
                  ) : 'N/A'}
                </td>
                  <td className="px-6 py-4 text-right">€{player.market_value?.toLocaleString()}</td>
                  <td className="px-6 py-4">{player.squad_role}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Transfer History for the Club */}
      <div className="mb-8">
        <h2 className="text-2xl font-semibold mb-4">Season Transfer History</h2>
        {team_transfer_history && team_transfer_history.length > 0 ? (
          <div className="overflow-x-auto bg-gray-800 shadow-xl rounded-lg">
            <table className="min-w-full text-sm text-left text-gray-300">
              <thead className="text-xs text-gray-400 uppercase bg-gray-700">
                <tr>
                  <th scope="col" className="px-6 py-3">Type</th>
                  <th scope="col" className="px-6 py-3">Player</th>
                  <th scope="col" className="px-6 py-3 text-right">Price</th>
                  <th scope="col" className="px-6 py-3 text-center">Success</th>
                  <th scope="col" className="px-6 py-3">Day</th>
                </tr>
              </thead>
              <tbody>
                {team_transfer_history.map((transferItem: any, index: number) => {
                  // Attempt to handle both object and array structures based on feedback
                  let type, player_name, price, success, day_of_window;

                  if (typeof transferItem === 'object' && transferItem !== null && !Array.isArray(transferItem)) {
                    // Standard object structure
                    type = transferItem.type;
                    player_name = transferItem.player_name;
                    price = transferItem.price;
                    success = transferItem.success;
                    day_of_window = transferItem.day_of_window;
                  } else if (Array.isArray(transferItem)) {
                    // Array/tuple structure
                    type = transferItem[0];
                    player_name = transferItem[1]; // Might be undefined if array is short
                    price = transferItem[2];       // Might be undefined
                    success = transferItem[3];     // Might be undefined
                    day_of_window = transferItem[4]; // Might be undefined
                  } else if (typeof transferItem === 'string') {
                    // Simple string type, e.g., "purchase" or "sale"
                    type = transferItem;
                    // Other fields will be undefined, leading to "N/A"
                    player_name = undefined;
                    price = undefined;
                    success = undefined;
                    day_of_window = undefined;
                     console.log(`Transfer item is a simple string: ${transferItem}`);
                  } else {
                    console.warn("Unknown transfer history item structure:", transferItem);
                    return (
                      <tr key={index} className="border-b border-gray-700 hover:bg-gray-700/50">
                        <td colSpan={5} className="px-6 py-4 text-center text-yellow-400">
                          Unknown transfer data structure.
                        </td>
                      </tr>
                    );
                  }
                  
                  // Normalize 'purchase' to 'buy' if needed, or handle as distinct type
                  let displayType = type;
                  if (typeof type === 'string') {
                    if (type.toLowerCase() === 'purchase') displayType = 'Buy (Listed)';
                    else displayType = type.charAt(0).toUpperCase() + type.slice(1); // Capitalize
                  } else {
                    displayType = 'N/A';
                  }
                  

                  return (
                    <tr key={index} className="border-b border-gray-700 hover:bg-gray-700/50">
                      <td className="px-6 py-4">{displayType}</td>
                      <td className="px-6 py-4">
                        {player_name ? (
                          <Link to={`/player/${encodeURIComponent(player_name)}/${selectedSeason}`} className="hover:text-blue-400">
                            {player_name}
                          </Link>
                        ) : 'N/A'}
                      </td>
                      <td className="px-6 py-4 text-right">
                        {typeof price === 'number' ? `€${price.toLocaleString()}` : 'N/A'}
                      </td>
                      <td className={`px-6 py-4 text-center ${success ? 'text-green-400' : 'text-red-400'}`}>
                        {typeof success === 'boolean' ? (success ? 'Yes' : 'No') : 'N/A'}
                      </td>
                      <td className="px-6 py-4 text-center">{day_of_window ?? 'N/A'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p>No transfer activity recorded for this club this season.</p>
        )}
      </div>
    </div>
  );
};

export default ClubPage;
