#!/usr/bin/env falcon-host
# frozen_string_literal: true
# $ PORT=8888 bundle exec ./falcon.rb

load :rack, :supervisor

rack 'amis.moedict' do
  scheme 'http'
  protocol { ::Async::HTTP::Protocol::HTTP1 }
  port     { ENV['PORT'] }
  endpoint { ::Async::HTTP::Endpoint.parse("http://localhost:#{port}") }
end

supervisor do
  ipc_path { ::File.expand_path("amis-moedict-supervisor.ipc", "/tmp") }
end
