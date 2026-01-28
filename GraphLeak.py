import requests
import json
import re
import argparse
import os
import sys
from urllib3.exceptions import InsecureRequestWarning

# --- Color Setup ---
try:
    from colorama import init, Fore, Style
    init(autoreset=True) # Automatically resets color after each print
    COLORS = {
        "info": Fore.CYAN,
        "success": Fore.GREEN,
        "warning": Fore.YELLOW,
        "error": Fore.RED,
        "dim": Style.DIM,
        "bold": Style.BRIGHT
    }
except ImportError:
    print("[!] 'colorama' library not found. Please install it for colored output: pip install colorama")
    print("[*] Continuing without colors...\n")
    # Fallback to no colors if colorama is not installed
    COLORS = {key: "" for key in ["info", "success", "warning", "error", "dim", "bold"]}


def find_field_suggestions(endpoint, query_file, wordlist_file, output_file, insecure, debug):
    """
    Fuzzes FIELD NAMES in a GraphQL query to discover valid fields via 'Did you mean' suggestions.
    Prints only found fields to the console for a clean output.
    """
    # --- 1. Validate and Read Input Files ---
    if not os.path.exists(query_file):
        print(f"{COLORS['error']}[!] Error: Query file not found at '{query_file}'{Style.RESET_ALL}")
        return
    if not os.path.exists(wordlist_file):
        print(f"{COLORS['error']}[!] Error: Wordlist file not found at '{wordlist_file}'{Style.RESET_ALL}")
        return

    try:
        with open(query_file, 'r') as f:
            query_template = f.read()
    except IOError as e:
        print(f"{COLORS['error']}[!] Error reading query file: {e}{Style.RESET_ALL}")
        return

    found_suggestions = set()

    # --- 2. Print Startup Banner ---
    print(f"{COLORS['bold']}{COLORS['info']}[*] GraphLeak Starting...{Style.RESET_ALL}")
    print(f"{COLORS['dim']}    Target: {endpoint}{Style.RESET_ALL}")
    print(f"{COLORS['dim']}    Wordlist: {wordlist_file}{Style.RESET_ALL}")
    print(f"{COLORS['dim']}    Output: {output_file}{Style.RESET_ALL}")
    if insecure:
        print(f"{COLORS['warning']}[!] WARNING: SSL certificate verification is DISABLED.{Style.RESET_ALL}")
    if debug:
        print(f"{COLORS['warning']}[!] DEBUG MODE: ON.{Style.RESET_ALL}")
    print("-" * 50)

    # --- 3. Setup Request ---
    headers = {"Content-Type": "application/json"}
    if insecure:
        requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

    # --- 4. Fuzzing Loop ---
    try:
        with open(wordlist_file, 'r') as f:
            for line in f:
                field_name = line.strip()
                if not field_name:
                    continue

                if debug:
                    print(f"\n{COLORS['info']}[*] Testing field: '{field_name}'{Style.RESET_ALL}")

                try:
                    final_query = re.sub(r'FUZZ', field_name, query_template)
                except Exception as e:
                    if debug: print(f"{COLORS['error']}    [!] Error formatting query. {e}{Style.RESET_ALL}")
                    continue
                
                if debug:
                    print(f"{COLORS['dim']}    [DEBUG] Sending Query: {final_query}{Style.RESET_ALL}")

                payload = {"query": final_query}

                try:
                    response = requests.post(
                        endpoint,
                        headers=headers,
                        json=payload,
                        timeout=10,
                        verify=not insecure
                    )
                    
                    if debug:
                        print(f"{COLORS['dim']}    [DEBUG] Raw Response Status: {response.status_code}{Style.RESET_ALL}")
                        print(f"{COLORS['dim']}    [DEBUG] Raw Response Body:\n{response.text}{Style.RESET_ALL}")
                    
                    data = response.json()
                    response_text = json.dumps(data)
                    
                    regex_pattern = r'Did you mean \\"([^"]+)\\"'
                    match = re.search(regex_pattern, response_text, re.IGNORECASE)

                    if match:
                        suggestion = match.group(1)
                        if suggestion not in found_suggestions:
                            found_suggestions.add(suggestion)
                            # --- THIS IS THE MAIN OUTPUT ---
                            print(f"{COLORS['success']}[+] Found Field: {suggestion}{Style.RESET_ALL}")
                        else:
                            if debug: print(f"{COLORS['dim']}    [*] Found duplicate suggestion: '{suggestion}'{Style.RESET_ALL}")

                except requests.exceptions.SSLError as e:
                    print(f"\n{COLORS['error']}[!] SSL Error: {e}{Style.RESET_ALL}")
                    print(f"{COLORS['info']}    Try running with the --insecure flag.{Style.RESET_ALL}")
                    break
                except requests.exceptions.RequestException as e:
                    if debug: print(f"{COLORS['error']}    [!] Network Error: {e}{Style.RESET_ALL}")
                    break
                except json.JSONDecodeError:
                    if debug: print(f"{COLORS['error']}    [!] Failed to decode JSON. Server did not return valid JSON.{Style.RESET_ALL}")

    except IOError as e:
        print(f"{COLORS['error']}[!] Error reading wordlist file: {e}{Style.RESET_ALL}")
        return

    # --- 5. Write to File and Final Summary ---
    print("-" * 50)
    if found_suggestions:
        print(f"{COLORS['success']}[+] Scan Complete. Found {len(found_suggestions)} unique fields.{Style.RESET_ALL}")
        try:
            sorted_suggestions = sorted(list(found_suggestions))
            with open(output_file, 'w') as f:
                for suggestion in sorted_suggestions:
                    f.write(f"{suggestion}\n")
            print(f"{COLORS['info']}[*] Results saved to: {output_file}{Style.RESET_ALL}")
        except IOError as e:
            print(f"{COLORS['error']}[!] Error writing to output file: {e}{Style.RESET_ALL}")
    else:
        print(f"{COLORS['warning']}[-] Scan Complete. No suggestions were found.{Style.RESET_ALL}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="GraphLeak: Discover hidden GraphQL fields by exploiting 'Did you mean?' errors.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("-e", "--endpoint", required=True, help="The target GraphQL endpoint URL.")
    parser.add_argument("-q", "--query", required=True, help="Path to the file containing the GraphQL query with the 'FUZZ' keyword.")
    parser.add_argument("-w", "--wordlist", required=True, help="Path to the wordlist file (one field name per line).")
    parser.add_argument("-o", "--output", required=True, help="Path to the output file for discovered fields.")
    parser.add_argument("--insecure", action="store_true", help="Disable SSL certificate verification (like curl -k).")
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug mode to see queries and raw responses.")
    
    args = parser.parse_args()

    find_field_suggestions(
        endpoint=args.endpoint,
        query_file=args.query,
        wordlist_file=args.wordlist,
        output_file=args.output,
        insecure=args.insecure,
        debug=args.debug
    )
