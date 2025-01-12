# Codacy to Semgrep Configuration Converter

A Python utility that converts Codacy code analysis configurations to Semgrep-compatible rule sets. This tool helps organizations migrate their code analysis rules from Codacy to Semgrep while maintaining their established code quality standards.

## Features

- Fetches coding standards from your Codacy organization
- Retrieves and filters enabled patterns from Codacy
- Converts Codacy patterns to Semgrep rules
- Supports language-specific rule filtering
- Interactive selection of coding standards and languages
- Progress indicators for long-running operations
- Customizable output configuration

## Prerequisites

- Python 3.6+
- Codacy API token
- A Codacy organization with existing coding standards

## Installation

1. Clone this repository:
```bash
git clone [repository-url]
cd semgrep-extractor
```

2. Install required dependencies:
```bash
pip install requests pyyaml tqdm
```

3. Set up your Codacy API token:
```bash
export CODACY_API_TOKEN="your-api-token-here"
```

## Usage

### Basic Usage

Run the script with minimal configuration:
```bash
python extractor.py
```

This will prompt you for:
- Organization name
- Coding standard selection
- Languages to include in the configuration

### Command Line Options

```bash
python extractor.py --organization YOUR_ORG --provider gh --output custom_config.yaml
```

 name (defaults to semgrep_config.yaml)

### Environment Variables

- `CODACY_API_TOKEN`: Your Codacy API token (required)

## Output

The script generates a YAML file containing Semgrep rules with:
- Simplified rule IDs
- Original pattern descriptions
- Severity levels
- Language specifications
- Pattern definitions

Example output structure:
```yaml
rules:
  - id: rule-id
    languages:
      - python
    message: "Rule description"
    severity: "WARNING"
    pattern: "pattern-definition"
```

## Error Handling

The script includes comprehensive error handling for:
- API connection issues
- Missing API tokens
- Invalid organization names
- Pattern conversion errors
- File writing errors

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions:
1. Open an issue in the repository
2. Contact your Codacy support representative
3. Check the [Semgrep documentation](https://semgrep.dev/docs/) for pattern syntax questions

## Acknowledgments

- Codacy API documentation
- Semgrep pattern documentation
- All contributors to this project