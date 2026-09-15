use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};
use tree_sitter_tags::{TagsConfiguration, TagsContext};

pub struct RepoMap {
    root: PathBuf,
}

impl RepoMap {
    pub fn new(root: impl AsRef<Path>) -> Self {
        Self {
            root: root.as_ref().to_path_buf(),
        }
    }

    pub fn build(&self, token_budget: usize) -> Result<String, String> {
        let mut context = TagsContext::new();
        
        // Define tags configurations for each language
        // (In a real scenario, this would be highly solid. For this MVP, we capture Go/Java/Ruby/Python classes and functions)
        
        let go_config = TagsConfiguration::new(
            tree_sitter_go::language(),
            r#"
            (function_declaration name: (identifier) @name) @definition.function
            (method_declaration name: (field_identifier) @name) @definition.method
            (type_spec name: (type_identifier) @name type: (struct_type)) @definition.class
            "#,
            ""
        ).map_err(|e| e.to_string())?;

        let python_config = TagsConfiguration::new(
            tree_sitter_python::language(),
            r#"
            (class_definition name: (identifier) @name) @definition.class
            (function_definition name: (identifier) @name) @definition.function
            "#,
            ""
        ).map_err(|e| e.to_string())?;
        
        let java_config = TagsConfiguration::new(
            tree_sitter_java::language(),
            r#"
            (class_declaration name: (identifier) @name) @definition.class
            (record_declaration name: (identifier) @name) @definition.class
            (method_declaration name: (identifier) @name) @definition.method
            "#,
            ""
        ).map_err(|e| e.to_string())?;

        let mut signatures: Vec<String> = Vec::new();
        
        for entry in walkdir::WalkDir::new(&self.root).into_iter().filter_map(|e| e.ok()) {
            if entry.file_type().is_dir() { continue; }
            let path = entry.path();
            let ext = path.extension().and_then(|s| s.to_str()).unwrap_or("");
            
            let config = match ext {
                "go" => &go_config,
                "py" => &python_config,
                "java" => &java_config,
                _ => continue,
            };

            let source = match fs::read(path) {
                Ok(bytes) => bytes,
                Err(_) => continue,
            };

            let tags = context.generate_tags(config, &source, None);
            if let Ok((tags_iter, _)) = tags {
                let mut file_signatures = vec![format!("File: {}", path.strip_prefix(&self.root).unwrap_or(path).display())];
                for tag in tags_iter.filter_map(|t| t.ok()) {
                    let start = tag.range.start;
                    let end = tag.range.end;
                    let text = String::from_utf8_lossy(&source[start..end]);
                    
                    // Simple heuristic: Take the first line (signature) of the node to omit the body
                    let signature = text.lines().next().unwrap_or("").trim().to_string();
                    if !signature.is_empty() {
                        file_signatures.push(format!("  {}", signature));
                    }
                }
                if file_signatures.len() > 1 {
                    signatures.extend(file_signatures);
                }
            }
        }

        let map_str = signatures.join("\n");
        let char_budget = token_budget * 4; // Approx 4 chars per token
        if map_str.len() > char_budget {
            Ok(format!("{}\n...[truncated]", &map_str[..char_budget]))
        } else {
            Ok(map_str)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::tempdir;

    #[test]
    fn test_repo_map() {
        let dir = tempdir().unwrap();
        let file_path = dir.path().join("main.go");
        let mut file = fs::File::create(file_path).unwrap();
        writeln!(file, "package main\n\ntype StripeCustomerSchema struct {{\n  ID string\n}}\n\nfunc (s *StripeCustomerSchema) validate() error {{\n  return nil\n}}").unwrap();
        
        let map = RepoMap::new(dir.path()).build(1000).unwrap();
        assert!(map.contains("StripeCustomerSchema"));
        assert!(map.contains("func (s *StripeCustomerSchema) validate()"));
    }
}
