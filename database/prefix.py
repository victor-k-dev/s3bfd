# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pickle
from pathlib import Path

def load(path:Path):
	if path.exists():
		with open(path, "rb") as f:
			return pickle.load(f)

def save(path:Path, prefix_cache):
	with open(path, "wb") as f:
		pickle.dump(prefix_cache, f)