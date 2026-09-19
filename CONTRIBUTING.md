# Contributing to Bergendy

Thank you for considering a contribution to Bergendy!

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/Bergendy.git`
3. Install dependencies: `pip install -e .` and `maturin develop`
4. Run tests: `./scripts/run_all_tests.py`

## Code Style

- **Rust:** Follow [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/)
- **Python:** Follow [PEP 8](https://peps.python.org/pep-0008/), use `ruff` for linting
- **Commits:** Use [Conventional Commits](https://www.conventionalcommits.org/)

## Pull Request Process

1. Create a feature branch
2. Make your changes
3. Add tests for new functionality
4. Run the full test suite
5. Update documentation if needed
6. Open a PR with a clear description

## Reporting Bugs

Open an issue with:
- Bergendy version (`bergendy --version`)
- Operating system
- Steps to reproduce
- Expected vs actual behavior
