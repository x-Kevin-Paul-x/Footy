const root = document.documentElement;
const toggle = document.getElementById('theme-toggle');

function syncThemeControl() {
  const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
  toggle.setAttribute('aria-label', `Switch to ${next} mode`);
  document.getElementById('theme-label').textContent = `${next === 'light' ? 'Light' : 'Dark'} mode`;
  document.querySelector('meta[name="theme-color"]').content = root.dataset.theme === 'light' ? '#FAA968' : '#06101E';
}
toggle.addEventListener('click', () => {
  root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
  try { localStorage.setItem('footy_theme_mode', root.dataset.theme); } catch { /* Switching still works without persistence. */ }
  syncThemeControl();
});
syncThemeControl();
function syncNavigation() {
  const section = ['#match', '#benchmarks', '#evidence'].includes(location.hash) ? location.hash : '#match';
  document.querySelectorAll('.finnova-nav-item').forEach(link => {
    const active = link.getAttribute('href') === section;
    link.classList.toggle('active', active);
    if (active) link.setAttribute('aria-current', 'location');
    else link.removeAttribute('aria-current');
  });
}
window.addEventListener('hashchange', syncNavigation);
syncNavigation();
async function readReport(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Report unavailable: ${response.status}`);
  return response.json();
}
const policyLabels = {
  trained_dqn_seed_42: 'DQN · seed 42', trained_dqn_seed_43: 'DQN · seed 43',
  trained_dqn_seed_44: 'DQN · seed 44', trained_dqn_best: 'Previous DQN',
  random: 'Random valid', do_nothing: 'Do nothing', youth_focus: 'Youth focused', rule_based: 'Rule based',
};
readReport('manager_evaluation.json').then(report => {
  const best = Object.entries(report.policies).reduce((a, b) => b[1].avg_reward > a[1].avg_reward ? b : a)[0];
  const rows = Object.entries(report.policies).map(([name, value]) => {
    const row = document.createElement('tr');
    if (name === best) row.classList.add('best-policy');
    [policyLabels[name] || name.replaceAll('_', ' '), value.avg_reward.toFixed(2), value.avg_points.toFixed(2), value.avg_position.toFixed(2)].forEach((text, index) => {
      const cell = document.createElement('td');
      cell.textContent = text;
      if (index === 0 && name === best) {
        const badge = document.createElement('span');
        badge.className = 'policy-tag';
        badge.textContent = 'Best reward';
        cell.append(badge);
      }
      row.append(cell);
    });
    return row;
  });
  document.getElementById('policies').replaceChildren(...rows);
  document.getElementById('finding').textContent = 'The rule-based baseline scored highest in this sample. The DQN runs did not establish an advantage over random decisions.';
}).catch(() => {
  document.getElementById('policies').firstElementChild.firstElementChild.textContent = 'Results could not be loaded. Read the verification report below.';
  document.getElementById('finding').textContent = 'The complete results are available in the project evidence folder.';
});
readReport('calibration.json').then(report => {
  const simulated = report.simulation.goals_per_match.toFixed(2);
  const reference = report.reference.goals_per_match.toFixed(2);
  document.getElementById('sim-goals').textContent = simulated;
  document.getElementById('reference-goals').textContent = reference;
  document.getElementById('calibration').textContent = `The recorded GRF season averaged ${simulated} goals per match, compared with ${reference} in the real reference. Scoring calibration remains an open research task.`;
}).catch(() => {
  document.getElementById('calibration').textContent = 'The season comparison is available in the project verification report.';
});
