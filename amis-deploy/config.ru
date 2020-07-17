# frozen_string_literal: true

class SetDictMeta
  def initialize(app)
    @app = app
  end

  DICT_MAPPING = {
    p: '方敏英字典',
    m: '潘世光阿法',
    s: '蔡中涵大辭典',
  }

  def call(env)
    status, headers, _ = @app.call(env)

    puts env["REQUEST_URI"]
    body = File.read('index.html')
    # binding.irb

    [status, headers, [body]]
  end
end

use Rack::Static, urls: {
                          "/2017-Amis-Logo.png" => "2017-Amis-Logo.png",
                          "/AmisMoedict-FB.png" => "AmisMoedict-FB.png",
                          "/about.html"         => "about.html",
                          "/icon.png"           => "icon.png",
                          "/favicon.png"        => "favicon.png",
                          "/manifest.appcache"  => "manifest.appcache",
                          "/styles.css"         => "styles.css",
                        },
                  root: __dir__

use Rack::Static, urls: [
                          "/css",
                          "/fonts",
                          "/images",
                          "/js",
                          "/m",
                          "/old-s",
                          "/p",
                          "/s",
                        ],
                  root: __dir__

use SetDictMeta

run lambda{|env| [404, [], ["Not Found"]]}
