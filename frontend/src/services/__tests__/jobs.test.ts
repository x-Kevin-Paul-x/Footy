const mockPost = jest.fn();
const mockGet = jest.fn();
jest.mock('axios', () => ({
  __esModule: true,
  default: { create: () => ({ post: (...args: unknown[]) => mockPost(...args), get: (...args: unknown[]) => mockGet(...args), interceptors: { request: { use: jest.fn() } } }) },
}));

import { runMlEvaluation, resolveApiBaseUrl, resolveSimulationSocketUrl, resumeMlEvaluation } from '../api';

beforeEach(() => {
  mockPost.mockReset();
  mockGet.mockReset();
  window.localStorage.clear();
  window.sessionStorage.clear();
});

test('evaluation follows acceptance through queued status to the result', async () => {
  mockPost.mockResolvedValue({ data: { job_id: 'job-1', status: 'accepted' } });
  mockGet.mockResolvedValueOnce({ data: { job_id: 'job-1', status: 'queued' } })
    .mockResolvedValueOnce({ data: { job_id: 'job-1', status: 'completed', result: { report_name: 'result.json' } } });
  const progress = jest.fn();
  const report = await runMlEvaluation({ models: ['dqn_best.pt'] }, progress);
  expect(report.report_name).toBe('result.json');
  expect(progress.mock.calls.map(call => call[0])).toEqual(['queued', 'completed']);
  expect(window.sessionStorage.getItem('footy_ml_job')).toBeNull();
});

test('refresh resumes an accepted job and reports failure', async () => {
  window.sessionStorage.setItem('footy_ml_job', 'previous-job');
  mockGet.mockResolvedValue({ data: { job_id: 'previous-job', status: 'failed', error_message: 'Model incompatible' } });
  await expect(resumeMlEvaluation(jest.fn())).rejects.toThrow('Model incompatible');
  expect(window.sessionStorage.getItem('footy_ml_job')).toBeNull();
});

test('HTTP and WebSocket resolve the updated connection setting', () => {
  window.localStorage.setItem('footy_api_url', 'https://example.test:8443');
  expect(resolveApiBaseUrl()).toBe('https://example.test:8443');
  expect(resolveSimulationSocketUrl()).toBe('wss://example.test:8443/ws');
});
