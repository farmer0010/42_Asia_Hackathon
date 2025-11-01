// PPT Contract Tests for Shimmy
// These tests ensure that critical invariants are always checked during execution

use crate::invariant_ppt::shimmy_invariants::*;
use crate::invariant_ppt::*;

// PPT tests require actual model loading, which needs a compiled backend
#[cfg(all(
    test,
    any(
        feature = "llama",
        feature = "llama-cuda",
        feature = "llama-vulkan",
        feature = "llama-opencl"
    )
))]
mod contract_tests {
    use super::*;
    use tokio;

    #[test]
    fn test_model_loading_contracts() {
        clear_invariant_log();

        // Simulate model loading with invariants
        let model_name = "test-model";
        assert_model_loaded(model_name, true);

        // Contract test: verify the model loading invariants were checked
        contract_test(
            "model_loading_integrity",
            &["Model name must not be empty", "Model loaded successfully"],
        );
    }

    #[test]
    fn test_generation_contracts() {
        clear_invariant_log();

        // Simulate generation with invariants
        let prompt = "Hello world";
        let response = "Hello! How can I help you today?";
        assert_generation_valid(prompt, response);

        // Contract test: verify generation invariants were checked
        contract_test(
            "generation_integrity",
            &[
                "Generation prompt must not be empty",
                "Generation response must not be empty",
                "Generation must produce output",
            ],
        );
    }

    #[test]
    fn test_api_response_contracts() {
        clear_invariant_log();

        // Simulate API response with invariants
        assert_api_response_valid(200, "{\"status\":\"ok\"}");
        assert_api_response_valid(404, "{\"error\":\"not found\"}");

        // Contract test: verify API invariants were checked
        contract_test(
            "api_response_integrity",
            &[
                "API response status must be valid HTTP code",
                "API response body must exist (unless 204)",
            ],
        );
    }

    #[test]
    fn test_backend_selection_contracts() {
        clear_invariant_log();

        // Simulate backend selection with invariants
        assert_backend_selection_valid("model.gguf", "llama");
        assert_backend_selection_valid("model.safetensors", "huggingface");

        // Contract test: verify backend selection invariants were checked
        contract_test(
            "backend_selection_integrity",
            &[
                "File path for backend selection must not be empty",
                "Selected backend must not be empty",
                "GGUF files must use Llama backend",
            ],
        );
    }

    #[test]
    fn test_discovery_contracts() {
        clear_invariant_log();

        // Simulate model discovery with invariants
        assert_discovery_valid(5); // Found 5 models
        assert_discovery_valid(0); // Found no models (edge case)

        // Contract test: verify discovery invariants were checked
        contract_test(
            "discovery_integrity",
            &["Model discovery must return reasonable count"],
        );
    }

    #[tokio::test]
    async fn test_full_workflow_contracts() {
        clear_invariant_log();

        // Simulate a full Shimmy workflow with all invariants

        // 1. Model discovery
        assert_discovery_valid(3);

        // 2. Backend selection
        assert_backend_selection_valid("phi3.gguf", "llama");

        // 3. Model loading
        assert_model_loaded("phi3", true);

        // 4. Generation
        assert_generation_valid("What is AI?", "AI is artificial intelligence...");

        // 5. API response
        assert_api_response_valid(200, "{\"response\":\"AI is artificial intelligence...\"}");

        // Contract test: verify ALL critical invariants were checked in workflow
        contract_test(
            "full_workflow_integrity",
            &[
                "Model discovery must return reasonable count",
                "File path for backend selection must not be empty",
                "GGUF files must use Llama backend",
                "Model name must not be empty",
                "Model loaded successfully",
                "Generation prompt must not be empty",
                "Generation must produce output",
                "API response status must be valid HTTP code",
            ],
        );
    }
}

#[cfg(all(
    test,
    any(
        feature = "llama",
        feature = "llama-cuda",
        feature = "llama-vulkan",
        feature = "llama-opencl"
    )
))]
mod property_tests {
    use super::*;

    #[test]
    #[serial_test::serial]
    fn test_model_name_property() {
        // Property: Valid model names are never empty and contain reasonable characters
        let test_names = vec!["phi3", "llama2-7b", "mistral-v0.1", "gpt-3.5-turbo"];

        for name in test_names {
            clear_invariant_log();
            assert_model_loaded(name, true);

            // Verify the invariant was checked
            let checked = checked_invariants();
            assert!(
                checked
                    .iter()
                    .any(|inv| inv.contains("Model name must not be empty")),
                "Missing model name invariant for model: {}",
                name
            );
        }
    }

    #[test]
    fn test_generation_length_property() {
        // Property: Generation always produces non-trivial output for non-empty prompts
        let test_cases = vec![
            ("Hi", "Hello there!"),
            ("What is 2+2?", "2+2 equals 4."),
            (
                "Tell me a joke",
                "Why don't scientists trust atoms? Because they make up everything!",
            ),
        ];

        for (prompt, response) in test_cases {
            clear_invariant_log();
            assert_generation_valid(prompt, response);

            // Verify all generation invariants were checked
            let checked = checked_invariants();

            assert!(
                checked
                    .iter()
                    .any(|inv| inv.contains("Generation prompt must not be empty")),
                "Missing prompt invariant for prompt: {}",
                prompt
            );

            assert!(
                checked
                    .iter()
                    .any(|inv| inv.contains("Generation response must not be empty")),
                "Missing response invariant for prompt: {}",
                prompt
            );

            assert!(
                checked
                    .iter()
                    .any(|inv| inv.contains("Generation must produce output")),
                "Missing output invariant for prompt: {}",
                prompt
            );
        }
    }

    #[test]
    #[serial_test::serial]
    fn test_backend_routing_property() {
        // Property: File extensions always map to correct backends
        let test_cases = vec![
            ("model.gguf", "llama"),
            ("model.GGUF", "llama"),
            ("large-model.gguf", "llama"),
            ("model.safetensors", "huggingface"),
        ];

        for (file_path, expected_backend) in test_cases {
            clear_invariant_log();
            assert_backend_selection_valid(file_path, expected_backend);

            // Verify invariants were checked
            let checked = checked_invariants();

            assert!(
                checked
                    .iter()
                    .any(|inv| inv.contains("File path for backend selection must not be empty")),
                "Missing invariant check for file path on {}",
                file_path
            );

            assert!(
                checked
                    .iter()
                    .any(|inv| inv.contains("Selected backend must not be empty")),
                "Missing invariant check for backend on {}",
                file_path
            );

            // For GGUF files, verify the specific invariant
            if file_path.to_lowercase().ends_with(".gguf") {
                assert!(
                    checked
                        .iter()
                        .any(|inv| inv.contains("GGUF files must use Llama backend")),
                    "Missing GGUF-specific invariant check for {}",
                    file_path
                );
            }
        }
    }

    #[test]
    fn test_api_status_codes_property() {
        // Property: API responses always have valid HTTP status codes
        let test_cases = vec![
            (200, "{\"success\": true}"),
            (201, "{\"created\": true}"),
            (400, "{\"error\": \"bad request\"}"),
            (404, "{\"error\": \"not found\"}"),
            (500, "{\"error\": \"internal error\"}"),
        ];

        for (status, body) in test_cases {
            clear_invariant_log();
            assert_api_response_valid(status, body);

            // Verify invariants were checked
            let checked = checked_invariants();
            assert!(
                checked
                    .iter()
                    .any(|inv| inv.contains("API response status must be valid HTTP code")),
                "Missing API status invariant for status code: {}",
                status
            );
        }
    }
}

#[cfg(all(
    test,
    any(
        feature = "llama",
        feature = "llama-cuda",
        feature = "llama-vulkan",
        feature = "llama-opencl"
    )
))]
mod exploration_tests {
    use super::*;

    #[test]
    fn explore_edge_cases() {
        // These are temporary exploration tests for development

        explore_test("empty_model_discovery", || {
            clear_invariant_log();
            assert_discovery_valid(0);
            !checked_invariants().is_empty()
        });

        explore_test("large_generation_response", || {
            clear_invariant_log();
            let large_response = "A".repeat(10000);
            assert_generation_valid("Generate a long response", &large_response);
            !checked_invariants().is_empty()
        });

        explore_test("api_no_content_response", || {
            clear_invariant_log();
            assert_api_response_valid(204, ""); // No content responses are valid
            !checked_invariants().is_empty()
        });
    }
}
