import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import LeagueOverview from "../LeagueOverview";
import * as api from "../../services/api";

jest.mock("../../services/api");

const mockedApi = api as jest.Mocked<typeof api>;

const mockReport: any = {
  season_year: 2025,
  champions: "Manchester United",
  champions_manager: {
    name: "Erik Ten Hag",
    experience: 10,
    formation: "4-2-3-1",
    transfer_success_rate: 0.5,
    market_trends: {},
    team: "Manchester United",
  },
  table: [
    [
      "Manchester United",
      {
        points: 81,
        w: 25,
        d: 6,
        l: 7,
        gf: 103,
        ga: 49,
        gd: 54,
        played: 38,
        form: "WWLWW",
      },
    ],
    [
      "Crystal Palace",
      {
        points: 80,
        w: 25,
        d: 5,
        l: 8,
        gf: 118,
        ga: 70,
        gd: 48,
        played: 38,
        form: "LLLLL",
      },
    ],
  ],
  transfers: {
    total_transfers: 0,
    biggest_spenders: [],
    most_active: [],
    all_completed_transfers: [],
  },
  best_players: [],
  season_stats: {
    total_matches: 380,
    total_goals: 1000,
    average_goals_per_match: 2.63,
    best_attack: ["Luton", { gf: 130 }],
    best_defense: ["Liverpool", { ga: 66 }],
  },
  all_teams_details: [
    {
      id: "manu",
      name: "Manchester United",
      crest: null,
      manager_name: "Erik Ten Hag",
      manager_formation: "4-2-3-1",
      budget: 120,
      squad_strength: 90,
      players: [],
      financial_summary: { annual_revenue: 0, annual_expenses: 0, financial_health: "good" },
      team_season_stats: {},
    },
    {
      id: "cp",
      name: "Crystal Palace",
      crest: null,
      manager_name: "Oliver",
      manager_formation: "4-3-3",
      budget: 110,
      squad_strength: 85,
      players: [],
      financial_summary: { annual_revenue: 0, annual_expenses: 0, financial_health: "fair" },
      team_season_stats: {},
    },
  ],
};

describe("LeagueOverview", () => {
  beforeEach(() => {
    mockedApi.getAvailableSeasons.mockResolvedValue([2025]);
    mockedApi.getSeasonReportData.mockResolvedValue(mockReport);
  });

  it("renders standings and financial overview from season report", async () => {
    render(<MemoryRouter><LeagueOverview /></MemoryRouter>);

    await waitFor(() => {
      expect(screen.getByText(/League Overview/i)).toBeInTheDocument();
    });

    // Teams from mock — use findAllByText because the team name appears multiple times in the rendered output
    const manuMatches = await screen.findAllByText("Manchester United");
    expect(manuMatches.length).toBeGreaterThanOrEqual(1);
    const cpMatches = await screen.findAllByText("Crystal Palace");
    expect(cpMatches.length).toBeGreaterThanOrEqual(1);

    // Points shown
    expect(screen.getByText("81")).toBeInTheDocument();
    expect(screen.getByText("80")).toBeInTheDocument();

    // Financial items (budget numbers)
    expect(screen.getByText("120")).toBeInTheDocument();
    expect(screen.getByText("110")).toBeInTheDocument();
  });
});
