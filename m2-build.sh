#!/bin/bash

source /etc/profile.d/rvm.sh

if ! command -v rvm &> /dev/null
then
  \curl -sSL https://get.rvm.io | bash -s master
fi

ruby_version="$(rvm current)"
if [[ $ruby_version == "ruby-2.7.1" ]]; then
  echo "Up-to-date ${ruby_version}"
else
  rvm install 2.7.1
fi

cd amis-deploy
bundle install
