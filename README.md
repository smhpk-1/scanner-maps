# Google Places API Scanner

This tool scans GitHub for exposed Google Places API Keys.

> [!WARNING]
> ⚠️ **DISCLAIMER**
>
> THIS PROJECT IS ONLY FOR SECURITY RESEARCH AND REMINDS OTHERS TO PROTECT THEIR PROPERTY, DO NOT USE IT ILLEGALLY!!
>
> The project authors are not responsible for any consequences resulting from misuse.

## Prerequisites

Ensure you have the following installed on your system:

- Google Chrome
- Python 3.8+

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/scanner-maps
cd scanner-maps
```

2. Install required packages:

```bash
pip install -r requirements.txt
```

## Usage

1. Run the main script:

```bash
python3 src/main.py
```

2. You will be prompted to log in to your GitHub account in the browser. Please do so.

That's it! The script will now scan GitHub for exposed Google Places API Keys.

## Command Line Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--from-iter` | None | Start scanning from a specific iteration |
| `--debug` | False | Enable debug mode |
| `-ceko, --check-existed-keys-only` | False | Only validate existing keys in database |
| `-k, --keywords` | Default keywords | Custom search keywords |
| `-l, --languages` | Default languages | Limit search to specific programming languages |

### Examples

```bash
# Start scanning from iteration 100
python3 src/main.py --from-iter 100

# Only check existing keys
python3 src/main.py --check-existed-keys-only

# Use custom keywords and languages
python3 src/main.py -k "google_maps" "places_api" -l python javascript
```

## Results

The results are stored in the `google_places.db` SQLite database, which is created in the same directory as the script.

You can view the contents of this database using any SQLite database browser of your choice.

### Key Status Values

| Status | Description |
|--------|-------------|
| `unknown` | Key has not been validated yet |
| `valid` | Key is valid and working |
| `invalid` | Key is invalid or revoked |
| `rate_limited` | Key has hit rate limits |
| `restricted` | Key has API restrictions |

## How It Works

1. **Search GitHub**: Uses Selenium to search GitHub for code patterns matching Google Places API keys
2. **Extract Keys**: Parses search results to extract potential API keys using regex patterns
3. **Validate Keys**: Tests each key against the Google Places API to verify if it's working
4. **Store Results**: Saves all findings to a SQLite database for later analysis

## Keeping Your API Key Safe

It's important to keep your API keys safe to prevent unauthorized access:

- [Google API Key Best Practices](https://cloud.google.com/docs/authentication/api-keys)
- [Restricting API Keys](https://cloud.google.com/docs/authentication/api-keys#securing_an_api_key)
- Never commit API keys to version control
- Use environment variables or secret management services

## FAQ

**Q: Why are you using Selenium instead of the GitHub Search API?**

A: We use regex search to have the best search results. However, the official GitHub search API does not support regex search, only web-based search does.

**Q: Why are you limiting the programming language in the search?**

A: There are many API keys available. However, the web-based search only provides the first 5 pages of results. By limiting the language, we can break down the search results and obtain more keys.

**Q: Why don't you use multithreading?**

A: Because GitHub searches and Google APIs are rate-limited. Using multithreading does not significantly increase efficiency.

## License

MIT License - See [LICENSE](LICENSE) for details.
