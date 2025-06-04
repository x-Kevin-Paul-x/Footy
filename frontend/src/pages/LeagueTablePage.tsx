import React, { useEffect } from 'react';
import { useSimulationStore } from '../store/simulationStore';
import { Link } from 'react-router-dom';

const LeagueTablePage: React.FC = () => {
  const { currentReport, isLoading, error, selectedSeason, fetchAvailableSeasons, availableSeasons } = useSimulationStore();

  useEffect(() => {
    // Ensure seasons are fetched if not already, or if navigating directly to this page
    if (availableSeasons.length === 0) {
      fetchAvailableSeasons();
    }
  }, [fetchAvailableSeasons, availableSeasons.length]);

  if (isLoading && !currentReport) {
    return <p className="text-center text-xl mt-8">Loading league table...</p>;
  }

  if (error && !currentReport) {
    return <p className="text-center text-xl mt-8 text-red-500">Error loading data: {error}</p>;
  }

  if (!selectedSeason) {
    return (
      <div className="text-center text-xl mt-8">
        <p>Please select a season from the <Link to="/" className="text-blue-400 hover:text-blue-600">Homepage</Link> to view the league table.</p>
      </div>
    );
  }
  
  if (!currentReport || !currentReport.table) {
    return <p className="text-center text-xl mt-8">No league table data available for the selected season.</p>;
  }

  const tableData = currentReport.table;

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6 text-center">League Table - Season {selectedSeason}</h1>
      <div className="overflow-x-auto bg-gray-800 shadow-xl rounded-lg">
        <table className="min-w-full text-sm text-left text-gray-300">
          <thead className="text-xs text-gray-400 uppercase bg-gray-700">
            <tr>
              <th scope="col" className="px-6 py-3">Pos</th>
              <th scope="col" className="px-6 py-3">Team</th>
              <th scope="col" className="px-6 py-3 text-center">Pld</th>
              <th scope="col" className="px-6 py-3 text-center">W</th>
              <th scope="col" className="px-6 py-3 text-center">D</th>
              <th scope="col" className="px-6 py-3 text-center">L</th>
              <th scope="col" className="px-6 py-3 text-center">GF</th>
              <th scope="col" className="px-6 py-3 text-center">GA</th>
              <th scope="col" className="px-6 py-3 text-center">GD</th>
              <th scope="col" className="px-6 py-3 text-center">Pts</th>
            </tr>
          </thead>
          <tbody>
            {tableData.map((row, index) => {
              const teamName = row[0];
              const stats = row[1];
              return (
                <tr key={teamName} className="border-b border-gray-700 hover:bg-gray-700/50">
                  <td className="px-6 py-4 font-medium">{index + 1}</td>
                  <td className="px-6 py-4 font-medium whitespace-nowrap">
                    <Link to={`/club/${encodeURIComponent(teamName)}/${selectedSeason}`} className="hover:text-blue-400">
                      {teamName}
                    </Link>
                  </td>
                  <td className="px-6 py-4 text-center">{stats.played}</td>
                  <td className="px-6 py-4 text-center">{stats.won}</td>
                  <td className="px-6 py-4 text-center">{stats.drawn}</td>
                  <td className="px-6 py-4 text-center">{stats.lost}</td>
                  <td className="px-6 py-4 text-center">{stats.gf}</td>
                  <td className="px-6 py-4 text-center">{stats.ga}</td>
                  <td className="px-6 py-4 text-center">{stats.gd}</td>
                  <td className="px-6 py-4 font-semibold text-center">{stats.points}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default LeagueTablePage;
