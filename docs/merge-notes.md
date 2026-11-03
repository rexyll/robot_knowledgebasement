# Local branch integration notes

## Integration summary

- Target branch: `main`
- Source branch: `local`
- Source head at integration: `c8bb4c6f889dd5d72834913c57606f326b3faa84`
- Main head used as the integration base: `caa0b596b270df870aef080a0d784492ef02132c`
- Strategy: create a merge commit with both branch heads as parents, while placing the local knowledge notes into the main-branch taxonomy.

## Organization

Existing main categories retained: robots, sensors, actuators, navigation, manipulation and troubleshooting.

New categories added because local contained substantial independent knowledge in these domains: mechanics, power, safety, computing, software, algorithms, architecture, parameters, ecosystem, projects, getting-started, examples and maps.

Vault administration material (writing guidelines, task plan, glossary and external-link ledger) is kept in `docs/` or at the knowledge root instead of being mixed into technical articles.

## Preservation

Local Markdown documents are moved without rewriting their substantive text. Their Chinese titles, metadata and Obsidian WikiLinks are retained to protect vault navigation. New README files provide the GitHub-friendly directory indexes.

Obsidian application settings are kept where useful (`.obsidian/app.json`, `.obsidian/appearance.json`, `.obsidian/core-plugins.json`). The machine/session-specific `.obsidian/workspace.json` is intentionally not merged.

No main-branch knowledge article is deleted or replaced during this integration. The existing differential-drive odometry and LiDAR checklist pages remain in place alongside the more detailed local articles.
