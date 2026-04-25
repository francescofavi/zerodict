# Changelog

## 0.1.2 (2026-04-25)

### Documentation

* Generate full public and internal documentation set (release-cycle Stage 3)
* Add Quality pipeline section to `docs/DEVELOPMENT.md` (ruff/mypy/bandit/vulture commands and pre-commit guidance)
* Align `docs/ARCHITECTURE.md` with current code: corrected `set_many` backup description, added security constants table, refreshed module/data-flow sections
* Fix incorrect array-element example for `move()` in `docs/API_REFERENCE.md` (`delete_path` pops the element; the previous example claimed it was set to `None`)
* Documentation polish + add `SECURITY.md` (#5)
* Add project logo to README
* Fix documentation and GitHub Actions configuration (#4)
* Fix badges, add metadata badges, switch to absolute documentation links for PyPI rendering

### Build

* Exclude `.github/`, `release-please-config.json`, `.release-please-manifest.json`, `.gitignore`, `uv.lock`, `.coverage`, `/build/**`, and `/.scripts/**` from sdist
* Exclude `.internal_docs/` from sdist (internal-only maintainer documentation)
* Track `.internal_docs/` in git via explicit whitelist in `.gitignore`
* Add `Programming Language :: Python :: 3 :: Only` classifier
* Add `Topic :: Software Development :: Libraries :: Python Modules` classifier
* Add Python 3.14 to test matrix and classifiers

## 0.1.1 (2026-03-30)

### Documentation

* Fix badge rendering on PyPI (added .svg extension)
* Add Status, Typed, Dependencies, and Code style badges
* Convert relative doc links to absolute GitHub URLs for PyPI compatibility

## 0.1.0 (2026-03-01)


### Features

* initial release ([68c3596](https://github.com/francescofavi/zerodict/commit/68c3596389a5fdc0392def551d6bd00bbea7bc65))
