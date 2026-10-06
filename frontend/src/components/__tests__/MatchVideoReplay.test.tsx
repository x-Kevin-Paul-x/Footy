import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import { MatchVideoReplay } from '../MatchVideoReplay';
import { getMatchRenderStatus, getMatchTimeline } from '../../services/api';

jest.mock('../../services/api', () => ({
  getMatchRenderStatus: jest.fn(), getMatchTimeline: jest.fn(),
  resolveReplayVideoUrl: (url: string) => url,
}));
const status = getMatchRenderStatus as jest.Mock;
const props = { matchId: 372, homeTeam: 'Burnley', awayTeam: 'Bournemouth', videoUrl: '/unfinished.mp4' };

beforeEach(() => {
  jest.useFakeTimers();
  status.mockReset();
  (getMatchTimeline as jest.Mock).mockResolvedValue(null);
});
afterEach(() => jest.useRealTimers());

test('refresh recovers running render and elapsed time despite an unfinished URL', async () => {
  status.mockResolvedValue({ status: 'rendering', progress: 45, stage: 'Rendering saved match', elapsed_seconds: 80, completed: false });
  const page = render(<MatchVideoReplay {...props} />);
  await waitFor(() => expect(screen.getByText('45%')).toBeInTheDocument());
  expect(document.querySelector('video')).toBeNull();
  expect(screen.getByText('Elapsed: 80s')).toBeInTheDocument();
  page.unmount();
  render(<MatchVideoReplay {...props} />);
  await waitFor(() => expect(screen.getByText('45%')).toBeInTheDocument());
  expect(document.querySelector('video')).toBeNull();
  status.mockResolvedValue({ status: 'completed', progress: 100, completed: true, video_url: '/ready.mp4' });
  await act(async () => { await jest.advanceTimersByTimeAsync(1500); });
  const video = document.querySelector('video')!;
  expect(video.getAttribute('src')).toBe('/ready.mp4');
  expect(video.controls).toBe(false);
  expect(screen.getByText('Preparing video playback')).toBeInTheDocument();
  fireEvent.loadedData(video);
  expect(video.controls).toBe(true);
  expect(screen.queryByText('Preparing video playback')).not.toBeInTheDocument();
});

test('failed render leaves loading and offers a generation retry', async () => {
  status.mockResolvedValue({ status: 'failed', progress: 0, completed: true, message: 'Encoder failed' });
  render(<MatchVideoReplay {...props} onGenerateReplay={jest.fn()} />);
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Encoder failed'));
  expect(document.querySelector('video')).toBeNull();
  expect(screen.getByRole('button', { name: /Generate 3D Broadcast Replay/ })).toBeInTheDocument();
});
