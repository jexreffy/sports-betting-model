---
name: jexreffy-pr-ready
description: >-
  When jexreffy says a feature is complete and ready for a PR: review first
  (Bugbot and/or CI), then open a PR. Never skip review. Never target main with
  a direct push.
---

# PR-ready (review, then PR)

Use when he says the work is complete, ready to PR, ready to land, or "open the PR."

## Never

- Commit, merge, rebase onto, or push `main`, `staging`, or `development` (treat them as protected even if the remote does not)
- Open a PR before a review pass
- Approve, merge, or auto-merge a PR — jexreffy does that himself. You may evaluate and comment only.

## Order

1. Confirm you are on a feature branch, not `main` / `staging` / `development`.
2. Run the project's **automated** test suite (and lint if present). Must be green. Do not start review if tests fail.
3. Run **Bugbot** on `branch changes` (follow the review-bugbot skill). If Bugbot cannot run, do a concise self-review of the diff and say so.
4. Report findings. Fix clear defects unless he says ship anyway.
5. If review caused code changes, run the **automated** suite again. Must be green.
6. Commit only if he already approved committing, or this message is the approval to land.
7. `git push -u origin HEAD` and `gh pr create` into the default branch. Return the PR URL.

This gate is the repo's automated suite only (pytest, ruff, package tests, CI unit job). A future AI-led QA bot that plays a full human regression package is **not** part of this rule.

GitHub Actions on the PR is extra coverage, not a substitute for the pre-PR automated run.
