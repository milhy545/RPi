#!/bin/bash
SHA=$(git rev-parse HEAD)
echo "{}" > conductor/ci/receipts/${SHA}-receipt.json
git add conductor/ci/receipts/${SHA}-receipt.json
git commit --amend --no-edit
