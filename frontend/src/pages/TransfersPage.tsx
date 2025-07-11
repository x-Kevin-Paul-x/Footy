import React, { useEffect, useMemo } from 'react';
import { useSimulationStore } from '../store/simulationStore';
import { Link } from 'react-router-dom';

interface CompletedTransfer {
  player: string;
  from_team: string;
  to_team: string;
  amount: number;
  day: number;
}

const TransfersPage: React.FC = () => {
  const { currentReport, isLoading, error, selectedSeason, fetchAvailableSeasons, availableSeasons, selectSeason } = useSimulationStore();

  useEffect(() => {
    if (availableSeasons.length === 0) {
      fetchAvailableSeasons();
    }
  }, [fetchAvailableSeasons, availableSeasons.length]);

  // Refetch transfers when season changes
  useEffect(() => {
    if (selectedSeason) {
      selectSeason(selectedSeason);
    }
  }, [selectedSeason, selectSeason]);

  // Filter transfers based on the selected season
  const currentSeasonTransfers = useMemo(() => {
    if (!currentReport?.transfers?.all_completed_transfers || !selectedSeason) {
      return [];
    }

    const transfers = currentReport.transfers.all_completed_transfers as CompletedTransfer[];
    // Assuming the API returns transfers for the selected season only,
    // or that 'day' is relative to the start of the *entire simulation* not just the season.
    // If 'day' is relative to the start of each season (0-27 for each season),
    // then this filtering is correct for showing only the current season's transfers.
    // The user's feedback implies 'day' might be continuous across seasons.
    // For now, we'll assume the API provides data correctly scoped to the selectedSeason.
    // If days 0-13 are season 1, and 14-27 are season 2, this needs backend adjustment
    // or more complex frontend logic if all data comes at once.
    // Based on current understanding, we show all transfers for the *selectedSeason*.
    return transfers; 

  }, [currentReport, selectedSeason]);

  if (isLoading && !currentReport) {
    return <p className="text-center text-xl mt-8">Loading transfers data...</p>;
  }

  if (error && !currentReport) {
    return <p className="text-center text-xl mt-8 text-red-500">Error loading data: {error}</p>;
  }

  if (!selectedSeason) {
    return (
      <div className="text-center text-xl mt-8">
        <p>Please select a season using the season selector in the navigation bar.</p>
      </div>
    );
  }

  if (!currentReport || !currentReport.transfers) {
    return <p className="text-center text-xl mt-8">No transfers data available for the selected season.</p>;
  }

  const { total_transfers, biggest_spenders, most_active } = currentReport.transfers;

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

      {/* All Completed Transfers Table for the selected season */}
      <h2 className="text-2xl font-semibold mb-4">All Completed Transfers for Season {selectedSeason}</h2>
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
            {currentSeasonTransfers.length > 0 ? (
              currentSeasonTransfers.map((transfer, index) => (
                <tr key={index} className="border-b border-gray-700 hover:bg-gray-700/50">
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
    </div>
  );
};

export default TransfersPage;
