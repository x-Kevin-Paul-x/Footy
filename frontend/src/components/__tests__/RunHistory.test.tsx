import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import RunHistory from '../../pages/RunHistory';

jest.mock('../../services/api', () => ({
  getSimulationRuns: jest.fn().mockResolvedValue([{ run_id: 'run_one', created_at: '2026-10-13', status: 'completed', matches_played: 380, seasons: [2026] }]),
  getCampaignSnapshot: jest.fn().mockResolvedValue({ teams: [{ name: 'Club one', players: [{ name: 'Player one' }], finances: { budget: 120_000_000 } }] }),
  getCampaignFinances: jest.fn().mockResolvedValue({ opening_balance: 100_000_000, closing_balance: 120_000_000, net_cashflow: 20_000_000,
    entries: [{ entry_number: 1, season_year: 2026, category: 'attendance', amount: 20_000_000, balance: 120_000_000, description: 'Recorded gate receipts' }] }),
}));

test('selecting a saved run exposes its club and reconciled cash ledger', async () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><RunHistory /></QueryClientProvider>);
  await waitFor(() => expect(screen.getByRole('combobox', { name: 'Simulation' })).toBeInTheDocument());
  fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Simulation' }));
  fireEvent.click(await screen.findByRole('option', { name: /2026-10-13.*completed/ }));
  fireEvent.click(await screen.findByRole('button', { name: 'Club one' }));
  expect(await screen.findByRole('table', { name: 'Club cash transactions' })).toBeInTheDocument();
  expect(screen.getByText('Recorded gate receipts')).toBeInTheDocument();
  expect(screen.getByText(/Opening £100,000,000/)).toHaveTextContent('Closing £120,000,000');
  client.clear();
});
