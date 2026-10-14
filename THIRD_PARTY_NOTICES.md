# Third-party notices

The root MIT license applies to Footy's original code. Dependency and upstream licenses retain their own terms.

- TiKick source under `backend/third_party/tikick` is Apache License 2.0; retain its [included license](backend/third_party/tikick/LICENSE). The integrated pretrained actor has separate upstream provenance documented in [checkpoint verification](docs/tikick_checkpoint_verification.md); Footy's MIT badge does not grant new rights to external weights.
- Google Research Football is an external native dependency. Consult its [upstream license](https://github.com/google-research/football/blob/master/LICENSE) and distribution instructions when packaging native binaries.
- The new manager checkpoints `dqn_seed_42.pt`, `dqn_seed_43.pt`, and `dqn_seed_44.pt` were generated from Footy's synthetic management environment. Their training configuration, logs and hashes are in the model manifest and `docs/evidence/`. Provenance of the older `dqn_best.pt` is not inferred from its filename.
- The calibration reference uses Football-Data's [2023/24 results dataset](https://www.football-data.co.uk/mmz4281/2324/E0.csv). Only derived aggregates and its checksum are included in the evidence report; the source dataset is not redistributed.
- Club names identify the simulated teams. External brands, screenshots and upstream model assets are not represented as original Footy intellectual property.
- The optional commentary stadium ambience is credited to cuauh89 under Creative Commons Attribution 3.0. Retain [the asset attribution](backend/commentary/assets/ATTRIBUTION.md) with redistributed commentary videos.
