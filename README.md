# s3bfd

An application for downloading files from S3 buckets.

## Notes

- This project has been re-licensed under the Mozilla Public License v2.0 as of 2026/07/03

## Compatibility

- Linux
- macOS (assumed, but untested)
- Windows (assumed, but untested)

## Installation

(Installation instructions are currently out-of-date)

1. Install a supported Python version
2. Create a virtual environment
3. Install `requests`, `tqdm`, and `sqlalchemy`
4. Download and place the `s3bfd.py`, `s3bfd_gui.py` and `utils.py` scripts into the same folder

## Usage

(Usage instructions are currently out-of-date)

### GUI

1. Start the virtual environment and run `python3 s3bfd_gui.py`
2. Provide at minimum:
- a bucket URL/name
- the region in which the bucket is located
- a prefix (similar to a directory/folder name, and must end with `/`)

### Command-line

Start the virtual environment, then:
`python3 s3bfd.py [BUCKET_URL] [PREFIX] [REGION] [OPTIONS]`

#### Options

(List of options is currently out-of-date)

```
-t, --threads				Number of threads to use
-p, --process-type			"cache_only": create a local cache of the 
							bucket's file and directory metadata
							"cache_download": create a local cache and 
							then download the files in the bucket
							"cache_download_validate": all of the above 
							along with validating file checksums
-D, --data-dir				Specify the parent directory for s3bfd, 
							defaulting to ~/.s3bfd
-L, --log-dir			
-B, --database-dir
-P, --prefix-cache-dir
-O, --download-dir
-c, --console-log-level
-f, --file-log-level
```

#### Debug Options
```
--debug-enabled
--debug-enable-caching
--debug-enable-downloading
--debug-enable-validation
--debug-max-file-downloads
--debug-enable-save-prefix-cache
--debug-enable-load-prefix-cache
```
