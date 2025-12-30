"""
DAT Execute DAT

me - this DAT

dat - the changed DAT
prevDAT - a simulated DAT containing previous contents

Info contains specific details on what's changed:

	rowsChanged	- list of row indices with different contents
	rowsAdded	- list of added row name indices (in dat)
	rowsRemoved	- list of removed row name indices (in prevDAT)

	colsChanged	- list of column indices with different contents
	colsAdded	- list of added column name indices (in dat)
	colsRemoved	- list of removed column name indices (in prevDAT)

	cellsChanged 	- list of cells that have changed content

	sizeChanged	- bool, true if number of rows or columns changed

Make sure the corresponding toggle is enabled in the DAT Execute DAT.
"""

from typing import List

def onTableChange(dat: DAT, prevDAT: DAT, info: ChangedDATInfo):
	"""
	Called when a table change occurs. This callback can be used to evaluate 
	several change conditions simultaneously.

	Args:
		dat: The changed DAT
		prevDAT: The DAT containing previous contents
		info: ChangedDATInfo object with specific details on what changed
	"""
	mode_name = dat[0, 0]
	parent.SSTV.SetMode(mode_name)

# The following legacy callbacks can be used to track individual changes.
# Note that if rows or columns are deleted, sizeChange will be called instead
# of row/col/cellChange.

def onRowChange(dat: DAT, rows: List[int]):
	"""
	Called when rows change.
	
	Args:
		dat: The changed DAT
		rows: A list of row indices that changed
	"""
	return

def onColChange(dat: DAT, cols: List[int]):
	"""
	Called when columns change.
	
	Args:
		dat: The changed DAT
		cols: A list of column indices that changed
	"""
	return

def onCellChange(dat: DAT, cells: List[Cell], prev: List[str]):
	"""
	Called when cells change.
	
	Args:
		dat: The changed DAT
		cells: List of cells that have changed content
		prev: List of previous string contents of the changed cells
	"""
	return

def onSizeChange(dat: DAT):
	"""
	Called when the size (rows or columns) of the DAT changes.
	
	Args:
		dat: The changed DAT
	"""
	return
