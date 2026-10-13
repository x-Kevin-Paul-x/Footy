import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Alert, Box, MenuItem, TextField, Typography, Table, TableHead, TableRow, TableCell, TableBody } from '@mui/material';
import { getSimulationRuns, getCampaignSnapshot, getCampaignFinances } from '../services/api';

const money = (amount: number) => new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 0 }).format(amount);

export default function RunHistory() {
  const [selectedRun, setSelectedRun] = useState('');
  const [selectedSeason, setSelectedSeason] = useState<number | undefined>();
  const [selectedTeam, setSelectedTeam] = useState('');
  const runs = useQuery({ queryKey: ['simulationRuns'], queryFn: getSimulationRuns });
  const run = runs.data?.find(item => item.run_id === selectedRun);
  const season = selectedSeason ?? run?.seasons[0];
  const snapshot = useQuery({ queryKey: ['campaignSnapshot', selectedRun, season],
    queryFn: () => getCampaignSnapshot(selectedRun, season!), enabled: Boolean(selectedRun && season) });
  const finances = useQuery({ queryKey: ['campaignFinances', selectedRun, selectedTeam],
    queryFn: () => getCampaignFinances(selectedRun, selectedTeam), enabled: Boolean(selectedRun && selectedTeam) });
  return <Box>
    <Typography variant="h4" mb={2}>Saved campaigns</Typography>
    <Typography color="text.secondary" mb={3}>Compare retained squads and finances from each simulation.</Typography>
    {(runs.isError || snapshot.isError || finances.isError) && <Alert severity="error">Unable to load saved campaign data.</Alert>}
    <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 3 }}>
      <TextField select label="Simulation" value={selectedRun} sx={{ minWidth: 300 }}
        onChange={event => { setSelectedRun(event.target.value); setSelectedSeason(undefined); setSelectedTeam(''); }}>
        {(runs.data ?? []).map(item => <MenuItem key={item.run_id} value={item.run_id}>{item.created_at.slice(0, 10)} · {item.status} · {item.matches_played} matches</MenuItem>)}
      </TextField>
      {run && <TextField select label="Season" value={season ?? ''} sx={{ minWidth: 120 }} onChange={event => setSelectedSeason(Number(event.target.value))}>
        {run.seasons.map(year => <MenuItem key={year} value={year}>{year}</MenuItem>)}
      </TextField>}
    </Box>
    {run && run.seasons.length === 0 && <Alert severity="info">This run has no saved campaign snapshot yet.</Alert>}
    {snapshot.data && <>
      <Table aria-label="Saved campaign clubs">
        <TableHead><TableRow><TableCell>Club</TableCell><TableCell>Squad</TableCell><TableCell align="right">Cash balance</TableCell></TableRow></TableHead>
        <TableBody>{snapshot.data.teams.map(team => <TableRow key={team.name}>
          <TableCell><button onClick={() => setSelectedTeam(team.name)}>{team.name}</button></TableCell>
          <TableCell>{team.players.length}</TableCell><TableCell align="right">{money(team.finances.budget)}</TableCell>
        </TableRow>)}</TableBody>
      </Table>
      <Typography color="text.secondary" mt={2}>Select a club to inspect its cash transactions.</Typography>
    </>}
    {finances.data && <Box mt={4}>
      <Typography variant="h6">{selectedTeam} cash ledger</Typography>
      <Typography mb={2}>Opening {money(finances.data.opening_balance)} · Net movement {money(finances.data.net_cashflow)} · Closing {money(finances.data.closing_balance)}</Typography>
      <Box sx={{ overflowX: 'auto', maxHeight: 500 }}>
        <Table aria-label="Club cash transactions" stickyHeader size="small">
          <TableHead><TableRow><TableCell>Season</TableCell><TableCell>Transaction</TableCell><TableCell>Description</TableCell><TableCell align="right">Amount</TableCell><TableCell align="right">Balance</TableCell></TableRow></TableHead>
          <TableBody>{finances.data.entries.map(entry => <TableRow key={entry.entry_number}>
            <TableCell>{entry.season_year}</TableCell><TableCell>{entry.category.replace(/_/g, ' ')}</TableCell><TableCell>{entry.description}</TableCell>
            <TableCell align="right">{money(entry.amount)}</TableCell><TableCell align="right">{money(entry.balance)}</TableCell>
          </TableRow>)}</TableBody>
        </Table>
      </Box>
    </Box>}
    {selectedTeam && snapshot.data && <Box mt={4} sx={{ overflowX: 'auto' }}>
      <Typography variant="h6">Registered players</Typography>
      <Table size="small" aria-label="Saved player contracts and availability">
        <TableHead><TableRow><TableCell>Player</TableCell><TableCell>Position</TableCell><TableCell>Availability</TableCell><TableCell>Contract</TableCell><TableCell>Release clause</TableCell><TableCell>Sell-on terms</TableCell><TableCell>Loan</TableCell></TableRow></TableHead>
        <TableBody>{snapshot.data.teams.find(team => team.name === selectedTeam)?.players.map(player => <TableRow key={player.name}>
          <TableCell>{player.name}</TableCell><TableCell>{player.position}</TableCell>
          <TableCell>{player.injury_days ? `${player.injury_days} days injured` : player.suspended_matches ? `${player.suspended_matches} match ban` : 'Available'}</TableCell>
          <TableCell>{player.contract_length ?? '—'} years</TableCell><TableCell>{player.release_clause ? money(player.release_clause) : 'None'}</TableCell>
          <TableCell>{player.sell_on_clause ? `${Math.round(player.sell_on_clause.percentage * 100)}% to ${player.sell_on_clause.beneficiary}` : 'None'}</TableCell>
          <TableCell>{player.loan_contract ? `From ${player.loan_contract.owner}, until day ${player.loan_contract.expires_day}` : 'None'}</TableCell>
        </TableRow>)}</TableBody>
      </Table>
    </Box>}
    {!runs.isLoading && runs.data?.length === 0 && <Alert severity="info">Run a season to create your first saved campaign.</Alert>}
  </Box>;
}
