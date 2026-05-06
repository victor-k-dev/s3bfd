# MIT License
# 
# Copyright (c) 2026 victor-k-dev
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import tkinter as tk
from tkinter import filedialog, Text, StringVar, IntVar, messagebox
from tkinter.ttk import (
	Label, LabelFrame, Notebook, Frame, 
	Button, Progressbar, Scrollbar, Radiobutton, 
	Combobox, Entry
	)
import os
from pathlib import Path
import threading
from threading import Event
from queue import Queue, Empty
from s3bfd import run_s3bfd
from logging import LogRecord, Formatter

# Constants
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
#DEFAULT_MAIN_DIRECTORY = "~/.s3bfd"
DEFAULT_DATA_DIRECTORY = "~/.s3bfd/data"
DEFAULT_LOG_DIRECTORY = f"{DEFAULT_DATA_DIRECTORY}/logs"
DEFAULT_DATABASE_DIRECTORY = f"{DEFAULT_DATA_DIRECTORY}/database"
DEFAULT_PREFIX_CACHE_DIRECTORY = f"{DEFAULT_DATA_DIRECTORY}/prefix_cache"
DEFAULT_BUFFER_DIRECTORY = f"{DEFAULT_DATA_DIRECTORY}/buffer"
DEFAULT_DOWNLOAD_DIRECTORY = f"{DEFAULT_DATA_DIRECTORY}/downloads"
DATABASE_NAME = "s3bfd_cache.db"
PREFIX_CACHE_NAME = "s3bfd_prefix_cache.pkl"

# Globals
log_rows = 0
scrollback_limit = 0
debug_options = []
current_debug_state = 'enabled'
selected_process_option = None
thread_options = [i for i in range(os.cpu_count()*2) if i > 0]
formatter = Formatter(fmt="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

bucket_url = None
prefix = None
region = None
threads = 4
current_data_directory = DEFAULT_DATA_DIRECTORY
current_log_directory = DEFAULT_LOG_DIRECTORY
current_database_directory = DEFAULT_DATABASE_DIRECTORY
current_prefix_cache_directory = DEFAULT_PREFIX_CACHE_DIRECTORY
current_buffer_directory = DEFAULT_BUFFER_DIRECTORY
current_download_directory = DEFAULT_DOWNLOAD_DIRECTORY

message_queue = Queue()
pbar_queue = Queue()
is_running_event = Event()
early_stop_event = Event()

s3bfd_thread = None

def check_events():
	if is_running_event.is_set():
		start_button.configure(state='disabled')
		stop_button.configure(state='enabled')
		bucket_url_entry.configure(state='disabled')
		prefix_entry.configure(state='disabled')
		region_entry.configure(state='disabled')
	elif not is_running_event.is_set():
		start_button.configure(state='enabled')
		stop_button.configure(state='disabled')
		bucket_url_entry.configure(state='enabled')
		prefix_entry.configure(state='enabled')
		region_entry.configure(state='enabled')
		if s3bfd_thread is not None and s3bfd_thread.is_alive():
			s3bfd_thread.join(timeout=90.0)
	check_for_log_message()
	check_for_pbar_updates()
	window.after(100, check_events)

def check_for_log_message():
	try:
		while True:
			log_message = message_queue.get_nowait()
			gui_output_to_log_widget(log_message)
	except Empty:
		pass

def check_for_pbar_updates():
	try:
		while True:
			pbar_type, value = pbar_queue.get_nowait()
			if is_running_event.is_set():
				if pbar_type == "r_buffer":
					r_buffer_state.set(value)
				elif pbar_type == "d_buffer":
					d_buffer_state.set(value)
				elif pbar_type == "f_buffer":
					f_buffer_state.set(value)
			else:
				r_buffer_state.set(value=0)
				d_buffer_state.set(value=0)
				f_buffer_state.set(value=0)
	except Empty:
		pass

def gui_start_process():
	global s3bfd_thread
	global is_running_event

	if not region.get():
		messagebox.showerror(title="Error", message="You must specify a region.", icon='error')
		return

	process_args = {
		"bucket_url": bucket_url.get(),
		"prefix": prefix.get() if prefix.get() else None,
		"region": region.get(),
		"threads": int(threads_selection.get()),
		"data_directory": current_data_directory,
		"log_directory": current_log_directory,
		"database_directory": current_database_directory,
		"prefix_cache_directory": current_prefix_cache_directory,
		"buffer_directory": current_buffer_directory,
		"download_directory": current_download_directory,
		"console_log_level": console_log_level.get(),
		"file_log_level": file_log_level.get(),
		"process_type": selected_process_option.get(),
		"is_debug_enabled": bool(int(debug_selection.get())),
		"debug_enable_caching": bool(int(debug_file_caching_selection.get())),
		"debug_enable_downloading": bool(int(debug_file_downloading_selection.get())),
		"debug_enable_validation": bool(int(debug_file_validation_selection.get())),
		"debug_enable_save_prefix_cache": True, # TODO: add debug option
		"debug_enable_load_prefix_cache": True, # TODO: add debug option
		"debug_max_file_downloads": 1024,
		"log_message_queue": message_queue,
		"pbar_queue": pbar_queue,
		"is_running_event": is_running_event,
		"early_stop_event": early_stop_event
	}
	s3bfd_thread = threading.Thread(target=run_s3bfd, args=(process_args,))
	s3bfd_thread.start()
	if is_running_event.wait(timeout=30):
		check_events()
	return

def gui_stop_process():
	early_stop_event.set()
	s3bfd_thread.join(timeout=90.0)
	if s3bfd_thread.is_alive():
		print("Attempt to join s3bfd_thread timed out")


def gui_output_to_log_widget(message:LogRecord):
	global log_rows
	log_text.configure(state='normal')
	if scrollback_limit > 0 and log_rows >= scrollback_limit:
		log_text.replace("1.0", "2.0", '')
	else:
		log_rows += 1
	message = formatter.format(message)
	log_text.insert(tk.INSERT, message + "\n")
	log_text.see(index=tk.END)
	log_text.configure(state='disabled')

def gui_set_data_directory():
	global current_data_directory
	global current_log_directory
	global current_database_directory
	global current_prefix_cache_directory
	global current_buffer_directory
	global current_download_directory

	new_dir = filedialog.askdirectory()
	if Path(new_dir).is_dir() and Path(new_dir).exists():
		current_data_directory = new_dir
		data_directory_path.set(new_dir)
		if current_log_directory == DEFAULT_LOG_DIRECTORY:
			current_log_directory = current_log_directory.replace(DEFAULT_DATA_DIRECTORY, current_data_directory)
			log_directory_path.set(current_log_directory)
		if current_database_directory == DEFAULT_DATABASE_DIRECTORY:
			current_database_directory = current_database_directory.replace(DEFAULT_DATA_DIRECTORY, current_data_directory)
			database_directory_path.set(current_database_directory)
		if current_prefix_cache_directory == DEFAULT_PREFIX_CACHE_DIRECTORY:
			current_prefix_cache_directory = current_prefix_cache_directory.replace(DEFAULT_DATA_DIRECTORY, current_data_directory)
			prefix_cache_directory_path.set(current_prefix_cache_directory)
		if current_buffer_directory == DEFAULT_BUFFER_DIRECTORY:
			current_buffer_directory = current_buffer_directory.replace(DEFAULT_DATA_DIRECTORY, current_data_directory)
			buffer_directory_path.set(current_buffer_directory)
		if current_download_directory == DEFAULT_DOWNLOAD_DIRECTORY:
			current_download_directory = current_download_directory.replace(DEFAULT_DATA_DIRECTORY, current_data_directory)
			download_directory_path.set(current_download_directory)
	else:
		pass

def gui_set_log_directory():
	global current_log_directory
	new_dir = filedialog.askdirectory()
	if Path(new_dir).is_dir and Path(new_dir).exists():
		current_log_directory = new_dir
		log_directory_path.set(new_dir)
	else:
		pass

def gui_set_database_directory():
	global current_database_directory
	new_dir = filedialog.askdirectory()
	if Path(new_dir).is_dir and Path(new_dir).exists():
		current_database_directory = new_dir
		database_directory_path.set(new_dir)
	else:
		pass

def gui_set_prefix_cache_directory():
	global current_prefix_cache_directory
	new_dir = filedialog.askdirectory()
	if Path(new_dir).is_dir and Path(new_dir).exists():
		current_prefix_cache_directory = new_dir
		prefix_cache_directory_path.set(new_dir)
	else:
		pass

def gui_set_buffer_directory():
	global current_buffer_directory
	new_dir = filedialog.askdirectory()
	if Path(new_dir).is_dir and Path(new_dir).exists():
		current_buffer_directory = new_dir
		buffer_directory_path.set(new_dir)
	else:
		pass

def gui_set_download_directory():
	global current_download_directory
	new_dir = filedialog.askdirectory()
	if Path(new_dir).is_dir and Path(new_dir).exists():
		current_download_directory = new_dir
		download_directory_path.set(new_dir)
	else:
		pass

def set_debug_options_state():
	global current_debug_state
	if current_debug_state == 'enabled':
		for opt in debug_options:
			opt.configure(state='disabled')
		current_debug_state = 'disabled'
	else:
		for opt in debug_options:
			opt.configure(state='enabled')
		current_debug_state = 'enabled'

def main():
	global current_data_directory
	global current_log_directory
	global current_database_directory
	global current_prefix_cache_directory
	global window
	window = tk.Tk()
	window.title("s3bfd (S3 Bucket File Downloader)")
	window.geometry("1280x720")
	window.resizable(width=False, height=False)
	
	tabs = Notebook(window)
	main_tab = Frame(tabs)
	#log_tab = Frame(tabs)
	config_tab = Frame(tabs)
	tabs.add(main_tab, text="Main")
	#tabs.add(log_tab, text="Log")
	tabs.add(config_tab, text="Config")

	# Main
	total_main_tab_rows = 12
	total_main_tab_cols = 16
	for row in range(0,total_main_tab_rows):
		main_tab.grid_rowconfigure(row, weight=1, uniform="a")
	for col in range(0, total_main_tab_cols):
		main_tab.grid_columnconfigure(col, weight=1, uniform="a")

	global start_button
	start_button = Button(main_tab, text="Start", command=gui_start_process)
	start_button.grid(column=2, columnspan=2, row=10)

	global stop_button
	stop_button = Button(main_tab, text="Stop", command=gui_stop_process)
	stop_button.grid(column=4, columnspan=2, row=10)
	stop_button.configure(state='disabled')

	bucket_url_labelframe = LabelFrame(main_tab, text="Bucket URL")
	bucket_url_labelframe.grid(column=1, row=5, columnspan=2)
	global bucket_url
	bucket_url = StringVar()
	global bucket_url_entry
	bucket_url_entry = Entry(bucket_url_labelframe, textvariable=bucket_url)
	bucket_url_entry.pack(expand=True, fill='both')

	prefix_labelframe = LabelFrame(main_tab, text="Prefix")
	prefix_labelframe.grid(column=1, row=6, columnspan=2)
	global prefix
	prefix = StringVar()
	global prefix_entry
	prefix_entry = Entry(prefix_labelframe, textvariable=prefix)
	prefix_entry.pack(expand=True, fill='both')

	region_labelframe = LabelFrame(main_tab, text="Region")
	region_labelframe.grid(column=1, row=7, columnspan=2)
	global region
	region = StringVar()
	global region_entry
	region_entry = Entry(region_labelframe, textvariable=region)
	region_entry.pack(expand=True, fill='both')

	global r_buffer_state
	r_buffer_state = IntVar(value=0)
	global d_buffer_state
	d_buffer_state = IntVar(value=0)
	global f_buffer_state
	f_buffer_state = IntVar(value=0)

	requests_buffer_labelframe = LabelFrame(main_tab, text="Requests Buffer")
	requests_buffer_labelframe.grid(column=2, row=1, columnspan=4)
	requests_buffer_pbar = Progressbar(requests_buffer_labelframe, orient="horizontal", length=400, mode="determinate", maximum=32768, variable=r_buffer_state)
	requests_buffer_pbar.pack(expand=True, fill='both')

	directories_buffer_labelframe = LabelFrame(main_tab, text="Directories Buffer")
	directories_buffer_labelframe.grid(column=2, row=2, columnspan=4)
	directories_buffer_pbar = Progressbar(directories_buffer_labelframe, orient="horizontal", length=400, mode="determinate", maximum=1024, variable=d_buffer_state)
	directories_buffer_pbar.pack(expand=True, fill='both')

	files_buffer_labelframe = LabelFrame(main_tab, text="Files Buffer")
	files_buffer_labelframe.grid(column=2, row=3, columnspan=4)
	files_buffer_pbar = Progressbar(files_buffer_labelframe, orient="horizontal", length=400, mode="determinate", maximum=1024, variable=f_buffer_state)
	files_buffer_pbar.pack(expand=True, fill='both')

	process_options_labelframe = LabelFrame(main_tab, text="Process Options")
	process_options_labelframe.grid(column=3, row=4, columnspan=6, rowspan=5)
	global selected_process_option
	selected_process_option = tk.StringVar(value="cache_only")
	cache_download_validate = Radiobutton(process_options_labelframe, text="Cache, Download, Validate", variable=selected_process_option, value="cache_download_validate")
	cache_download = Radiobutton(process_options_labelframe, text="Cache, Download", variable=selected_process_option, value="cache_download")
	download_validate = Radiobutton(process_options_labelframe, text="Download, Validate", variable=selected_process_option, value="download_validate")
	cache_only = Radiobutton(process_options_labelframe, text="Cache Only", variable=selected_process_option, value="cache_only")
	download_only = Radiobutton(process_options_labelframe, text="Download Only", variable=selected_process_option, value="download_only")

	download_validate.configure(state='disabled')
	download_only.configure(state='disabled')

	cache_download_validate.pack(expand=True, fill='x')
	cache_download.pack(expand=True, fill='x')
	download_validate.pack(expand=True, fill='x')
	cache_only.pack(expand=True, fill='x')
	download_only.pack(expand=True, fill='x')

	logging_labelframe = LabelFrame(main_tab, text="Log")
	logging_labelframe.grid(column=9, row=0, rowspan=11, columnspan=7, pady=20)

	log_y_scrollbar = Scrollbar(logging_labelframe, orient='vertical')
	log_y_scrollbar.pack(side=tk.RIGHT, fill="y")

	global log_text
	log_text = Text(logging_labelframe, height=36, wrap="word")
	log_text.pack(side=tk.LEFT, expand=True, fill='both')
	log_text.config(yscrollcommand=log_y_scrollbar.set)
	log_y_scrollbar.config(command=log_text.yview)
	
	log_text.configure(state='disabled')

	# Config
	# TODO: add the following options
	#		(debug) enable save directory cache to disk (default true)
	#		(debug) enable load directory cache from disk (default true)
	#		clear data directory (logs, db, cache, downloads, etc.)
	total_config_tab_rows = 9
	total_config_tab_cols = 16
	for row in range(0,total_config_tab_rows):
		config_tab.grid_rowconfigure(row, weight=1, uniform="a")
	for col in range(0, total_config_tab_cols):
		config_tab.grid_columnconfigure(col, weight=1, uniform="a")
	
	# Regular Options
	#clear_data_directory_button = Button(config_tab, text="Clear Data Directory", command=...)

	regular_options_labelframe = LabelFrame(config_tab, text="Options")
	regular_options_labelframe.grid(column=0, row=0, columnspan=4, rowspan=8)
	
	data_directory_location_labelframe = LabelFrame(regular_options_labelframe, text="Choose Data Directory")
	data_directory_location_labelframe.pack(expand=True, fill='x')
	global data_directory_path
	data_directory_path = StringVar(value=current_data_directory)
	set_data_directory_location_button = Button(data_directory_location_labelframe, text="Data Directory Location", command=gui_set_data_directory)
	set_data_directory_location_button.pack(expand=True, fill='x', side=tk.TOP)
	data_directory_location_label = Label(data_directory_location_labelframe, textvariable=data_directory_path)
	data_directory_location_label.pack(expand=True, fill='both', side=tk.BOTTOM)

	log_directory_location_labelframe = LabelFrame(regular_options_labelframe, text="Choose Log Directory")
	log_directory_location_labelframe.pack(expand=True, fill='x')
	global log_directory_path
	log_directory_path = StringVar(value=current_log_directory)
	set_log_location_button = Button(log_directory_location_labelframe, text="Log Directory", command=gui_set_log_directory)
	set_log_location_button.pack(expand=True, fill='both', side=tk.TOP)
	log_directory_location_label = Label(log_directory_location_labelframe, textvariable=log_directory_path)
	log_directory_location_label.pack(expand=True, fill='both', side=tk.BOTTOM)

	database_directory_location_labelframe = LabelFrame(regular_options_labelframe, text="Choose Database Directory")
	database_directory_location_labelframe.pack(expand=True, fill='x')
	global database_directory_path
	database_directory_path = StringVar(value=current_data_directory)
	set_database_location_button = Button(database_directory_location_labelframe, text="Database Directory", command=gui_set_database_directory)
	set_database_location_button.pack(expand=True, fill='both', side=tk.TOP)
	database_location_label = Label(database_directory_location_labelframe, textvariable=database_directory_path)
	database_location_label.pack(expand=True, fill='both', side=tk.BOTTOM)

	prefix_cache_location_labelframe = LabelFrame(regular_options_labelframe, text="Choose Prefix Cache Directory")
	prefix_cache_location_labelframe.pack(expand=True, fill='x')
	global prefix_cache_directory_path
	prefix_cache_directory_path = StringVar(value=current_prefix_cache_directory)
	set_prefix_cache_location_button = Button(prefix_cache_location_labelframe, text="Directory Cache", command=gui_set_prefix_cache_directory)
	set_prefix_cache_location_button.pack(expand=True, fill='both', side=tk.TOP)
	prefix_cache_location_label = Label(prefix_cache_location_labelframe, textvariable=prefix_cache_directory_path)
	prefix_cache_location_label.pack(expand=True, fill='both', side=tk.BOTTOM)

	buffer_location_labelframe = LabelFrame(regular_options_labelframe, text="Choose Buffer Directory")
	buffer_location_labelframe.pack(expand=True, fill='x')
	global buffer_directory_path
	buffer_directory_path = StringVar(value=current_buffer_directory)
	set_buffer_location_button = Button(buffer_location_labelframe, text="Buffer Directory", command=gui_set_buffer_directory)
	set_buffer_location_button.pack(expand=True, fill='both', side=tk.TOP)
	buffer_location_label = Label(buffer_location_labelframe, textvariable=buffer_directory_path)
	buffer_location_label.pack(expand=True, fill='both', side=tk.BOTTOM)

	download_location_labelframe = LabelFrame(regular_options_labelframe, text="Choose Download Directory")
	download_location_labelframe.pack(expand=True, fill='x')
	global download_directory_path
	download_directory_path = StringVar(value=current_download_directory)
	set_download_location_button = Button(download_location_labelframe, text="Download Directory", command=gui_set_download_directory)
	set_download_location_button.pack(expand=True, fill='both', side=tk.TOP)
	download_location_label = Label(download_location_labelframe, textvariable=download_directory_path)
	download_location_label.pack(expand=True, fill='both', side=tk.BOTTOM)

	threads_labelframe = LabelFrame(regular_options_labelframe, text="Threads")
	threads_labelframe.pack(expand=True, fill='both')
	global threads_selection
	threads_selection = StringVar(value="4")
	threads_combobox = Combobox(threads_labelframe, textvariable=threads_selection, values=thread_options)
	threads_combobox.pack(expand=True, fill='x')

	# Debug Options
	
	global debug_options
	debug_options_labelframe = LabelFrame(config_tab, text="Debug Options", width=60, height=60)
	debug_options_labelframe.grid(column=9, row=0, columnspan=7, rowspan=14, ipadx=8, ipady=8)

	debug_selection_frame = Frame(debug_options_labelframe)
	debug_selection_frame.pack(expand=True, fill='x', side=tk.TOP)
	global debug_selection
	debug_selection = StringVar(value=True)
	enable_debug_radio_button = Radiobutton(debug_selection_frame, text="Enable", variable=debug_selection, value=True, command=set_debug_options_state)
	enable_debug_radio_button.pack(expand=True, fill='x', side=tk.LEFT)
	disable_debug_radio_button = Radiobutton(debug_selection_frame, text="Disable", variable=debug_selection, value=False, command=set_debug_options_state)
	disable_debug_radio_button.pack(expand=True, fill='x', side=tk.RIGHT)

	debug_bucket_cache_labelframe = LabelFrame(debug_options_labelframe, text="S3 bucket caching")
	debug_bucket_cache_labelframe.pack(expand=True, fill='x')
	global debug_file_caching_selection
	debug_file_caching_selection = StringVar(value=True)
	enable_bucket_caching_radio_button = Radiobutton(debug_bucket_cache_labelframe, text="Enabled", variable=debug_file_caching_selection, value=True)
	enable_bucket_caching_radio_button.pack(expand=True, fill='x', side=tk.LEFT, padx=4, pady=8)
	disable_bucket_caching_radio_button = Radiobutton(debug_bucket_cache_labelframe, text="Disabled", variable=debug_file_caching_selection, value=False)
	disable_bucket_caching_radio_button.pack(expand=True, fill='x', side=tk.RIGHT, padx=4, pady=4)
	debug_options.append(enable_bucket_caching_radio_button)
	debug_options.append(disable_bucket_caching_radio_button)

	debug_file_downloading_labelframe = LabelFrame(debug_options_labelframe, text="File Downloading")
	debug_file_downloading_labelframe.pack(expand=True, fill='x')
	global debug_file_downloading_selection
	debug_file_downloading_selection = StringVar(value=True)
	enable_file_downloading_radio_button = Radiobutton(debug_file_downloading_labelframe, text="Enabled", variable=debug_file_downloading_selection, value=True)
	enable_file_downloading_radio_button.pack(expand=True, fill='x', side=tk.LEFT, padx=4, pady=4)
	disable_file_downloading_radio_button = Radiobutton(debug_file_downloading_labelframe, text="Disabled", variable=debug_file_downloading_selection, value=False)
	disable_file_downloading_radio_button.pack(expand=True, fill='x', side=tk.RIGHT, padx=4, pady=4)
	debug_options.append(enable_file_downloading_radio_button)
	debug_options.append(disable_file_downloading_radio_button)

	debug_file_validation_labelframe = LabelFrame(debug_options_labelframe, text="File Validation")
	debug_file_validation_labelframe.pack(expand=True, fill='x')
	global debug_file_validation_selection
	debug_file_validation_selection = StringVar(value=True)
	enable_file_validation_radio_button = Radiobutton(debug_file_validation_labelframe, text="Enabled", variable=debug_file_validation_selection, value=True)
	enable_file_validation_radio_button.pack(expand=True, fill='x', side=tk.LEFT, padx=4, pady=4)
	disable_file_validation_radio_button = Radiobutton(debug_file_validation_labelframe, text="Disabled", variable=debug_file_validation_selection, value=False)
	disable_file_validation_radio_button.pack(expand=True, fill='x', side=tk.RIGHT, padx=4, pady=4)
	debug_options.append(enable_file_validation_radio_button)
	debug_options.append(disable_file_validation_radio_button)

	console_log_options_labelframe = LabelFrame(debug_options_labelframe, text="Console log level")
	console_log_options_labelframe.pack(expand=True, fill='x')
	global console_log_level
	console_log_level = StringVar(value="INFO")
	console_log_level_combobox = Combobox(console_log_options_labelframe, textvariable=console_log_level, values=LOG_LEVELS)
	console_log_level_combobox.pack(expand=True, fill='both')
	debug_options.append(console_log_level_combobox)

	file_log_options_labelframe = LabelFrame(debug_options_labelframe, text="File log level")
	file_log_options_labelframe.pack(expand=True, fill='x')
	global file_log_level
	file_log_level = StringVar(value="WARNING")
	file_log_level_combobox = Combobox(file_log_options_labelframe, textvariable=file_log_level, values=LOG_LEVELS)
	file_log_level_combobox.pack(expand=True, fill='both')
	debug_options.append(file_log_level_combobox)

	tabs.pack(expand=True, fill='both')

	debug_selection.set(False)
	window.after(100, set_debug_options_state)
	window.after(100, check_events)
	window.mainloop()

if __name__ == "__main__":
	main()