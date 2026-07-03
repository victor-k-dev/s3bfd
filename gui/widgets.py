# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import tkinter as tk
from database.fetch import fetch_children
from utils.globals import Globals
from utils.paths import CurrentPaths
from process.parameters import Parameters
from tkinter import filedialog, Text, StringVar, BooleanVar, IntVar, messagebox, Event as tkEvent, Toplevel
from tkinter.ttk import (
	Label, LabelFrame, Notebook, Frame, 
	Button, Progressbar, Scrollbar, Checkbutton,
	Combobox, Entry, Treeview
	)
from pathlib import Path
from logging import LogRecord
from typing import Literal

class StartButton():
	def __init__(self, tab, text="Start", func=None):
		self.button = Button(tab, text=text, command=self._press)
		self.func = func
		self._setup()

	def _setup(self):
		self.button.grid(column=0, columnspan=2, row=10)

	def _press(self):
		# TODO: read currently set parameters/input fields etc., pass to func()
		# OR: set params so func() can read them
		self.func()

	def set_command(self, func):
		self.func = func

class StopButton():
	def __init__(self, tab, text="Stop", func=None):
		self.button = Button(tab, text=text, command=self._press)
		self.func = func
		self._setup()

	def _setup(self):
		self.button.grid(column=2, columnspan=2, row=10)
		#self.button.configure(state='disabled')
	
	def _press(self):
		self.func()

	def set_command(self, func):
		self.func = func

class DownloadButton():
	def __init__(self, tab, text="Download", func=None):
		self.button = Button(tab, text=text, command=self._press)
		self.func = func
		self.download_target = None # {"is_dir": ..., "prefix": ..., "file_path": ...}
		self._setup()

	def _setup(self):
		self.button.grid(column=2, columnspan=2, row=12)
		self.button.configure(state='disabled')

	def _press(self):
		self.func()
	
	def set_state(self, state:Literal["enabled", "disabled"]):
		self.button.configure(state=state)

	def set_download_target(self, download_target):
		self.download_target = download_target

	def set_command(self, func):
		self.func = func

class ShowDirectoriesButton():
	def __init__(self, tab, text="Show Directories", func=None):
		self.button = Button(tab, text=text, command=self._press)
		self.func = func
		self._setup()

	def _setup(self):
		self.button.grid(column=4, columnspan=2, row=10)
	
	def _press(self):
		self.func()

	def set_command(self, func):
		self.func = func

class SelectParameterButtons():
	def __init__(self, window):
		self.label_frame = LabelFrame(window, text="Options")
		self.cache_only_button = Checkbutton(self.label_frame, text="Cache only", command=self._change_cache_only)
		self.skip_validation_button = Checkbutton(self.label_frame, text="Skip validation", command=self._change_skip_validation)
		self.process_in_memory_button = Checkbutton(self.label_frame, text="Process files in memory", command=self._change_process_in_memory)
		self.save_to_disk_button = Checkbutton(self.label_frame, text="Save files to disk", command=self._change_save_to_disk)
		self.delete_after_validation_button = Checkbutton(self.label_frame, text="Delete files after validation", command=self._change_delete_after_validation)
		
		self.cache_only_variable = BooleanVar(self.cache_only_button, value=Parameters.cache_only)
		self.skip_validation_variable = BooleanVar(self.skip_validation_button, value=Parameters.skip_validation)
		self.process_in_memory_variable = BooleanVar(self.process_in_memory_button, value=Parameters.process_in_memory)
		self.save_to_disk_variable = BooleanVar(self.save_to_disk_button, value=Parameters.save_to_disk)
		self.delete_after_validation_variable = BooleanVar(self.delete_after_validation_button, value=Parameters.delete_after_validation)

		self._setup()
		self._change_cache_only()
		self._change_skip_validation()
		self._change_process_in_memory()
		self._change_save_to_disk()
		self._change_delete_after_validation()

	def _setup(self):
		self.label_frame.grid(column=2, columnspan=4, row=3, rowspan=8)
		self.cache_only_button.pack(expand=True, fill="both")
		self.skip_validation_button.pack(expand=True, fill="both")
		self.process_in_memory_button.pack(expand=True, fill="both")
		self.save_to_disk_button.pack(expand=True, fill="both")
		self.delete_after_validation_button.pack(expand=True, fill="both")

		self.cache_only_button.configure(variable=self.cache_only_variable)
		self.skip_validation_button.configure(variable=self.skip_validation_variable)
		self.process_in_memory_button.configure(variable=self.process_in_memory_variable)
		self.save_to_disk_button.configure(variable=self.save_to_disk_variable)
		self.delete_after_validation_button.configure(variable=self.delete_after_validation_variable)
	
	def _change_cache_only(self):
		if self.cache_only_variable.get():
			Parameters.cache_only = self.cache_only_variable.get()
			self.skip_validation_variable.set(True)
			self.process_in_memory_variable.set(False)
			self.save_to_disk_variable.set(False)
			self.delete_after_validation_variable.set(False)
			self.skip_validation_button.config(state="disabled")
			self.process_in_memory_button.config(state="disabled")
			self.save_to_disk_button.config(state="disabled")
			self.delete_after_validation_button.config(state="disabled")
		else:
			Parameters.cache_only = self.cache_only_variable.get()
			self.skip_validation_button.config(state="enabled")
			self.process_in_memory_button.config(state="enabled")
			self.save_to_disk_button.config(state="enabled")
			self.delete_after_validation_button.config(state="enabled")
			self.skip_validation_variable.set(False)
		Globals.logger.debug("%s, %s, %s, %s, %s" % (Parameters.cache_only, Parameters.skip_validation, Parameters.process_in_memory, Parameters.save_to_disk, Parameters.delete_after_validation))
		
	def _change_skip_validation(self):
		if self.skip_validation_variable.get():
			Parameters.skip_validation = self.skip_validation_variable.get()
			self.cache_only_variable.set(False)
			self.cache_only_button.config(state="disabled")
		else:
			Parameters.skip_validation = self.skip_validation_variable.get()
			self.cache_only_button.config(state="enabled")
		Globals.logger.debug("%s, %s, %s, %s, %s" % (Parameters.cache_only, Parameters.skip_validation, Parameters.process_in_memory, Parameters.save_to_disk, Parameters.delete_after_validation))

	def _change_process_in_memory(self):
		Parameters.process_in_memory = self.process_in_memory_variable.get()
		Globals.logger.debug("%s, %s, %s, %s, %s" % (Parameters.cache_only, Parameters.skip_validation, Parameters.process_in_memory, Parameters.save_to_disk, Parameters.delete_after_validation))

	def _change_save_to_disk(self):
		if self.save_to_disk_variable.get():
			Parameters.save_to_disk = self.save_to_disk_variable.get()
			self.delete_after_validation_variable.set(False)
			self.delete_after_validation_button.config(state="disabled")
		else:
			Parameters.save_to_disk = self.save_to_disk_variable.get()
			self.delete_after_validation_button.config(state="enabled")
		Globals.logger.debug("%s, %s, %s, %s, %s" % (Parameters.cache_only, Parameters.skip_validation, Parameters.process_in_memory, Parameters.save_to_disk, Parameters.delete_after_validation))
			
	def _change_delete_after_validation(self):
		if self.delete_after_validation_variable.get():
			Parameters.delete_after_validation = self.delete_after_validation_variable.get()
			self.save_to_disk_variable.set(False)
			self.save_to_disk_button.config(state="disabled")
		else:
			Parameters.delete_after_validation = self.delete_after_validation_variable.get()
			self.save_to_disk_button.config(state="enabled")
		Globals.logger.debug("%s, %s, %s, %s, %s" % (Parameters.cache_only, Parameters.skip_validation, Parameters.process_in_memory, Parameters.save_to_disk, Parameters.delete_after_validation))

class SelectDirectoryButtons():
	def __init__(self, window):
		self.label_frame = LabelFrame(window, text="Change Directories")
		self.download_directory_button = Button(self.label_frame, text="Choose Download Directory", command=self._change_download_directory)
		self.current_download_directory_variable = StringVar(self.download_directory_button, value=str(CurrentPaths.download_directory))
		self.download_directory_label = Label(self.label_frame, textvariable=self.current_download_directory_variable)
		self._setup()

	def _setup(self):
		self.label_frame.grid(column=2, columnspan=2, row=8, rowspan=2)
		self.download_directory_label.pack(expand=True, fill="x", side=tk.TOP)
		self.download_directory_button.pack(expand=True, fill="x", side=tk.BOTTOM)

	def _change_download_directory(self):
		new_directory = filedialog.askdirectory()
		if Path(new_directory).is_dir() and Path(new_directory).exists():
			self.current_download_directory_variable.set(new_directory)
			CurrentPaths.download_directory = Path(new_directory)
"""
def gui_set_download_directory():
	global current_download_directory
	new_dir = filedialog.askdirectory()
	if Path(new_dir).is_dir and Path(new_dir).exists():
		current_download_directory = new_dir
		download_directory_path.set(new_dir)
	else:
		pass
"""

class InputURL():
	def __init__(self, tab, text="URL"):
		self.labelframe = LabelFrame(tab, text=text)
		self.url = StringVar()
		self.entry = Entry(self.labelframe, textvariable=self.url)
		self._setup()

	def _setup(self):
		self.labelframe.grid(column=1, row=5, columnspan=2)
		self.entry.pack(expand=True, fill='both')

	def set_url(self, url):
		self.url.set(url)

	def get_url(self) -> str:
		return self.url.get()

class InputPrefix():
	def __init__(self, tab, text="Prefix"):
		self.labelframe = LabelFrame(tab, text=text)
		self.prefix = StringVar()
		self.entry = Entry(self.labelframe, textvariable=self.prefix)
		self._setup()

	def _setup(self):
		self.labelframe.grid(column=1, row=6, columnspan=2)
		self.entry.pack(expand=True, fill='both')

	def set_prefix(self, prefix):
		self.prefix.set(prefix)
	
	def get_prefix(self) -> str:
		return self.prefix.get()

class InputRegion():
	def __init__(self, tab, text="Region"):
		self.labelframe = LabelFrame(tab, text=text)
		self.region = StringVar()
		self.entry = Entry(self.labelframe, textvariable=self.region)
		self._setup()

	def _setup(self):
		self.labelframe.grid(column=1, row=7, columnspan=2)
		self.entry.pack(expand=True, fill='both')

	def set_region(self, region):
		self.region.set(region)

	def get_region(self) -> str:
		return self.region.get()

class DirectoryTree():
	def __init__(self, tab, download_button:DownloadButton, text="Directories", columns=["Name", "Size", "Download Date", "Path"]):
		self.labelframe = LabelFrame(tab, text=text)
		self.vertical_scrollbar = Scrollbar(self.labelframe, orient='vertical')
		self.horizontal_scrollbar = Scrollbar(self.labelframe, orient='horizontal')
		self.tree = Treeview(self.labelframe, columns=columns, height=16)
		self.download_button = download_button
		self.selection_type = None
		self.selection = None
		self.selection_root = None
		self._setup()

	def _setup(self):
		self.labelframe.grid(column=0, row=0, rowspan=11, columnspan=16, pady=20)
		self.vertical_scrollbar.pack(side=tk.RIGHT, fill="y")
		self.horizontal_scrollbar.pack(side=tk.BOTTOM, fill="x")
		self.vertical_scrollbar.config(command=self.tree.yview)
		self.horizontal_scrollbar.config(command=self.tree.xview)

		self.tree.pack(side=tk.LEFT, expand=True, fill='both')
		self.tree.bind('<<TreeviewOpen>>', self._add_files_ondemand)
		self.tree.bind('<<TreeviewClose>>', self._remove_files_ondemand)
		self.tree.bind('<<TreeviewSelect>>', self._set_download_target)
		self._init_tree()

	def _add_files_ondemand(self, event:tkEvent):
		tree_children = event.widget.get_children(event.widget.focus())
		root_of_selected = None
		key = None
		children = None
		
		if self.selection_type == "dir":
			root_node = event.widget.parent(event.widget.focus())
			#Globals.logger.debug(root_node)
			while True:
				if event.widget.parent(root_node):
					root_node = event.widget.parent(root_node)
				else:
					root_of_selected = event.widget.item(root_node, option="text")
					break
			
			key = Path(event.widget.item(event.widget.focus(), option="values")[3])
			#Globals.logger.debug(key)
			children = Globals.s3bfd_prefix_cache[root_of_selected][key]["children"]

			if (len(tree_children) == 1) and ("null" in event.widget.item(tree_children[0])["tags"]):
				self.tree.delete(tree_children[0])
				results = fetch_children(children)
				for result in results:
					#Globals.logger.debug(result.parent_id, result.id)
					self.tree.insert(parent=result.parent_id, index=result.node_id, iid=result.node_id, text=result.name, tags="file",
						 values=[result.size_bytes, result.downloaded_at, result.path])#,result.checksum, result.checksum_type, result.original_checksum, result.original_checksum_type, result.path])

	def _remove_files_ondemand(self, event:tkEvent):
		children_to_delete = [int(child) for child in event.widget.get_children(event.widget.focus()) if "file" in event.widget.item(child)["tags"]]

		for child in children_to_delete:
			self.tree.delete(child)
		children = [event.widget.item(child) for child in event.widget.get_children(event.widget.focus())]
		child_tags = []
		for child in children:
			child_tags.extend(child["tags"])
		if ("null" not in child_tags) and ("dir" not in child_tags):
			self.tree.insert(parent=event.widget.focus(), index=0, tags="null")

	def _set_download_target(self, event:tkEvent):
		if "file" in event.widget.item(event.widget.focus())["tags"]:
			self.download_button.button.configure(text="Download File")
			self.download_button.set_state("enabled")
			self.selection_type = "file"
			self.selection = event.widget.item(event.widget.focus(), option="values")

			root_node = event.widget.parent(event.widget.focus())
			while True:
				if event.widget.parent(root_node):
					root_node = event.widget.parent(root_node)
				else:
					self.selection_root = event.widget.item(root_node, option="text")
					break

		elif "dir" in event.widget.item(event.widget.focus())["tags"]:
			self.download_button.button.configure(text="Download Files")
			self.download_button.set_state("enabled")
			self.selection_type = "dir"
			self.selection = event.widget.item(event.widget.focus(), option="values")

			root_node = event.widget.parent(event.widget.focus())
			while True:
				if event.widget.parent(root_node):
					root_node = event.widget.parent(root_node)
				else:
					self.selection_root = event.widget.item(root_node, option="text")
					break
		else:
			self.download_button.set_state("disabled")
			self.selection_type = None
			self.selection = None
			self.selection_root = None

	def _init_tree(self):
		#debug_fetch()
		# Insert root node(s)
		cache = Globals.s3bfd_prefix_cache
		for url in list(cache):
			root = self.tree.insert(parent="",index=-1,text=url,open=True,tags="root")

		for bucket_url_data in cache.values():
			for path_data in bucket_url_data.values():
				if (path_data["parent_id"] is None) and (not self.tree.exists(path_data["node_id"])):
					#Globals.logger.debug(f"Inserting: {path_data["parent_id"]}, {path_data["id"]}, {path_data["id"]}, {path_data["name"]}")
					self.tree.insert(parent=root, index=path_data["node_id"], iid=path_data["node_id"], text=path_data["name"], open=True, tags="dir", 
					  values=[None, None, None, path_data["path"]])
					break

		for bucket_url_data in cache.values():
			for path_data in bucket_url_data.values():
				if (path_data["parent_id"] is not None) and (not self.tree.exists(path_data["node_id"])):
					#Globals.logger.debug(f"Inserting: {path_data["parent_id"]}, {path_data["id"]}, {path_data["id"]}, {path_data["name"]}")
					self.tree.insert(parent=path_data["parent_id"], index=path_data["node_id"], iid=path_data["node_id"], text=path_data["name"], tags="dir", 
					  values=[None, None, None, path_data["path"]])

			for path_data in bucket_url_data.values():
				#Globals.logger.debug(file_tree.get_children(str(child_data["id"])))
				if len(self.tree.get_children(path_data["node_id"])) < 1:
					#Globals.logger.debug(file_tree.item(path_data["id"])["text"])
					self.tree.insert(parent=path_data["node_id"], index=0, tags="null")

class LogWindow():
	def __init__(self, tab, text="Log"):
		self.labelframe = LabelFrame(tab, text=text)
		self.vertical_scrollbar = Scrollbar(self.labelframe, orient='vertical')
		self.log_text = Text(self.labelframe, height=36, wrap="word")
		self.scrollback_limit = 0
		self.row_count = 0
		self._setup()
	
	def _setup(self):
		self.vertical_scrollbar.pack(side=tk.RIGHT, fill="y")
		self.vertical_scrollbar.config(command=self.log_text.yview)

		self.labelframe.grid(column=9, row=0, rowspan=11, columnspan=7, pady=20)

		self.log_text.pack(side=tk.LEFT, expand=True, fill='both')
		self.log_text.config(yscrollcommand=self.vertical_scrollbar.set)
		self.log_text.configure(state='disabled')

	def _print(self, message:LogRecord):
		self.log_text.configure(state='normal')
		if self.scrollback_limit > 0 and self.row_count >= self.scrollback_limit:
			self.log_text.replace("1.0", "2.0", "")
		else:
			self.row_count += 1
		message = Globals.formatter.format(message)
		self.log_text.insert(tk.INSERT, message + "\n")
		self.log_text.see(index=tk.END)
		self.log_text.configure(state='disabled')

class DirectoryWindow():
	def __init__(self):
		self.root = None
		self.window = None
		self.download_button = None
		self.directory_tree = None
		self.download_func = None

	def set_root(self, root):
		self.root = root

	def create_window(self):
		if self.window is None and self.root:
			self.window = Toplevel(self.root, takefocus=True)
			self.window.title("s3bfd - Directories")
			self.window.geometry("1280x720")
			self.window.resizable(width=False, height=False)

			win_rows = 12
			win_cols = 16
			for row in range(0,win_rows):
				self.window.grid_rowconfigure(row, weight=1, uniform="a")
			for col in range(0, win_cols):
				self.window.grid_columnconfigure(col, weight=1, uniform="a")

			self.window.protocol("WM_DELETE_WINDOW", self.destroy_window)
			
			self._create_widgets()
		else:
			Globals.logger.warning("directory window already exists")
	
	def _create_widgets(self):
		self.download_button = DownloadButton(self.window)
		self.download_button.set_command(self.download_func)
		self.directory_tree = DirectoryTree(self.window, self.download_button)

	def destroy_window(self):
		if self.window:
			self.window.destroy()
			self.window = None
			self.download_button = None
			self.directory_tree = None
		else:
			Globals.logger.warning("no directory window to destroy")

	def _setup(self) -> None:
		self.window.title("s3bfd - Directories")
		self.window.geometry("1280x720")
		self.window.resizable(width=False, height=False)

	#def set_download_button_command(self, func) -> None:
	#	self.download_button.set_command(func)

	

