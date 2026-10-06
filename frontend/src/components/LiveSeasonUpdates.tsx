import { useEffect, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Box, LinearProgress, Typography } from '@mui/material';
import { getCurrentSimulationRun } from '../services/api';
import { useSimulationStore } from '../store/simulationStore';

/** Follow committed batches, including seasons started outside the browser. */
export default function LiveSeasonUpdates() {
  const queryClient = useQueryClient();
  const refresh = useSimulationStore(state => state.refreshLiveSeason);
  const lastRefresh = useRef('');
  const { data: run } = useQuery({
    queryKey: ['liveSimulationRun'],
    queryFn: getCurrentSimulationRun,
    refetchInterval: query => ['running', 'cancelling'].includes(query.state.data?.status ?? '') ? 2000 : 10000,
    refetchIntervalInBackground: true,
  });

  useEffect(() => {
    if (!run || run.status === 'ready') return;
    const revision = `${run.run_id}:${run.matches_played}:${run.status}`;
    if (revision === lastRefresh.current) return;
    let cancelled = false;
    refresh().then(() => {
      if (cancelled) return;
      lastRefresh.current = revision;
      for (const key of ['seasonReport', 'matchesBySeason', 'allSeasonsOverview', 'financialSummary', 'transferActivity']) {
        queryClient.invalidateQueries({ queryKey: [key] });
      }
    }).catch(error => console.error('Unable to refresh saved season batch', error));
    return () => { cancelled = true; };
  }, [run?.run_id, run?.matches_played, run?.status, refresh, queryClient]);

  if (!run || !['running', 'cancelling'].includes(run.status)) return null;
  const progress = run.total_matches > 0 ? run.matches_played / run.total_matches * 100 : 0;
  return <Box sx={{ mb: 2, p: 2, borderRadius: 3, bgcolor: 'background.paper' }} role="status">
    <Typography fontWeight={700} mb={1}>
      Season {run.season_year} in progress · {run.matches_played}/{run.total_matches} matches saved
    </Typography>
    <LinearProgress variant="determinate" value={progress} />
    <Typography variant="body2" mt={1}>Standings and results update automatically after each batch.</Typography>
  </Box>;
}
