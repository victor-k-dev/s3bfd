# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import tkinter as tk
from tkinter import filedialog, Text, StringVar, IntVar, messagebox, Event as tkEvent
from tkinter.ttk import (
	Label, LabelFrame, Notebook, Frame, 
	Button, Progressbar, Scrollbar, Radiobutton, 
	Combobox, Entry, Treeview
	)
from .widgets import (
	StartButton, 
	StopButton,
	DownloadButton,
	DirectoryWindow,
	ShowDirectoriesButton,
	DirectoryTree,
	LogWindow,
	InputURL,
	InputPrefix,
	InputRegion,
	SelectParameterButtons,
	SelectDirectoryButtons,
)

from process.process import start, stop, single_file_start, multi_file_start
from process.parameters import Parameters
from utils.globals import Globals
from pathlib import Path

def init_gui():

	def init_process():
		Parameters.url = input_url.get_url()
		Parameters.prefix = Path(input_prefix.get_prefix())
		Parameters.region = input_region.get_region()
		if Parameters.url == Parameters.region:
			Parameters.s3_url = Parameters.url
		Parameters.cache_only = True
		Globals.logger.debug(
			Parameters.url, 
			Parameters.prefix, 
			Parameters.region, 
			Parameters.s3_url, 
			Parameters.download_threads,
			Parameters.requests_threads,
			Parameters.total_threads,
			Parameters.no_gui,
			Parameters.skip_validation,
			Parameters.cache_only,
			Parameters.tree_id,
		)
		start()

		return
	
	def init_download():
		if directory_window.directory_tree.selection_type == "dir":
			Globals.logger.debug(directory_window.directory_tree.selection)
			Globals.logger.debug(directory_window.directory_tree.selection[3])
			
			Parameters.url = directory_window.directory_tree.selection_root
			Parameters.multi_file_directory = Path(directory_window.directory_tree.selection[3])
			
			url = "https://%s/" % directory_window.directory_tree.selection_root
			Parameters.multi_file_base_url = url
			
			multi_file_start()
		elif directory_window.directory_tree.selection_type == "file":
			Globals.logger.debug(directory_window.directory_tree.selection)

			url = "https://%s/%s" % (directory_window.directory_tree.selection_root, directory_window.directory_tree.selection[2])
			Globals.logger.debug(url)
			Parameters.single_file_path = directory_window.directory_tree.selection[2]
			Parameters.single_file_url = url
			single_file_start()
			
		return
	
	window = tk.Tk()
	window.title("s3bfd")
	window.geometry("1280x720")
	window.resizable(width=False, height=False)
	
	tabs = Notebook(window)
	main_tab = Frame(tabs)
	#log_tab = Frame(tabs)
	config_tab = Frame(tabs)
	tabs.add(main_tab, text="Main")
	#tabs.add(log_tab, text="Log")
	tabs.add(config_tab, text="Config")

	total_main_tab_rows = 12
	total_main_tab_cols = 16
	for row in range(0,total_main_tab_rows):
		main_tab.grid_rowconfigure(row, weight=1, uniform="a")
	for col in range(0, total_main_tab_cols):
		main_tab.grid_columnconfigure(col, weight=1, uniform="a")

	start_button = StartButton(main_tab)
	start_button.set_command(init_process)
	stop_button = StopButton(main_tab)
	stop_button.set_command(stop)
	
	#log_window = LogWindow(main_tab)
	parameter_buttons = SelectParameterButtons(main_tab)
	directory_buttons = SelectDirectoryButtons(main_tab)
	input_url = InputURL(main_tab)
	input_prefix = InputPrefix(main_tab)
	input_region = InputRegion(main_tab)

	input_url.set_url("historical-data.kucoin.com")
	input_prefix.set_prefix("data/")
	input_region.set_region("historical-data.kucoin.com")

	directory_window = DirectoryWindow()
	directory_window.set_root(window)
	show_directories_button = ShowDirectoriesButton(main_tab)
	show_directories_button.set_command(directory_window.create_window)
	directory_window.download_func = init_download
	#directory_window.download_button.set_command(init_download)

	tabs.pack(expand=True, fill='both')
	window.mainloop()