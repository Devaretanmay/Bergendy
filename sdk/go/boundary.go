package boundary

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
)

// Validate consumes the HTTP response, checks the status code,
// parses the JSON body into the provided schema type T, and returns the result.
func Validate[T any](resp *http.Response, err error, schema T) (T, error) {
	if err != nil {
		return schema, err
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return schema, fmt.Errorf("boundary: unexpected status code %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return schema, fmt.Errorf("boundary: failed to read response body: %w", err)
	}

	if err := json.Unmarshal(body, &schema); err != nil {
		return schema, fmt.Errorf("boundary: schema validation failed: %w", err)
	}

	return schema, nil
}
