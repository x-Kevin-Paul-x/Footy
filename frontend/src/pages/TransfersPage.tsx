import React, { useEffect } from 'react';
import { useSimulationStore } from '../store/simulationStore';
import { Link } from 'react-router-dom';

// Define a more specific type for completed transfers if available from your backend
interface CompletedTransfer {
  player: string; // Assuming player name, adjust if it's an object or ID
  from_team: string;
  to_team: string;
  amount: number;
  day: number; // Or date string
  // Add other relevant fields like value, listing_id etc. if present
}

const TransfersPage: React.FC = () => {
  const { currentReport, isLoading, error, selectedSeason, fetchAvailableSeasons, availableSeasons } = useSimulationStore();

  useEffect(() => {
    if (availableSeasons.length === 0) {
      fetchAvailableSeasons();
    }
  }, [fetchAvailableSeasons, availableSeasons.length]);

  if (isLoading && !currentReport) {
    return <p className="text-center text-xl mt-8">Loading transfers data...</p>;
  }

  if (error && !currentReport) {
    return <p className="text-center text-xl mt-8 text-red-500">Error loading data: {error}</p>;
  }

  if (!selectedSeason) {
    return (
      <div className="text-center text-xl mt-8">
        <p>Please select a season from the <Link to="/" className="text-blue-400 hover:text-blue-600">Homepage</Link> to view transfers.</p>
      </div>
    );
  }

  if (!currentReport || !currentReport.transfers) {
    return <p className="text-center text-xl mt-8">No transfers data available for the selected season.</p>;
  }

  const { total_transfers, biggest_spenders, most_active, all_completed_transfers } = currentReport.transfers;

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6 text-center">Transfer Market - Season {selectedSeason}</h1>

      {/* Transfer Summaries */}
      <div className="grid md:grid-cols-3 gap-6 mb-8">
        <div className="bg-gray-800 p-6 rounded-lg shadow-xl">
          <h2 className="text-xl font-semibold text-blue-400 mb-2">Total Transfers</h2>
          <p className="text-4xl font-bold">{total_transfers}</p>
        </div>
        <div className="bg-gray-800 p-6 rounded-lg shadow-xl">
          <h2 className="text-xl font-semibold text-blue-400 mb-2">Biggest Spenders</h2>
          {biggest_spenders && biggest_spenders.length > 0 ? (
            <ul className="space-y-1">
              {biggest_spenders.map(([team, amount]) => (
                <li key={team} className="flex justify-between">
                  <span>{team}</span>
                  <span className="font-semibold">€{amount.toLocaleString()}</span>
                </li>
              ))}
            </ul>
          ) : <p>No spending data.</p>}
        </div>
        <div className="bg-gray-800 p-6 rounded-lg shadow-xl">
          <h2 className="text-xl font-semibold text-blue-400 mb-2">Most Active Teams</h2>
           {most_active && most_active.length > 0 ? (
            <ul className="space-y-1">
              {most_active.map(([team, count]) => (
                <li key={team} className="flex justify-between">
                  <span>{team}</span>
                  <span className="font-semibold">{count} deals</span>
                </li>
              ))}
            </ul>
          ) : <p>No activity data.</p>}
        </div>
      </div>

      {/* All Completed Transfers Table */}
      <h2 className="text-2xl font-semibold mb-4">All Completed Transfers</h2>
      <div className="overflow-x-auto bg-gray-800 shadow-xl rounded-lg">
        <table className="min-w-full text-sm text-left text-gray-300">
          <thead className="text-xs text-gray-400 uppercase bg-gray-700">
            <tr>
              <th scope="col" className="px-6 py-3">Player</th>
              <th scope="col" className="px-6 py-3">From Team</th>
              <th scope="col" className="px-6 py-3">To Team</th>
              <th scope="col" className="px-6 py-3 text-right">Amount</th>
              <th scope="col" className="px-6 py-3 text-center">Day</th>
            </tr>
          </thead>
          <tbody>
            {(all_completed_transfers as CompletedTransfer[]).length > 0 ? (
              (all_completed_transfers as CompletedTransfer[]).map((transfer, index) => (                <tr key={index} className="border-b border-gray-700 hover:bg-gray-700/50">
                  <td className="px-6 py-4 font-medium whitespace-nowrap">
                    <Link 
                      to={`/player/${encodeURIComponent(transfer.player)}/${selectedSeason}`}
                      className="text-accent-cyan hover:text-accent-blue transition-colors duration-200 font-semibold hover:underline"
                    >
                      {transfer.player}
                    </Link>
                  </td>
                  <td className="px-6 py-4">{transfer.from_team}</td>
                  <td className="px-6 py-4">{transfer.to_team}</td>
                  <td className="px-6 py-4 text-right">€{transfer.amount.toLocaleString()}</td>
                  <td className="px-6 py-4 text-center">{transfer.day}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5} className="px-6 py-4 text-center">No completed transfers recorded for this season.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {/* Placeholder for charts */}
    </div>
  );
};

export default TransfersPage;
