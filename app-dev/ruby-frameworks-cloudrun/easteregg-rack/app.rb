# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

require 'bundler/setup'
require 'rack'

class App
  def call env
     return [200, {}, ["👋 Hello from just Rack/WEBrick"]]
  end
end

Rack::Handler::WEBrick.run(App.new, :Host => "0.0.0.0", :Port => ENV['PORT'].to_i || 8080)
