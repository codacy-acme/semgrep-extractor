import requests
import yaml
import os
import argparse
import time
from typing import List, Dict, Optional, Any, Iterator
from tqdm import tqdm

# Codacy API configuration
CODACY_API_TOKEN = os.environ.get("CODACY_API_TOKEN")
CODACY_API_BASE_URL = "https://api.codacy.com/api/v3"

# Provider configuration
VALID_PROVIDERS = {
    'gh': 'GitHub',
    'ghe': 'GitHub Enterprise',
    'bb': 'Bitbucket',
    'gl': 'GitLab'
}

def select_provider() -> str:
    """Let user select a provider from the available options."""
    print("\nAvailable providers:")
    for code, name in VALID_PROVIDERS.items():
        print(f"  {code}: {name}")
    
    while True:
        provider = input("\nEnter the provider code (gh/ghe/bb/gl): ").lower()
        if provider in VALID_PROVIDERS:
            return provider
        print("Invalid provider. Please try again.")

# Semgrep UUID
SEMGREP_UUID = "6792c561-236d-41b7-ba5e-9d6bee0d548b"

def get_codacy_headers() -> Dict[str, str]:
    """Get headers required for Codacy API calls."""
    return {
        "api-token": CODACY_API_TOKEN,
        "Accept": "application/json"
    }

def spinner(message: str) -> Iterator[str]:
    """Display a spinner while a task is in progress."""
    symbols = ['|', '/', '-', '\\']
    i = 0
    while True:
        i = (i + 1) % len(symbols)
        yield f"\r{message} {symbols[i]}"

def get_coding_standards(organization: str, provider: str) -> List[Dict[str, Any]]:
    """Fetch coding standards from Codacy API."""
    spin = spinner("Fetching coding standards")
    url = f"{CODACY_API_BASE_URL}/organizations/{provider}/{organization}/coding-standards"
    response = requests.get(url, headers=get_codacy_headers())
    response.raise_for_status()
    coding_standards = response.json()['data']
    print("\rFetched coding standards  ")
    return coding_standards

def select_coding_standard(coding_standards: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Let user select a coding standard from the list."""
    print("\nAvailable coding standards:")
    for i, standard in enumerate(coding_standards, 1):
        print(f"{i}. {standard['name']}")
    
    while True:
        try:
            selection = int(input("\nEnter the number of the coding standard you want to use: "))
            if 1 <= selection <= len(coding_standards):
                return coding_standards[selection - 1]
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a valid number.")

def get_tools_for_coding_standard(organization: str, provider: str, coding_standard_id: str) -> List[Dict[str, Any]]:
    """Fetch tools available for a coding standard."""
    spin = spinner("Fetching tools for coding standard")
    url = f"{CODACY_API_BASE_URL}/organizations/{provider}/{organization}/coding-standards/{coding_standard_id}/tools"
    response = requests.get(url, headers=get_codacy_headers())
    response.raise_for_status()
    tools = response.json()["data"]
    print("\rFetched tools for coding standard  ")
    return tools

def get_tool_by_uuid(tools: List[Dict[str, Any]], tool_uuid: str) -> Optional[Dict[str, Any]]:
    """Find a tool by its UUID."""
    for tool in tools:
        if tool.get('uuid') == tool_uuid:
            return tool
    return None

def get_code_patterns_for_tool(
    organization: str,
    provider: str,
    coding_standard_id: str,
    tool_uuid: str
) -> List[Dict[str, Any]]:
    """Fetch all patterns for a specific tool."""
    patterns = []
    cursor = None
    pbar = tqdm(desc="Fetching patterns", unit=" pages")
    
    while True:
        url = f"{CODACY_API_BASE_URL}/organizations/{provider}/{organization}/coding-standards/{coding_standard_id}/tools/{tool_uuid}/patterns?limit=1000"
        if cursor:
            url += f"&cursor={cursor}"
        
        response = requests.get(url, headers=get_codacy_headers())
        response.raise_for_status()
        data = response.json()
        patterns.extend(data["data"])
        
        pbar.update(1)
        
        cursor = data.get("pagination", {}).get("cursor")
        if not cursor:
            break
    
    pbar.close()
    return patterns

def filter_enabled_patterns(patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter out disabled patterns."""
    return [pattern for pattern in patterns if pattern.get("enabled", False)]

def get_available_languages(patterns: List[Dict[str, Any]]) -> List[str]:
    """Get list of available languages from patterns."""
    languages = set()
    for pattern in tqdm(patterns, desc="Processing patterns", unit=" patterns"):
        pattern_languages = pattern.get("patternDefinition", {}).get("languages", [])
        languages.update(lang.lower() for lang in pattern_languages)
    return sorted(list(languages))

def get_user_selected_languages(available_languages: List[str]) -> List[str]:
    """Let user select languages from available options."""
    print("\nAvailable languages:")
    for i, lang in enumerate(available_languages, 1):
        print(f"{i}. {lang.capitalize()}")
    
    selected_indices = input("\nEnter the numbers of the languages you want to include (comma-separated): ")
    selected_indices = [int(idx.strip()) for idx in selected_indices.split(',') if idx.strip().isdigit()]
    
    return [available_languages[idx - 1] for idx in selected_indices if 1 <= idx <= len(available_languages)]

def format_rule_id(pattern_def: Dict[str, Any]) -> str:
    """Format rule ID in a simple format."""
    # Get the pattern ID
    pattern_id = pattern_def.get('id', '')
    
    # Extract the most specific part of the ID
    if '.' in pattern_id:
        pattern_id = pattern_id.split('.')[-1]
    
    # Further simplify by taking just the last part if it contains hyphens
    if '-' in pattern_id:
        parts = pattern_id.split('-')
        # If there are duplicated parts, take just one instance
        unique_parts = []
        for part in parts:
            if part not in unique_parts:
                unique_parts.append(part)
        pattern_id = '-'.join(unique_parts)
    
    return pattern_id if pattern_id else 'unknown-rule'

def create_semgrep_config(patterns: List[Dict[str, Any]], selected_languages: List[str]) -> Dict[str, Any]:
    """Create Semgrep configuration from Codacy patterns."""
    rules = []

    for pattern in tqdm(patterns, desc="Creating Semgrep config", unit=" patterns"):
        pattern_def = pattern.get("patternDefinition", {})
        pattern_languages = set(lang.lower() for lang in pattern_def.get("languages", []))
        
        if not pattern_languages.intersection(selected_languages):
            continue

        # Create rule with simplified ID
        rule = {
            "id": format_rule_id(pattern_def),
            "languages": list(pattern_languages.intersection(selected_languages)),
        }

        # Add message if available
        message = pattern_def.get("description")
        if message:
            rule["message"] = message

        # Add severity if available
        severity = pattern.get("severity", "WARNING")
        if severity:
            rule["severity"] = severity.upper()

        # Add pattern if available
        if "pattern" in pattern_def:
            rule["pattern"] = pattern_def["pattern"]
        else:
            rule["pattern"] = "{}"

        rules.append(rule)
    
    return {"rules": rules}

def save_semgrep_config(config: Dict[str, Any], filename: str) -> None:
    """Save Semgrep configuration to a YAML file with proper formatting."""
    header = """# This file contains Semgrep rules generated from Codacy configuration
# See https://semgrep.dev for more information about Semgrep
#
# You can use this file locally with:
#  - semgrep --config semgrep_config.yaml .
#
# For more information about rule syntax, visit:
# https://semgrep.dev/docs/writing-rules/rule-syntax/

"""
    
    # Custom YAML formatting to match the desired style
    def custom_str_presenter(dumper, data):
        if len(data.splitlines()) > 1:  # check for multiline string
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)
    
    yaml.add_representer(str, custom_str_presenter)
    
    with open(filename, "w") as f:
        f.write(header)
        yaml.dump(
            config,
            f,
            default_flow_style=False,
            sort_keys=False,
            indent=2,
            width=80,
            allow_unicode=True
        )

def main() -> None:
    """Main function to run the Codacy to Semgrep config converter."""
    parser = argparse.ArgumentParser(description="Generate Semgrep configuration from Codacy API")
    parser.add_argument("--organization", help="Specify the Codacy organization")
    parser.add_argument("--provider", help="Specify the provider (gh/ghe/bb/gl)",
                       choices=VALID_PROVIDERS.keys())
    parser.add_argument("--tool", help="Specify a different tool UUID (default is Semgrep)",
                       default=SEMGREP_UUID)
    parser.add_argument("--output", help="Output file name",
                       default="semgrep_config.yaml")
    args = parser.parse_args()

    if not CODACY_API_TOKEN:
        raise ValueError("CODACY_API_TOKEN environment variable is not set")

    try:
        # 1. Get provider and organization
        if args.provider:
            selected_provider = args.provider
        else:
            selected_provider = select_provider()
        print(f"\nUsing provider: {VALID_PROVIDERS[selected_provider]}")

        if args.organization:
            selected_organization = args.organization
        else:
            selected_organization = input("Enter the Codacy organization name: ")
        print(f"Using organization: {selected_organization}")

        # 2. Get and select coding standards
        coding_standards = get_coding_standards(selected_organization, selected_provider)
        if not coding_standards:
            raise Exception(f'No Coding Standards found for org {selected_organization}')
        
        selected_standard = select_coding_standard(coding_standards)
        coding_standard_id = selected_standard["id"]
        print(f"\nSelected coding standard: {selected_standard['name']} (ID: {coding_standard_id})")

        # 3. Get tools for the coding standard
        tools = get_tools_for_coding_standard(selected_organization, selected_provider, coding_standard_id)
        print(f"Found {len(tools)} tools for the coding standard")

        # 4. Select the tool (Semgrep by default or user-specified)
        selected_tool = get_tool_by_uuid(tools, args.tool)
        if not selected_tool:
            print(f"Tool with UUID '{args.tool}' not found. Available tools:")
            for tool in tools:
                print(f"- Name: {tool.get('name', 'Unknown')}")
                print(f"  UUID: {tool.get('uuid', 'Unknown UUID')}")
            return

        print(f"\nSelected tool: {selected_tool.get('name', 'Unknown')} (UUID: {selected_tool['uuid']})")

        # 5. Get patterns for the selected tool
        tool_patterns = get_code_patterns_for_tool(selected_organization, selected_provider, coding_standard_id, selected_tool['uuid'])
        print(f"Found {len(tool_patterns)} patterns in total")

        # 6. Filter enabled patterns
        enabled_patterns = filter_enabled_patterns(tool_patterns)
        print(f"Found {len(enabled_patterns)} enabled patterns")

        # 7. Get available languages and let user select
        available_languages = get_available_languages(enabled_patterns)
        selected_languages = get_user_selected_languages(available_languages)
        print(f"Selected languages: {', '.join(selected_languages)}")

        # 8. Create the Semgrep YAML
        semgrep_config = create_semgrep_config(enabled_patterns, selected_languages)
        save_semgrep_config(semgrep_config, args.output)
        print(f"\nSemgrep configuration has been saved to {args.output}")
        
        # 9. Print total number of rules
        print(f"Total rules added to config file: {len(semgrep_config['rules'])}")

    except requests.RequestException as e:
        print(f"Error accessing Codacy API: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()