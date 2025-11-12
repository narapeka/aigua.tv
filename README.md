# TV Show Media Library Organizer

A powerful Python tool that automatically organizes your TV show media library following Emby/Plex naming conventions. It handles mixed folder structures and intelligently extracts show names, season numbers, and episode numbers from various file naming patterns.

## Features

- 🎯 **Smart Structure Detection**: Automatically detects two common folder structures:
  - **Direct Files**: Media files directly in show folder (single season)
  - **Season Subfolders**: Multiple season folders containing episodes
- 🏷️ **Intelligent Parsing**: Extracts show names, season numbers, and episode numbers using advanced regex patterns
- 📁 **Emby/Plex Compatible**: Organizes files following standard media server naming conventions
- 🎨 **Colored Output**: Beautiful, informative console output with progress tracking
- 🔍 **Dry Run Mode**: Preview all changes before actual file operations
- 🛡️ **Error Handling**: Comprehensive error handling with detailed logging
- 📺 **Wide Format Support**: Supports all common video formats (mp4, mkv, avi, mov, etc.)

## Installation

1. Clone or download the script:
```bash
git clone <repository-url>
cd tv-show-organizer
```

2. Make the script executable:
```bash
chmod +x tv_show_organizer.py
```

3. No additional dependencies required - uses only Python standard library!

## Usage

### Basic Usage

```bash
python tv_show_organizer.py "/path/to/tv/shows" "/path/to/organized" --dry-run
```

### Command Line Options

```
python tv_show_organizer.py [-h] [--dry-run] [--verbose] [--version] input_dir output_dir

positional arguments:
  input_dir      Input directory containing TV show folders
  output_dir     Output directory for organized TV shows

optional arguments:
  -h, --help     show this help message and exit
  --dry-run      Preview changes without moving files
  --verbose, -v  Enable verbose logging
  --version      show program's version number and exit
```

### Examples

1. **Preview organization (recommended first step):**
```bash
python tv_show_organizer.py "~/Downloads/TV Shows" "~/Media/TV" --dry-run --verbose
```

2. **Organize TV shows:**
```bash
python tv_show_organizer.py "/Users/john/Unsorted TV" "/Users/john/Organized TV"
```

3. **Verbose output with preview:**
```bash
python tv_show_organizer.py "/media/downloads" "/media/tv" --dry-run -v
```

## Supported Folder Structures

### Case 1: Direct Files (Single Season)
```
Input:
/TV Shows/
├── Breaking Bad/
│   ├── Breaking.Bad.S01E01.mp4
│   ├── Breaking.Bad.S01E02.mp4
│   └── Breaking.Bad.S01E03.mp4

Output:
/Organized TV/
└── Breaking Bad/
    └── Season 01/
        ├── Breaking Bad - S01E01 - Episode 01.mp4
        ├── Breaking Bad - S01E02 - Episode 02.mp4
        └── Breaking Bad - S01E03 - Episode 03.mp4
```

### Case 2: Season Subfolders
```
Input:
/TV Shows/
└── The Office/
    ├── Season 1/
    │   ├── episode1.mp4
    │   └── episode2.mp4
    └── Season 2/
        ├── S02E01.mkv
        └── S02E02.mkv

Output:
/Organized TV/
└── The Office/
    ├── Season 01/
    │   ├── The Office - S01E01 - Episode 01.mp4
    │   └── The Office - S01E02 - Episode 02.mp4
    └── Season 02/
        ├── The Office - S02E01 - Episode 01.mkv
        └── The Office - S02E02 - Episode 02.mkv
```

## Supported Naming Patterns

The tool intelligently recognizes various naming patterns:

### Season Detection
- `Season 1`, `season 1`, `S1`, `S01`
- `1`, `01` (fallback numeric detection)

### Episode Detection
- **S##E## Format**: `S01E01`, `S1E1`, `S01.E01`
- **##x## Format**: `1x01`, `1x1`
- **Episode Numbers**: `Episode 1`, `E01`, `Ep1`
- **Numeric Fallback**: Any 1-2 digit numbers in filename
- **Position-based**: If no numbers found, uses file sort order

### Supported Video Formats
- MP4, MKV, AVI, MOV, WMV, FLV, WEBM, M4V, TS, M2TS

## Output Format

The tool creates an Emby/Plex compatible structure:

```
/Output Directory/
└── [Show Name]/
    └── Season ##/
        └── [Show Name] - S##E## - Episode ##.[ext]
```

Example: `Breaking Bad - S01E01 - Episode 01.mp4`

## Sample Output

```
INFO: TV Show Media Library Organizer
INFO: Input Directory: /Users/john/TV Shows
INFO: Output Directory: /Users/john/Organized TV
INFO: Mode: DRY RUN

INFO: 
Scanning input directory...
INFO: Found 3 potential TV show folders

Processing: Breaking Bad
INFO: Processing show: Breaking Bad (Direct Files)
INFO:   Organizing Season 01 -> Breaking Bad/Season 01
INFO:     Moving: Breaking.Bad.S01E01.mp4
INFO:     To: Breaking Bad/Season 01/Breaking Bad - S01E01 - Episode 01.mp4
INFO: ✓ Successfully processed: Breaking Bad

============================================================
OPERATION SUMMARY
============================================================
Shows Processed: 3
Seasons Processed: 5
Episodes Moved: 48
Errors: 0

This was a DRY RUN - no files were actually moved.
Remove --dry-run flag to perform actual organization.
```

## Safety Features

- **Dry Run Mode**: Always test with `--dry-run` first
- **Non-destructive**: Files are moved (renamed), not copied
- **Error Recovery**: Failed operations don't affect other files
- **Detailed Logging**: Track exactly what changes will be made
- **Path Validation**: Validates input/output directories before processing

## Advanced Usage Tips

1. **Always use dry-run first**: Preview changes before committing
```bash
python tv_show_organizer.py "/path/input" "/path/output" --dry-run -v
```

2. **Check verbose output**: Use `-v` to see detailed processing information

3. **Organize incrementally**: Process shows in batches for large libraries

4. **Backup important data**: While the tool is designed to be safe, always backup irreplaceable media

## Troubleshooting

### Common Issues

**"No video files found"**
- Check that your folders contain supported video file formats
- Ensure files aren't hidden or have unusual extensions

**"Permission denied"**
- Ensure you have read/write permissions to both input and output directories
- On macOS/Linux, you may need to adjust file permissions

**"Season/Episode detection failed"**
- Check the verbose output to see what patterns were detected
- Files will be organized by sort order if pattern detection fails

### Debug Mode

Enable verbose logging to see detailed processing:
```bash
python tv_show_organizer.py input output --dry-run --verbose
```

## Contributing

Feel free to contribute improvements:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly with various file structures
5. Submit a pull request

## License

This project is open source. Feel free to use and modify as needed.

## Changelog

### Version 1.0.0
- Initial release with full feature set
- Support for both direct files and season subfolder structures
- Intelligent season/episode detection
- Emby/Plex compatible output format
- Colored logging and dry-run mode