# Ditto Homebrew tap

Install the `heyditto` command from Ditto's company tap:

```sh
brew tap ditto-assistant/tap
brew install ditto-assistant/tap/heyditto
heyditto --version
heyditto --help
heyditto review local --preview
```

The preview inspects your current Git checkout without login, upload or inference.
Actual reviews and other connected commands require your own Ditto login and may
incur usage charges. This is a company tap, with no Homebrew core submission or
acceptance implied. macOS and Linux are validation targets; see Actions for the
specific runner architectures actually tested.

The formula installs the published `@heyditto/cli` npm tarball, checks SHA256,
uses its exact source commit's checksummed dependency lock and runs `npm ci`
with production dependencies and lifecycle scripts disabled. npm verifies each
locked dependency's integrity. Optional platform dependencies remain optional.
Only `heyditto` is linked, avoiding the macOS `/usr/bin/ditto` command.
Node is provided by Homebrew `node@24`, with the CLI's supported minimum checked
at install time. The wrapper uses that Node explicitly, regardless of shell PATH.

## Upgrades, collisions and removal

```sh
brew update
brew upgrade ditto-assistant/tap/heyditto
brew test ditto-assistant/tap/heyditto
brew uninstall ditto-assistant/tap/heyditto
brew untap ditto-assistant/tap
```

If an npm installation already owns `heyditto`, inspect `command -v heyditto`
and `npm list --global @heyditto/cli` first. Choose one owner; remove the npm
installation with its own package manager before linking Homebrew. Do not use
`brew link --overwrite` to hide the collision. Uninstall leaves your account
configuration and Homebrew dependencies alone.

Homebrew owns the installed files and upgrades. The launcher sets
`HEYDITTO_INSTALL_METHOD=homebrew` and `HEYDITTO_NO_UPDATE=1`; `libexec/INSTALL_METHOD`
also contains `homebrew`. CLI updater work under DITTO-1502 must honor this
contract (or detect the Homebrew Cellar) and recommend `brew upgrade
 ditto-assistant/tap/heyditto` rather than run npm or write into the keg. Version
2.33.0 has no automatic package updater. Future releases must pass the offline
checks and have their updater ownership reviewed before promotion.

## Release maintenance

Owner: Ditto CLI maintainers (Peyton Spencer); tracked by DITTO-1546.

1. Finish the CLI semantic-release workflow and confirm the exact version exists
   on npm. Never update from an unmerged branch, anticipated version or tag alone.
2. In a fresh tap branch run `python3 scripts/update-formula.py X.Y.Z`. It checks
   npm SHA512, the published package metadata and its source lockfile, then pins
   source SHA256, lockfile SHA256, source commit and supported Node minimum.
   It refuses changed executable layout, license or unsupported Node conventions.
3. Review the actual package changes, including updater ownership and any native
   dependency requirements. Install and run `brew test` and `brew audit`.
4. Push a PR, wait for macOS/Linux install tests and Ditto Review, then merge at
   the validated head. Publication to npm must precede promotion in the tap.

The `Prepare published release update` workflow accepts an exact published
version and uploads a patch for review. It deliberately needs only the built-in
read-only GitHub token: no cross-repository PAT, app grant or npm publishing
credential. Download/apply the patch in a fresh branch and open a PR. It does
not push, merge, publish npm or activate unattended formula updates. An upstream
release hook can later invoke this workflow only with separately authorized
cross-repository credentials; none were created for this task.

CI installs the candidate tap from its checked-out PR tree and exercises the
installed command, including a disposable Git preview with Node networking
blocked, without login or paid inference. It also uninstalls the package and
checks that the linked executable disappeared. No Depot workflow exists here.

## Rollback

Before upgrading, `brew pin heyditto` can hold the current version (unpin before
an intended upgrade). To restore an earlier release, revert the formula update
in a PR, preserving that release's artifact and lock checksums; validate and merge
it, then run `brew update && brew reinstall ditto-assistant/tap/heyditto`.
`brew upgrade` alone will not downgrade. Homebrew's cached old keg is not a
reliable rollback plan after cleanup. Never change npm's published artifact or
force-push tap history. Emergency local rollback can install a reviewed historical
formula through a separate local tap, keeping its dependency pins together.

## Local validation in an isolated prefix

A secondary Homebrew checkout under ignored `.tmp/` keeps this task's keg,
symlinks and tap away from the workstation's main Homebrew installation.
Nonstandard prefixes may build dependencies from source. The implementation
validation used a checksum-verified official Node 24.22.1 archive in that prefix,
then `brew install --ignore-dependencies --build-from-source` for the formula;
this checks the real formula and command but does not prove normal Homebrew
Node dependency installation. CI uses normal dependency resolution in standard
prefixes to cover that separate path. No account configuration is copied.
