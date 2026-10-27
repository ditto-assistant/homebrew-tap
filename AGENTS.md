# Tap maintenance

Keep formula updates tied to published npm artifacts. Run the generator, review
its diff, then run actual `brew install`, `brew test`, and `brew audit` against
the candidate tap tree. CI covers macOS and Linux. Never run connected/inference
commands in tests. Keep Homebrew ownership markers and check future CLI updaters
honor them. Use PRs and current-head review. Do not add publishing tokens or
cross-repository app grants as a workaround. Prepare-update only exports a patch.
