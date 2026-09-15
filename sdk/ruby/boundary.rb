require 'json'

module Boundary
  class ValidationError < StandardError; end

  def self.validate(response, schema_class)
    # response can be Net::HTTPResponse or Faraday::Response
    status = response.respond_to?(:status) ? response.status : response.code.to_i
    body = response.body

    if status < 200 || status >= 300
      raise ValidationError, "Boundary: unexpected status code #{status}"
    end

    begin
      parsed = JSON.parse(body, symbolize_names: true)
      # In Ruby, we just instantiate the class with the parsed hash
      # Assumes schema_class has an initializer taking a hash
      schema_class.new(parsed)
    rescue JSON::ParserError => e
      raise ValidationError, "Boundary: schema validation failed (invalid JSON): #{e.message}"
    rescue => e
      raise ValidationError, "Boundary: schema validation failed: #{e.message}"
    end
  end
end
