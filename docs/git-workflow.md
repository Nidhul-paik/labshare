# Git workflow

## First-time setup
```bash
git init -b main
git add .
git commit -m "chore: initial LabShare project"
git remote add origin <your-repo-url>
git push -u origin main
```
`.gitignore` keeps databases, saved settings and `received/` out of the repository, and `.gitattributes` keeps
`.bat` files CRLF and `.sh` files LF so the scripts work on both systems.

## Branches
- `main`: always passes the tests. `feature/<name>`, `fix/<name>`, `docs/<name>` for work.
- Merge by pull request after `python -m unittest discover` passes (CI runs it on Ubuntu and Windows).

## Commit messages (Conventional Commits)
`feat: add inbox preview`, `fix: reconnect after host restart`, `docs: windows hotspot notes`, `test: cover token check`.

## Releases
Update `__version__` in `src/labshare/__init__.py` and `CHANGELOG.md`, then
`git tag -a v1.0.0 -m "LabShare 1.0.0" && git push --tags`.
