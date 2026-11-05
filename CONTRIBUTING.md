# Contributing to Floatbeat

Small project, few rules, all of them about keeping the history readable.

## Branches

`main` is always releasable. Every iteration happens on its own branch, even if
you are the only person working on it:

```
main
└── feat/phase-2-mpris        # one branch per iteration or feature
    ├── feat/mpris-discovery
    └── fix/artwork-cache-crash
```

| Prefix | Use for |
| --- | --- |
| `feat/` | New behaviour (a phase, a feature) |
| `fix/` | Bug fixes |
| `docs/` | Documentation only |
| `chore/` | Tooling, CI, packaging, dependencies |
| `refactor/` | No behaviour change |
| `test/` | Tests only |

Branch names use kebab-case: `feat/phase-3-parec-capture`, not
`Feature/Phase3_Capture`.

## Commits — Conventional Commits

```
<type>(<scope>): <imperative summary>

<optional body explaining why, not what>

<optional footer: Closes #12>
```

Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `perf`.
Scopes: `ui`, `audio`, `desktop`, `packaging`, `docs`, `deps`.

Examples:

```
feat(audio): capture the default sink monitor with parec
fix(ui): keep the visor inside the damage rect when the bob peaks
docs: explain why Wayland cannot position a window
perf(ui): cache the visor plate instead of stroking it every frame
```

Rules:

- Imperative mood in the summary ("add", not "added").
- Summary under 72 characters, no trailing period.
- One logical change per commit. If the message needs an "and", it is probably
  two commits.
- Never commit generated files, `.venv`, caches or build output.

## Versioning — SemVer

`MAJOR.MINOR.PATCH`, tagged as `vX.Y.Z`.

| Change | Version |
| --- | --- |
| A whole phase lands (new user-facing capability) | `MINOR` bump: 0.1.0 → 0.2.0 |
| Bug fix, no new surface | `PATCH` bump: 0.2.0 → 0.2.1 |
| Breaking public behaviour (CLI flags, config keys, API) | `MAJOR` bump |

While the project is `0.x`, `MAJOR` stays at 0 and the minor number marks
phases: 0.1 floating window, 0.2 MPRIS, 0.3 audio, 0.4 panel, 0.5 packaging.
The first stable release will be `1.0.0`.

Every release gets:

1. A `CHANGELOG.md` entry under `## [X.Y.Z] - YYYY-MM-DD`.
2. A git tag `vX.Y.Z` on `main`.
3. A GitHub release with the same notes.

## Pull requests

1. Branch from `main`.
2. Keep the PR focused; one phase or one bug.
3. Fill in: what changes, why, and how it was verified (commands and numbers for
   performance work).
4. `Closes #<issue>` in the description so the issue closes on merge.
5. Merge only when CI is green and the PR has its own review pass.

## Definition of done

- [ ] `ruff check .` passes.
- [ ] `pytest` passes.
- [ ] New behaviour is covered by a test when it is testable without a display.
- [ ] User-facing changes are in `docs/USAGE.md` or `README.md`.
- [ ] Performance-sensitive changes include before/after numbers from
      `FLOATBEAT_STATS=1`.
- [ ] `CHANGELOG.md` has an entry under `[Unreleased]`.

## Performance work

Any change that touches painting, the frame loop or audio processing must come
with measurements. The protocol is in
[`docs/BENCHMARKS.md`](BENCHMARKS.md):

```bash
FLOATBEAT_STATS=1 python -m floatbeat
```

Report CPU as a percentage of **one core** (the `top` unit) and state the thread
count, because "6 %" means very different things on a dual-core and a 16-thread
machine.
