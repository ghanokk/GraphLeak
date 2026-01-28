import requests
import json
import re
import argparse
import os
from urllib3.exceptions import InsecureRequestWarning

def find_field_suggestions(endpoint, query_file, wordlist_file, output_file, insecure, debug):
    """
    Fuzzes FIELD NAMES in a GraphQL query to discover valid fields via 'Did you mean' suggestions.
    """
    # --- 1. Validate and Read Input Files ---
    if not os.path.exists(query_file):
        print(f"[!] Error: Query file not found at '{query_file}'")
        return
    if not os.path.exists(wordlist_file):
        print(f"[!] Error: Wordlist file not found at '{wordlist_file}'")
        return

    try:
        with open(query_file, 'r') as f:
            query_template = f.read()
    except IOError as e:
        print(f"[!] Error reading query file: {e}")
        return

    found_suggestions = set()

    print(f"[*] Target Endpoint: {endpoint}")
    print(f"[*] Reading query from: {query_file}")
    print(f"[*] Reading wordlist from: {wordlist_file}")
    print(f"[*] Output will be saved to: {output_file}")
    if insecure:
        print("[!] WARNING: SSL certificate verification is DISABLED.")
    if debug:
        print("[!] DEBUG MODE: ON. Verbose output enabled.")
    print("-" * 50)

    # --- 2. Setup Request ---
    headers = {"Content-Type": "application/json"}
    # If you need an auth token, add it here:
    # headers["Authorization"] = "Bearer YOUR_TOKEN_HERE"
    
    if insecure:
        requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

    # --- 3. Fuzzing Loop ---
    try:
        with open(wordlist_file, 'r') as f:
            for line in f:
                field_name = line.strip()
                if not field_name:
                    continue

                print(f"\n[*] Testing field: '{field_name}'")

                try:
                    final_query = re.sub(r'FUZZ', field_name, query_template)
                except Exception as e:
                    print(f"[!] Error formatting query. {e}")
                    continue
                
                if debug:
                    print(f"    [DEBUG] Sending Query: {final_query}")

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
                        print(f"    [DEBUG] Raw Response Status: {response.status_code}")
                        print(f"    [DEBUG] Raw Response Body:\n{response.text}")
                    
                    data = response.json()
                    response_text = json.dumps(data)
                    
                    # --- THE FIX IS HERE ---
                    # This regex now correctly handles the escaped quotes (\") in the JSON response.
                    regex_pattern = r'Did you mean \\"([^"]+)\\"'
                    match = re.search(regex_pattern, response_text, re.IGNORECASE)

                    if match:
                        suggestion = match.group(1)
                        if suggestion not in found_suggestions:
                            found_suggestions.add(suggestion)
                            print(f"    [+] FOUND suggestion: '{suggestion}'")
                        else:
                            print(f"    [*] Found duplicate suggestion: '{suggestion}'")
                    else:
                        if debug:
                            print("    [DEBUG] Regex did not match. No 'Did you mean' pattern found.")
                        else:
                            print("    [-] No suggestion found.")

                except requests.exceptions.SSLError as e:
                    print(f"\n[!] SSL Error: {e}")
                    print("    Try running with the --insecure flag.")
                    break
                except requests.exceptions.RequestException as e:
                    print(f"\n[!] Network Error: {e}")
                    break
                except json.JSONDecodeError:
                    print(f"\n[!] Failed to decode JSON. The server did not return valid JSON.")
                    if not debug:
                        print("    Run with --debug to see the raw response.")

    except IOError as e:
        print(f"[!] Error reading wordlist file: {e}")
        return

    # --- 4. Write Unique Suggestions to Output File ---
    print("\n" + "-" * 50)
    if found_suggestions:
        print(f"[+] Enumeration complete. Found {len(found_suggestions)} unique valid fields.")
        try:
            sorted_suggestions = sorted(list(found_suggestions))
            with open(output_file, 'w') as f:
                for suggestion in sorted_suggestions:
                    f.write(f"{suggestion}\n")
            print(f"[*] Successfully saved suggestions to '{output_file}'")
        except IOError as e:
            print(f"[!] Error writing to output file: {e}")
    else:
        print("[-] Enumeration complete. No suggestions were found.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="GraphQL Field Fuzzer. Finds valid field names via 'Did you mean' suggestions and saves them to a file.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("-e", "--endpoint", required=True, help="The target GraphQL endpoint URL.")
    parser.add_argument("-q", "--query", required=True, help="Path to the file containing the GraphQL query with the 'FUZZ' keyword for a field name.")
    parser.add_argument("-w", "--wordlist", required=True, help="Path to the wordlist file (one potential field name per line).")
    parser.add_argument("-o", "--output", required=True, help="Path to the output file where valid fields will be saved.")
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
