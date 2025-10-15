# Configuration System for LeekWars Tools

All tools in this directory have been refactored to use a centralized configuration file for storing credentials.

## Setup

1. **Copy the template to create your config file:**
   ```bash
   cd tools
   cp config.template.json config.json
   ```

2. **Edit `config.json` with your credentials:**
   ```json
   {
     "accounts": {
       "main": {
         "email": "your.email@example.com",
         "password": "your_password"
       },
       "cure": {
         "email": "your_alternate_account",
         "password": "your_password"
       }
     }
   }
   ```

3. **Security**: The `config.json` file is already excluded from git via `.gitignore`, so your credentials won't be committed to the repository.

## Usage

### For Scripts Using Main Account

Most scripts automatically use the main account:
```python
from config_loader import load_credentials

email, password = load_credentials()  # Loads main account
```

### For Scripts Using Cure Account

Scripts with `_cure` suffix automatically use the cure account:
```python
from config_loader import load_credentials

email, password = load_credentials(account="cure")  # Loads cure account
```

## Updated Scripts

All 40+ scripts in the tools directory have been updated:

- ✅ `upload_v8.py` - Main account uploader
- ✅ `upload_v8_cure.py` - Cure account uploader
- ✅ `lw_test_script.py` - Main account testing
- ✅ `lw_test_script_cure.py` - Cure account testing
- ✅ `lw_solo_fights_flexible.py` - Main account battles
- ✅ `lw_solo_fights_flexible_cure.py` - Cure account battles
- ✅ And 30+ other scripts...

## Testing

To verify your configuration is working:
```bash
cd tools
python3 config_loader.py
```

You should see:
```
✅ Loaded credentials for: your.email@example.com
✅ Loaded credentials for: Cure
```

## Benefits

- **Security**: No hardcoded credentials in source code
- **Flexibility**: Easy to switch accounts by editing one file
- **Consistency**: All scripts use the same credential source
- **Git-safe**: Config file is excluded from version control
