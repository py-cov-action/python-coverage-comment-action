#!/bin/sh
# Usage $0 {repo/owner} {filename} {commit_message}
# Stores the content of stdin in a file named {filename} in the wiki of
# the provided repo
# Reads envvar GITHUB_TOKEN

set -eux

stdin=$(cat -)
repo_name=${1}
filename=${2}
commit_message=${3}
dir=$(mktemp -d)
cd $dir

git clone "https://${GITHUB_TOKEN}@github.com/${repo_name}.wiki.git" .
echo $stdin > ${filename}
git add ${filename}
git commit -m $commit_message
git push -u origin
