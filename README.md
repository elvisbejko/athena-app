# Why not `settings.json`
Paths in windows use backward slashes. A valid `json` requires forward ones.
To have the user not care about this and avoid battling the `json` with 
pre-processing, we migrate to .toml files for configuration. The only caveat
with `toml` is that it needs single quotes for paths at least.
