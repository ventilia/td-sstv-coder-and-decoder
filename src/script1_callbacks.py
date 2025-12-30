"""
Script CHOP Callbacks

me - this DAT

scriptOp - the OP which is cooking
"""

from typing import Any
from enum import StrEnum

import numpy as np


# press 'Setup Parameters' in the OP to call this function to re-create the
# parameters.
def onSetupParameters(scriptOp: scriptCHOP):
	"""
	Called to setup custom parameters for the Script CHOP.
	"""
	# page = scriptOp.appendCustomPage('Custom')
	# p = page.appendPulse('Pulepar', label='Pulse')
	
	return

def onPulse(par: Any):
	"""
	Called when a custom pulse parameter is pushed.
	
	Args:
		par: The parameter that was pulsed
	"""
	return


def onCook(scriptOp: scriptCHOP):
	sample_rate = parent.SSTV.SampleRate
	
	imageChop = op('topto1')
	buffer_size =  int(sample_rate / project.cookRate)
	try:
		signal = parent.SSTV.GetSamples(imageChop, buffer_size)
	except ValueError:
		signal = np.zeros(buffer_size)
	
	scriptOp.clear()
	scriptOp.rate = sample_rate
	
	channel = scriptOp.appendChan('out')
	channel.vals = signal
	

def onGetCookLevel(scriptOp: scriptCHOP) -> CookLevel:
	"""
	Sets the scriptOp's cook level, the conditions necessary to cause a cook.

	Return one of the following:
		CookLevel.AUTOMATIC - inputs changed and output being used. TD default
		                      behavior.
		CookLevel.ON_CHANGE - inputs changed, output used or not.
		CookLevel.WHEN_USED - every frame when output is being used
		CookLevel.ALWAYS - every frame
	"""

	return CookLevel.WHEN_USED
