import React, { useEffect, useMemo } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useSimulationStore } from '../store/simulationStore';
import type { Player, PlayerAttributes } from '../services/api'; // Import types
import { Radar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
  type ChartData, // Type-only import
  type ChartOptions, // Type-only import
} from 'chart.js';

ChartJS.register(
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend
);

const PlayerPage: React.FC = () => {
  const { playerName, season: seasonParam } = useParams<{ playerName: string; season: string }>();
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
      selectSeason(numericSeasonParam);
    }
  }, [numericSeasonParam, selectedSeason, selectSeason]);

  const playerData: Player | undefined = useMemo(() => {
    if (!currentReport || !playerName) return undefined;
    for (const team of currentReport.all_teams_details) {
      const foundPlayer = team.players.find(
        (p) => p.name.toLowerCase() === playerName.toLowerCase()
      );
      if (foundPlayer) return foundPlayer;
    }
    return undefined;
  }, [currentReport, playerName]);

  if (isLoading && !currentReport) {
    return <p className="text-center text-xl mt-8">Loading player data...</p>;
  }

  if (error) {
    return <p className="text-center text-xl mt-8 text-red-500">Error loading data: {error}</p>;
  }

  if (!numericSeasonParam) {
    return <p className="text-center text-xl mt-8">Season parameter is missing or invalid.</p>;
  }
  
  if (!selectedSeason || selectedSeason !== numericSeasonParam) {
    return <p className="text-center text-xl mt-8">Loading data for season {numericSeasonParam}...</p>;
  }

  if (!playerData) {
    return (
      <div className="text-center text-xl mt-8">
        <p>Player data not found for "{playerName}" in season {selectedSeason}.</p>
        <Link to="/" className="text-blue-400 hover:text-blue-600 mt-4 inline-block">Go to Homepage</Link>
      </div>
    );
  }

  const { name, age, position, team, potential, wage, contract_length, form, injury_history, squad_role, attributes, stats, market_value } = playerData;

  const attributeCategories = attributes ? Object.keys(attributes) as (keyof PlayerAttributes)[] : [];
  
  const radarChartData: ChartData<'radar'> = {
    labels: [],
    datasets: [
      {
        label: 'Attributes',
        data: [],
        backgroundColor: 'rgba(0, 255, 255, 0.2)', // accent-cyan with alpha
        borderColor: 'rgb(0, 255, 255)',          // accent-cyan solid
        borderWidth: 2,                            // Slightly thicker border
        pointBackgroundColor: 'rgb(0, 255, 255)',  // accent-cyan solid
        pointBorderColor: '#fff',                  // White border for points for better visibility
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: 'rgb(0, 255, 255)'
      },
    ],
  };
  
  // Logic for populating radarChartData
  if (attributes) {
    const labels: string[] = [];
    const data: number[] = [];

    if (position === 'GK' && attributes.goalkeeping) {
      // For GKs, use their specific goalkeeping attributes
      const gkAttributes = attributes.goalkeeping;
      for (const key in gkAttributes) {
        if (Object.prototype.hasOwnProperty.call(gkAttributes, key) && typeof gkAttributes[key as keyof typeof gkAttributes] === 'number') {
          labels.push(key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()));
          data.push(gkAttributes[key as keyof typeof gkAttributes] as number);
        }
      }
    } else {
      // For outfield players, calculate averages for major categories
      const outfieldMajorCategoriesForRadar: (keyof PlayerAttributes)[] = [
        'pace', 'shooting', 'passing', 'dribbling', 'defending', 'physical'
      ];

      outfieldMajorCategoriesForRadar.forEach(categoryKey => {
        const categoryAttributes = attributes[categoryKey];
        if (categoryAttributes && typeof categoryAttributes === 'object') {
          const values: number[] = Object.values(categoryAttributes).filter(val => typeof val === 'number');
          if (values.length > 0) {
            const average = values.reduce((sum, val) => sum + val, 0) / values.length;
            labels.push(categoryKey.charAt(0).toUpperCase() + categoryKey.slice(1));
            data.push(parseFloat(average.toFixed(2)));
          } else {
            // Handle case where a category might have no numeric sub-attributes
            labels.push(categoryKey.charAt(0).toUpperCase() + categoryKey.slice(1));
            data.push(0); 
          }
        } else {
            // Handle case where a major category might be missing
            labels.push(categoryKey.charAt(0).toUpperCase() + categoryKey.slice(1));
            data.push(0);
        }
      });
    }
    radarChartData.labels = labels;
    radarChartData.datasets[0].data = data;
  }

  const radarChartOptions: ChartOptions<'radar'> = {
    scales: {
      r: {
        angleLines: { display: true, color: 'rgba(224, 224, 224, 0.2)' }, // primary-text (E0E0E0) with alpha
        suggestedMin: 0,
        suggestedMax: 100,
        grid: { color: 'rgba(224, 224, 224, 0.1)' }, // Lighter grid lines
        pointLabels: { 
          font: { size: 12, family: 'Montserrat' }, // Use heading font
          color: '#E0E0E0' // primary-text
        },
        ticks: { 
          backdropColor: 'transparent', 
          color: '#999999', // secondary-text
          stepSize: 20,
          font: { family: 'Inter' } // Use body font
        },
      },
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: function(context) {
            return `${context.dataset.label}: ${context.raw}`;
          }
        }
      }
    },
    maintainAspectRatio: false,
  };

  return (
    <div className="container mx-auto p-4 font-sans"> {/* Ensure body font is applied if not inherited perfectly */}
      <button 
        onClick={() => navigate(-1)} 
        className="mb-6 bg-secondary-bg hover:bg-tertiary-bg text-primary-text font-heading py-2 px-4 rounded-lg shadow-md transition-colors duration-200"
      >
        &larr; Back
      </button>
      <div className="bg-secondary-bg shadow-xl rounded-lg p-6 md:p-8"> {/* Use secondary-bg for main card, more padding */}
        <div className="flex flex-col md:flex-row gap-6 md:gap-8 mb-6 md:mb-8">
          {/* Player Info Block */}
          <div className="flex-grow">
            <h1 className="font-heading text-5xl md:text-6xl xl:text-7xl font-black text-primary-text mb-1 tracking-tight">{name}</h1> {/* Even Larger, bolder, tighter tracking */}
            <p className="font-heading text-xl text-secondary-text mb-6">Season {selectedSeason}</p>
            
            {/* Quick Stats Data Blocks */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-6">
              {[
                { label: "Position", value: position },
                { label: "Age", value: age },
                { label: "Potential", value: potential, highlight: "text-accent-green font-bold text-2xl" }, // Highlight potential
                { label: "Team", value: <Link to={`/club/${encodeURIComponent(team)}/${selectedSeason}`} className="text-accent-cyan hover:underline">{team}</Link> },
                { label: "Value", value: `€${market_value?.toLocaleString()}` },
                { label: "Wage", value: `€${wage?.toLocaleString()} / week` },
                { label: "Contract", value: `${contract_length} years` },
                { label: "Role", value: squad_role },
              ].map(stat => (
                <div key={stat.label} className="bg-tertiary-bg p-3 rounded-lg shadow">
                  <p className="text-sm font-heading text-secondary-text uppercase tracking-wider">{stat.label}</p>
                  <p className={`text-xl font-semibold text-primary-text ${stat.highlight || ''}`}>{stat.value}</p>
                </div>
              ))}
            </div>
          </div>
          {/* Radar Chart Block */}
          {attributes && radarChartData.labels && radarChartData.labels.length > 0 && (
            <div className="w-full md:w-1/2 lg:w-1/2 h-[400px] md:h-[500px] bg-tertiary-bg p-4 rounded-lg shadow-md flex flex-col mx-auto"> 
              <h3 className="font-heading text-xl font-semibold mb-3 text-center text-accent-blue">Key Attributes</h3> 
              <div className="relative flex-grow"> 
                <Radar data={radarChartData} options={radarChartOptions} /> 
              </div>
            </div>
          )}
        </div>

        {/* Detailed Attributes & Stats */}
        <div className="grid md:grid-cols-2 gap-6 md:gap-8">
          {/* Attributes Table */}
          <div>
            <h2 className="font-heading text-3xl font-semibold mb-4 text-accent-purple">Attributes</h2> {/* Heading font, accent color */}
            <div className="space-y-4">
              {attributes && attributeCategories.map(categoryName => {
                const categoryData = attributes[categoryName as keyof PlayerAttributes];
                if (!categoryData || typeof categoryData !== 'object' || Object.keys(categoryData).length === 0) {
                  return null;
                }

                // Define traditional order for attributes within categories
                const traditionalAttributeOrder: { [key: string]: string[] } = {
                  pace: ['acceleration', 'sprint_speed'],
                  shooting: ['finishing', 'long_shots', 'shot_power', 'penalties', 'volleys', 'free_kick_accuracy', 'curve'],
                  passing: ['short_passing', 'long_passing', 'vision', 'crossing', 'curve'], // Curve can also be here
                  dribbling: ['agility', 'balance', 'ball_control', 'composure', 'dribbling_control', 'reactions'], // Reactions can be here
                  defending: ['defensive_awareness', 'interceptions', 'heading_accuracy', 'sliding_tackle', 'standing_tackle'],
                  physical: ['aggression', 'jumping', 'stamina', 'strength', 'reactions'], // Reactions can also be here
                  goalkeeping: ['diving', 'handling', 'kicking', 'positioning', 'reflexes', 'speed'] // GK speed is often listed here
                  // Add more categories and their preferred attribute order as needed
                };
                
                const orderedAttributeKeys = traditionalAttributeOrder[categoryName] || Object.keys(categoryData);
                
                return (
                  <div key={categoryName} className="bg-tertiary-bg p-4 rounded-lg shadow-md">
                    <h3 className="font-heading text-xl font-semibold capitalize mb-3 text-accent-cyan">{categoryName.replace(/_/g, ' ')}</h3>
                    <ul className="space-y-1.5 text-primary-text"> {/* Changed to single column with space-y for vertical spacing */}
                      {orderedAttributeKeys.map(attrKey => {
                        const rawValue = categoryData[attrKey as keyof typeof categoryData];
                        if (rawValue === undefined) return null; // Attribute not present for this player in this category

                        const displayValue = typeof rawValue === 'number' ? parseFloat(rawValue.toFixed(1)) : rawValue; // Round to 1 decimal place
                        return (
                          <li key={attrKey} className="flex justify-between items-center text-sm"> {/* Ensure vertical alignment if lines wrap, and space distribution */}
                            <span className="capitalize text-secondary-text text-left flex-grow basis-0">{attrKey.replace(/_/g, ' ')}:</span> {/* Name, takes available space, left aligned */}
                            {/* This middle span creates the gap. It's invisible. */}
                            <span className="w-2 flex-shrink-0"></span> {/* Drastically reduced gap to w-2 (0.5rem) for testing */}
                            <span className="font-semibold text-primary-text text-right flex-grow basis-0">{displayValue}</span> {/* Value, takes available space, right aligned */}
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Stats Table */}
          <div>
            <h2 className="font-heading text-3xl font-semibold mb-4 text-accent-green">Season Stats</h2> {/* Heading font, accent color */}
            {stats ? (
              <div className="bg-tertiary-bg p-4 rounded-lg shadow-md"> {/* Use tertiary-bg, rounded-lg */}
                 <ul className="space-y-2 text-primary-text text-sm"> {/* Keep vertical spacing */}
                    <li className="flex justify-between items-center">
                      <span className="text-secondary-text text-left flex-grow basis-0">Appearances:</span>
                      <span className="w-8 flex-shrink-0"></span> {/* Fixed gap */}
                      <span className="font-semibold text-right flex-grow basis-0">{stats.appearances ?? 'N/A'}</span>
                    </li>
                    <li className="flex justify-between items-center">
                      <span className="text-secondary-text text-left flex-grow basis-0">Goals:</span>
                      <span className="w-8 flex-shrink-0"></span> {/* Fixed gap */}
                      <span className="font-semibold text-right flex-grow basis-0">{stats.goals ?? 'N/A'}</span>
                    </li>
                    <li className="flex justify-between items-center">
                      <span className="text-secondary-text text-left flex-grow basis-0">Assists:</span>
                      <span className="w-8 flex-shrink-0"></span> {/* Fixed gap */}
                      <span className="font-semibold text-right flex-grow basis-0">{stats.assists ?? 'N/A'}</span>
                    </li>
                    <li className="flex justify-between items-center">
                      <span className="text-secondary-text text-left flex-grow basis-0">Clean Sheets:</span>
                      <span className="w-8 flex-shrink-0"></span> {/* Fixed gap */}
                      <span className="font-semibold text-right flex-grow basis-0">{stats.clean_sheets ?? 'N/A'}</span>
                    </li>
                    <li className="flex justify-between items-center">
                      <span className="text-secondary-text text-left flex-grow basis-0">Fitness:</span>
                      <span className="w-8 flex-shrink-0"></span> {/* Fixed gap */}
                      <span className="font-semibold text-right flex-grow basis-0">{stats.fitness?.toFixed(0) ?? 'N/A'}%</span>
                    </li>
                    <li className="flex justify-between items-center">
                      <span className="text-secondary-text text-left flex-grow basis-0">Yellow Cards:</span>
                      <span className="w-8 flex-shrink-0"></span> {/* Fixed gap */}
                      <span className="font-semibold text-right flex-grow basis-0">{stats.yellow_cards ?? 'N/A'}</span>
                    </li>
                    <li className="flex justify-between items-center">
                      <span className="text-secondary-text text-left flex-grow basis-0">Red Cards:</span>
                      <span className="w-8 flex-shrink-0"></span> {/* Fixed gap */}
                      <span className="font-semibold text-right flex-grow basis-0">{stats.red_cards ?? 'N/A'}</span>
                    </li>
                 </ul>
              </div>
            ) : <p className="text-secondary-text">No season stats available.</p>}
            
            {/* Injury History (Placeholder) */}
            {injury_history && injury_history.length > 0 && (
              <div className="mt-6 bg-tertiary-bg p-4 rounded-lg shadow-md"> {/* Use tertiary-bg, rounded-lg */}
                <h3 className="font-heading text-xl font-semibold mb-2 text-accent-blue">Injury History</h3> {/* Heading font, accent color */}
                <p className="text-sm text-secondary-text">(Display format TBD)</p>
                {/* injury_history.map... */}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PlayerPage;
