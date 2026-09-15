package com.boundary.sdk;

import java.net.http.HttpResponse;
import com.fasterxml.jackson.databind.ObjectMapper;

public class Boundary {
    private static final ObjectMapper mapper = new ObjectMapper();

    public static <T> T validate(HttpResponse<String> response, Class<T> schemaClass) throws Exception {
        if (response.statusCode() < 200 || response.statusCode() >= 300) {
            throw new RuntimeException("Boundary: unexpected status code " + response.statusCode());
        }

        String body = response.body();
        if (body == null || body.isEmpty()) {
            throw new RuntimeException("Boundary: empty response body");
        }

        try {
            return mapper.readValue(body, schemaClass);
        } catch (Exception e) {
            throw new RuntimeException("Boundary: schema validation failed", e);
        }
    }
}
