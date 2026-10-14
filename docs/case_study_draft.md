# What the Footy reliability update taught me

Footy combines season management with Google Research Football and recorded replay artifacts. This update focused on making its claims reproducible: accepted jobs now have persisted identities, saves use SQLite's backup API, historical campaign data has run-scoped snapshots, and native benchmarks dispatch real worker pools.

The manager DQN results were less convincing than the interface suggested. Three new seeded training runs, evaluated against 30 held-out scenarios each, did not establish an advantage over random valid actions. The rule-based baseline had the highest mean reward. Publishing the raw episodes and training curves makes that finding more useful than an unsupported claim that reinforcement learning improved results.

Native verification also found a useful distinction: identical physics can still produce different archive hashes when one entry point records different policy metadata. Making provenance consistent allowed the direct and pooled paths to use the same strict archive checks. The tests compare multiple seeds and populated worker topologies rather than trusting a worker-count label in a sequential benchmark.

The economy soak found that attendance was recorded without crediting cash and that cheap squads accumulated excessive funds. The cash ledger now explains each movement, loans move and return players, and year-end surplus distributions limit transfer-fund inflation. Remaining work includes scoring calibration, native substitutions and reconstruction of live campaign state after interruption.

This is a draft for a future project post; it has not been published externally.
