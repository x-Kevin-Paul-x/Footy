import { render, screen, waitFor } from '@testing-library/react';
import LiveSeasonUpdates from '../LiveSeasonUpdates';

let mockRun = { run_id: 'externally-started', season_year: 2026, status: 'running', matches_played: 20, total_matches: 380 };
const mockRefresh = jest.fn().mockResolvedValue(undefined);
const mockQueryClient = { invalidateQueries: jest.fn() };
jest.mock('@tanstack/react-query', () => ({
  useQuery: () => ({ data: mockRun }),
  useQueryClient: () => mockQueryClient,
}));
jest.mock('../../store/simulationStore', () => ({
  useSimulationStore: (selector: any) => selector({ refreshLiveSeason: mockRefresh }),
}));
jest.mock('../../services/api', () => ({ getCurrentSimulationRun: jest.fn() }));

test('follows an external run, refreshes new saved batches, and refreshes completion', async () => {
  const { rerender } = render(<LiveSeasonUpdates />);
  await waitFor(() => expect(mockRefresh).toHaveBeenCalledTimes(1));
  expect(screen.getByRole('status')).toHaveTextContent('20/380 matches saved');
  mockRun = { ...mockRun };
  rerender(<LiveSeasonUpdates />);
  expect(mockRefresh).toHaveBeenCalledTimes(1);
  mockRun = { ...mockRun, matches_played: 40 };
  rerender(<LiveSeasonUpdates />);
  await waitFor(() => expect(mockRefresh).toHaveBeenCalledTimes(2));
  expect(screen.getByRole('status')).toHaveTextContent('40/380 matches saved');
  mockRun = { ...mockRun, matches_played: 380, status: 'completed' };
  rerender(<LiveSeasonUpdates />);
  await waitFor(() => expect(mockRefresh).toHaveBeenCalledTimes(3));
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
  expect(mockQueryClient.invalidateQueries).toHaveBeenCalledWith({ queryKey: ['matchesBySeason'] });
});
