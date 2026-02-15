# GraphLeak

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.6+-blue.svg)

GraphLeak is a command-line tool to discover hidden GraphQL fields by exploiting the "Did you mean?" error message. It automates the process of sending invalid field names and parsing the server's suggestions to enumerate valid schema fields.

> This technique is useful for security testing and reconnaissance on GraphQL endpoints where field names are not publicly documented.

## How It Works

Many GraphQL servers, when faced with an unknown field in a query, return a helpful error message like:

```json
{"errors":[{"message":"Cannot query field \"validationError\" on type \"Query\". Did you mean \"validateFile\"?","extensions":{"code":"GRAPHQL_VALIDATION_FAILED"}}]}
```

GraphLeak automates this process:
1.  It takes a wordlist of potential field names.
2.  It injects each name into a GraphQL query template.
3.  It sends the malformed query to the target endpoint.
4.  It parses the JSON response for the `Did you mean "..."` pattern.
5.  It extracts and saves all unique, valid field names discovered.

## Features

-   **Clean, Colored Output:** Only shows discovered fields in the console for a focused experience. Uses colors for easy reading.
-   **File-based Input:** Use external files for your GraphQL query and wordlist.
-   **Clean Output:** Saves all discovered fields to a specified output file, with duplicates automatically removed.
-   **SSL Support:** Handles endpoints with SSL/TLS, with an option to disable verification for testing (`--insecure`).
-   **Debug Mode:** A `--debug` flag to view the exact queries being sent and the full server responses, making troubleshooting easy.

## Installation

GraphLeak requires Python 3 and the `requests` and `colorama` libraries.

1.  Clone the repository:
    ```bash
    git clone https://github.com/your-username/graphleak.git
    cd graphleak
    ```

2.  Install the required packages:
    ```bash
    pip install requests colorama
    ```

## Usage

### 1. Prepare Your Files

Create a file for your GraphQL query template (e.g., `query.txt`) with the `FUZZ` keyword marking the field to be tested.

**`query.txt`**
```graphql
query {
  FUZZ
}
```

Create a wordlist file (e.g., `wordlist.txt`) with one potential field name per line.

**`wordlist.txt`**
```
validationError
user
profile
admin
validateFile
secretKey
internalData
```

### 2. Run the Tool

Execute the script from your terminal, providing the required arguments.

**Basic Command:**
```bash
python graphleak.py \
  --endpoint "https://target.com/graphql" \
  --query "query.txt" \
  --wordlist "wordlist.txt" \
  --output "found_fields.txt"
```

**Example Output:**
```
[*] GraphLeak Starting...
    Target: https://target.com/graphql
    Wordlist: wordlist.txt
    Output: found_fields.txt
--------------------------------------------------
[+] Found Field: validateFile
[+] Found Field: internalData
[+] Found Field: userProfile
--------------------------------------------------
[+] Scan Complete. Found 3 unique fields.
[*] Results saved to: found_fields.txt
```

**Command with Debug Mode:**
Use this if you encounter issues or want to see verbose output.
```bash
python graphleak.py \
  --endpoint "https://target.com/graphql" \
  --query "query.txt" \
  --wordlist "wordlist.txt" \
  --output "found_fields.txt" \
  --debug
```

## Options

| Option               | Description                                                              |
|----------------------|--------------------------------------------------------------------------|
| `-e, --endpoint`     | (Required) The target GraphQL endpoint URL.                               |
| `-q, --query`        | (Required) Path to the file containing the GraphQL query with `FUZZ`.     |
| `-w, --wordlist`     | (Required) Path to the wordlist file.                                     |
| `-o, --output`       | (Required) Path to the output file for discovered fields.                 |
| `--insecure`         | Disable SSL certificate verification (like `curl -k`).                     |
| `--debug`            | Enable verbose debug mode to see queries and raw responses.               |

## ⚠️ Ethical Warning

This tool is for authorized security testing and educational purposes only. Do not use it on any system or API for which you do not have explicit, written permission. Unauthorized scanning is illegal.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
```


