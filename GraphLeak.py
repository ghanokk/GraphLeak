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
    init(autoreset=True)
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
    COLORS = {key: "" for key in ["info", "success", "warning", "error", "dim", "bold"]}


def save_results(found_suggestions, suggestion_map, output_file, track_file, track):
    """A helper function to write the found fields and tracking map to files."""
    if not found_suggestions:
        print(f"{COLORS['warning']}[-] No fields were found to save.{Style.RESET_ALL}")
        return

    print(f"{COLORS['success']}[+] Found {len(found_suggestions)} unique fields.{Style.RESET_ALL}")
    
    # Write the clean list of fields to the main output file
    try:
        sorted_suggestions = sorted(list(found_suggestions))
        with open(output_file, 'w') as f:
            for suggestion in sorted_suggestions:
                f.write(f"{suggestion}\n")
        print(f"{COLORS['info']}[*] Field list saved to: {output_file}{Style.RESET_ALL}")
    except IOError as e:
        print(f"{COLORS['error']}[!] Error writing to output file: {e}{Style.RESET_ALL}")

    # Write the tracking map to the tracking file if tracking was enabled
    if track and suggestion_map:
        try:
            with open(track_file, 'w') as f:
                f.write("# GraphLeak Tracking Map: Suggested Field -> Typos that led to it\n")
                for suggestion, typos in suggestion_map.items():
                    f.write(f"{suggestion}: {', '.join(typos)}\n")
            print(f"{COLORS['info']}[*] Tracking map saved to: {track_file}{Style.RESET_ALL}")
        except IOError as e:
            print(f"{COLORS['error']}[!] Error writing to tracking file: {e}{Style.RESET_ALL}")


def find_field_suggestions(endpoint, query_file, wordlist_file, output_file, insecure, debug, track, track_file):
    """
    Fuzzes FIELD NAMES in a GraphQL query to discover valid fields.
    Saves results even if the script is interrupted.
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

    # --- Load wordlist and get total count for progress ---
    try:
        with open(wordlist_file, 'r') as f:
            wordlist = [line.strip() for line in f]
        total_words = len(wordlist)
        if total_words == 0:
            print(f"{COLORS['warning']}[-] Wordlist is empty. Exiting.{Style.RESET_ALL}")
            return
    except IOError as e:
        print(f"{COLORS['error']}[!] Error reading wordlist file: {e}{Style.RESET_ALL}")
        return

    found_suggestions = set()
    suggestion_map = {} 

    # --- 2. Print Startup Banner ---
    print(f"{COLORS['bold']}{COLORS['info']}[*] GraphLeak Starting...{Style.RESET_ALL}")
    print(f"{COLORS['dim']}    Target: {endpoint}{Style.RESET_ALL}")
    print(f"{COLORS['dim']}    Wordlist: {wordlist_file} ({total_words} words){Style.RESET_ALL}")
    print(f"{COLORS['dim']}    Output: {output_file}{Style.RESET_ALL}")
    if track:
        print(f"{COLORS['dim']}    Tracking Map: {track_file}{Style.RESET_ALL}")
    if insecure:
        print(f"{COLORS['warning']}[!] WARNING: SSL certificate verification is DISABLED.{Style.RESET_ALL}")
    if debug:
        print(f"{COLORS['warning']}[!] DEBUG MODE: ON.{Style.RESET_ALL}")
    print("-" * 50)

    # --- 3. Setup Request ---
    headers = {"Content-Type": "application/json"}
    if insecure:
        requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

    # --- 4. Fuzzing Loop with Graceful Interruption Handling ---
    try:
        for index, field_name in enumerate(wordlist, start=1):
            if not field_name:
                continue

            progress_str = f"[{index}/{total_words}]"
            
            if debug:
                print(f"{COLORS['info']}[*] {progress_str} Testing field: '{field_name}'{Style.RESET_ALL}")
            else:
                print(f"{COLORS['dim']}{progress_str} Scanning...{Style.RESET_ALL}", end="\r")

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
                        if not debug:
                            print() 
                        print(f"{COLORS['success']}[+] Found Field: {suggestion}{Style.RESET_ALL}")
                    
                    if track:
                        print(f"{COLORS['dim']}    - Mapped from typo: '{field_name}'{Style.RESET_ALL}")
                        if suggestion not in suggestion_map:
                            suggestion_map[suggestion] = []
                        suggestion_map[suggestion].append(field_name)

            except requests.exceptions.SSLError as e:
                print(f"\n{COLORS['error']}[!] SSL Error: {e}{Style.RESET_ALL}")
                print(f"{COLORS['info']}    Try running with the --insecure flag.{Style.RESET_ALL}")
                break
            except requests.exceptions.RequestException as e:
                if debug: print(f"{COLORS['error']}    [!] Network Error: {e}{Style.RESET_ALL}")
                break
            except json.JSONDecodeError:
                if debug: print(f"{COLORS['error']}    [!] Failed to decode JSON. Server did not return valid JSON.{Style.RESET_ALL}")

    except KeyboardInterrupt:
        # This block runs when you press Ctrl+C
        print(f"\n{COLORS['warning']}[!] Scan interrupted by user.{Style.RESET_ALL}")

    finally:
        # This block runs whether the loop finished or was interrupted
        if not debug:
            print(" " * 50, end="\r") # Clear the progress line
        
        print("-" * 50)
        
        # Call the save_results function to write to files
        save_results(
            found_suggestions,
            suggestion_map,
            output_file,
            track_file,
            track
        )
        
        print(f"{COLORS['info']}[*] Done.{Style.RESET_ALL}")


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
    parser.add_argument("--track", action="store_true", help="Enable tracking to see which typos led to which field discoveries.")
    parser.add_argument("--track-file", default=None, help="Path to save the field-to-typo mapping file. Defaults to 'tracking_map.txt' if --track is used.")
    
    args = parser.parse_args()

    if args.track and not args.track_file:
        args.track_file = "tracking_map.txt"

    find_field_suggestions(
        endpoint=args.endpoint,
        query_file=args.query,
        wordlist_file=args.wordlist,
        output_file=args.output,
        insecure=args.insecure,
        debug=args.debug,
        track=args.track,
        track_file=args.track_file
    )
