# -*- coding: utf-8 -*-
import wx, re, subprocess, os, sys, wave, glob
from os.path import isdir, isfile, join, basename, dirname
import numpy as np

## list of cmu vowels sorted into columns (as displayed on the window)
cmu = [('IY', 'IH', 'EY', 'EH', 'AE'), ('', '','AH', '', ''), ('UW', 'UH', 'OW', 'AO', 'AA'), ('AY','OY', 'AW', 'IW', 'ER')]

def DrawCaptionOntoBitmap(imageFile, captionTxt):
	## adapted from Ray Pasco's comment at https://groups.google.com/forum/#!topic/wxpython-users/9UYtstGL6tU
	## comments are by Ray in this function
	# Create a dc "canvas" onto which the caption text will be drawn
	# in order to get the text's extent (size).
	bmSize = (100, 100)     # any size larger than the expexted text extent.
	bm = wx.EmptyBitmap( *bmSize )
	dc = wx.MemoryDC(bm)
	txtPos = (10, 10)                     # an offset so the text doesn't get clipped
	dc.DrawText(captionTxt, *txtPos)
	txtWid, txtHgt = dc.GetTextExtent( captionTxt )
	dc.SelectObject( wx.NullBitmap )        # done with this dc; not used again

	# Draw the caption on the file graphic bitmap.
	if imageFile:
		imgBmap = wx.Image( imageFile, wx.BITMAP_TYPE_ANY ).ConvertToBitmap()
	else:
		imgBmap = wx.EmptyBitmap(60,60)
	bmapX, bmapY = imgBmap.GetSize()


	# Create a dc "canvas" onto which the caption text  will be drawn
	dc = wx.MemoryDC( imgBmap )
	dc.SetBrush( wx.Brush( wx.Colour( 0, 0, 0 ), wx.SOLID ) )

	# Draw text at the top of the bitmap
	txtPosX = (bmapX - txtWid) / 2
	txtPosY = (bmapY - txtHgt) / 2
	dc.DrawText( captionTxt, txtPosX, txtPosY )

	# Done doing text drawing.
	dc.SelectObject( wx.NullBitmap )        # Done with this dc

	return imgBmap

def UpdateFAVE(filePath, outPath):
	## converts layout of formant.txt files output from FAVE-extract
	## so they can be read by FVR
	delim = '\t'
	headingsRow = 2
	## read in files
	files = glob.glob(join(filePath,'*formant.txt'))
	## iterate over files 
	for fPath in files:
		lines = []
		with open(fPath) as f:
			for i,line in enumerate(f):
				if i < headingsRow: ## if the row is before the heading row
					lines.append(line)
				elif i == headingsRow: ## get location of relevant columns from the heading row
					line = line.split(delim)
					newLine = []
					percInts = []
					poleInt = None
					for j,name in enumerate(line):
						if 'F1@' in name:
							name = 'F'+name[2:]
							percInts.append(j)
						elif 'F2@' in name:
							continue
						elif 'poles' in name:
							name = delim.join(['F@Max3', 'F@Max4', 'F@Max5', 'F@Max6'])
							poleInt = j
						newLine.append(name)
					lines.append(delim.join(newLine))
				else:  ## convert rows to new format
					line = line.split(delim)
					newLine = []
					skip = False
					for j,value in enumerate(line):
						if skip:
							skip = False
							continue
						if j in percInts:
							value = ', '.join(line[j:j+2])
							skip = True
						elif poleInt != None and j == poleInt:
							value = delim.join([', '.join(v.split(', ')[:2]) for v in value.strip('[').strip(']').split('],[')])
						newLine.append(value)
					lines.append(delim.join(newLine))
		## write new file
		with open(join(outPath, basename(fPath)), 'w') as out:
			for l in lines:
				out.write(l)


class VowelButton():
	## class defining vowel instances on plot panel
	## for speed reasons, this class does not inheret from any wx object (ie. staticbitmap)
	## click events are handled in the plotpanel
	def __init__(self,parent, lineInFile, cmuType, formants, word, stress, 
					timeRange, timePoint, maxFormant,
					index, wav, infoFile, pronunciation = None, durationAlternates = [], maxFormantAlternates = [], 
					otherType = '', pitch = None, alternate = False, original = None): 
		self.parent = parent
		self.line = lineInFile ## row in the file this vowel appears in (used to save changes back to the file later) 
		self.position = None
		self.show = False
		## define vowel values
		self.cmuType = cmuType
		self.f1 = formants[0]
		self.f2 = formants[1]
		self.word = word
		self.stress = stress
		self.min = timeRange[0]
		self.max = timeRange[1]
		self.duration = (self.max-self.min)
		self.timePoint = timePoint
		self.timePercentage = (self.timePoint-self.min)/self.duration
		self.pronunciation = pronunciation
		self.index = index
		self.wav = wav
		self.infoFile = infoFile
		self.environment = (pronunciation[index-1] if index != 0 else '#') + ' v ' + (pronunciation[index+1] if index != len(pronunciation)-1 else '#') if pronunciation and index else '' 
		self.maxFormant = maxFormant
		self.pitch = pitch
		self.otherType = otherType.decode('utf8') if otherType else ''
		self.durationAlternateValues = durationAlternates
		self.maxFormantAlternateValues = maxFormantAlternates
		## Set bitmaps
		self.circleBitmap = self.parent.GetPreloadedBitmap(self.cmuType)
		self.currentBitmap = self.circleBitmap
		## remeasurement settings
		self.alternates = []
		self.original = original
		## add values to appropriate dicts and sets
		self.parent.AddVowelValues(self, self.f1, self.f2, self.word, self.duration, self.cmuType, self.otherType)

	def __str__(self):
		## used for displaying all relevant vowel info
		otherLabel = self.parent.GetTopLevelParent().GetOtherLabel()
		return  'CMU\t'+ self.cmuType +'\n'+\
				(otherLabel+'\t' if otherLabel else 'OTHER\t')+ self.otherType +'\n'+\
				'F1\t' + str(self.f1) +'\n'+\
				'F2\t' + str(self.f2) +'\n'+\
				'STRESS\t' + str(self.stress)+'\n'+\
				'DURATION\t'+ str(int(self.duration*1000))+'\n'+\
				'WORD\t'+ self.word+'\n'+\
				'TIME\t'+ str(self.timePoint)+'\n'+\
				'ENVIRONMENT\t'+ self.environment+'\n'+\
				'MAX FORMANTS\t'+ str(self.maxFormant)

	def Play(self):
		## plays corresponding wav file in self.timerange
		## read chunk from wav file corresponding to the vowel
		wav = wave.open(self.wav)
		frameRate = wav.getframerate()
		nChannels = wav.getnchannels()
		sampWidth = wav.getsampwidth()
		start = int(self.min*frameRate)
		end = int(self.max*frameRate)
		wav.setpos(start)
		wavChunk = wav.readframes(end-start)
		wav.close()
		## create temporary wav file containing the vowel sound
		tempWav = wave.open('temp.wav', 'w')
		tempWav.setnchannels(nChannels)
		tempWav.setsampwidth(sampWidth)
		tempWav.setframerate(frameRate)
		tempWav.writeframes(wavChunk)
		tempWav.close()
		## play the new wav file then remove it 
		sound = wx.Sound('temp.wav')
		sound.Play()
		subprocess.call(['rm','temp.wav'])
		## This does the same thing as above but requires SoX to run 
		# subprocess.call(['play',self.wav,'trim', str(self.min), '='+str(self.max)]) 

	def MakeAlternate(self, altValues, altType):  
		## creates alternate vowel buttons when remeasuring 
		## usually then sent to self.alternates
		## altValues = (timePercentage OR maxFormant OR timePoint, (alternateF1, alternateF2))
		## altType = ('d' OR 'm') ... duration or maxformant
		alternates = []
		for a in altValues:
			alt = VowelButton(	parent = self.parent,
								lineInFile = self.line,
								cmuType = self.cmuType,
								formants = a[1],
								word = self.word,
								stress = self.stress,
								timeRange = (self.min, self.max),
								timePoint = a[0]*self.duration+self.min if altType == 'd' else self.timePoint if altType == 'm' else a[0],
								pronunciation = self.pronunciation,
								maxFormant = a[0] if altType == 'm' else self.maxFormant,
								index = self.index,
								wav = self.wav,
								infoFile = self.infoFile,
								durationAlternates = [d for d in self.durationAlternateValues + [(self.timePercentage, (self.f1,self.f2))] \
														if a != d] if altType == 'd' else self.durationAlternateValues,
								maxFormantAlternates = [m for m in self.maxFormantAlternateValues + [(self.maxFormant, (self.f1,self.f2))] if a != m] \
														if altType == 'm' else self.maxFormantAlternateValues,
								otherType = self.otherType,
								pitch = self.pitch,
								alternate = True,
								original = self) 
			alternates.append(alt)
		return alternates

	def GetAdjustedBitmapPosition(self):
		## Adjusts the bitmap so it is displayed with self.position at the centre
		## used to draw it to the panel in the right place
		x,y = self.position
		return (x-5,y-5)

	def Hide(self):
		## set show setting to false
		try: 
			self.parent.visibleVowels.remove(self)
		except:
			pass

	def Show(self):
		## set show setting
		self.parent.visibleVowels.add(self)

	def SetBitmap(self, bm):
		## set current bitmap value
		self.currentBitmap = bm

	def PlaceBitmap(self):
		## places the vowels on the plot or hides them if they are out of range
		f1Min, f1Max, f2Min, f2Max = self.parent.maxmins
		## if in range of maxmin formants or if the vowel is an alternate (has a self.original value)
		## to be displayed properly all vowels must have a position (alternate values receive position here after they are created)
		if self.original or f1Max >= self.f1 >= f1Min and f2Max >= self.f2 >= f2Min:
			plotWidth, plotHeight = self.parent.GetAdjustedSize()
			x = plotWidth - int(plotWidth * (float(self.f2-f2Min)/(f2Max-f2Min)))
			y = int(plotHeight * (float(self.f1-f1Min)/(f1Max-f1Min)))
			## set position
			self.position = (x,y)
			## add position to positions dict and positionKeys set
			try:
				self.parent.positions[self.position].append(self)
			except:
				self.parent.positionKeys.add(self.position)
				self.parent.positions[self.position] = []
				self.parent.positions[self.position].append(self)
			
			## now hide alternate vowels that are off the plot (now that they have received a position value)
			if self.original and (f1Max >= self.f1 >= f1Min or f2Max >= self.f2 >= f2Min):
				self.Hide()
		else:
			self.Hide()



	def OnRemeasure(self):
		## when clicking a vowel point (when not removing vowels)
		if self.parent.remeasureOptions: # if selecting a remeasurement for a vowel
			if self in self.parent.remeasureOptions: 
				self.TheChosenOne()
		else: # if selecting a vowel to remeasure
			if self.parent.GetRemeasurePermissions():
				self.parent.GetTopLevelParent().toolBarPanel.cancelButton.button.Enable() 
				remeasureMode = self.parent.GetTopLevelParent().toolBarPanel.reMeasureButton.GetMode()
				# create remeasurements or open praat and wait
				self.SetBitmap(self.parent.GetPreloadedBitmap('org'))
				if remeasureMode == 'F':
					self.alternates = self.MakeAlternate(self.maxFormantAlternateValues, 'm')
				elif remeasureMode == 'D':
					self.alternates = self.MakeAlternate(self.durationAlternateValues, 'd')
				else:
					self.parent.vowelInFocus = self
					self.parent.SetRemeasurePermissions(False)
					self.MakePraatAlternates()
					return None
				self.parent.remeasureOptions.append(self)
				# change bitmaps of all relevant vowels
				for a in self.alternates:
					a.SetBitmap(self.parent.GetPreloadedBitmap('alt'))
					self.parent.remeasureOptions.append(a)
				self.parent.SetRemeasurePermissions(False)
				self.parent.vowelInFocus = self				
		## update the plotpanel
		self.parent.CalculateFormantMaxMins()
		self.parent.PlaceVowels()


	def ReadPraatAlternates(self):
		## Reads the new vowel values remeasured in Praat
		## called in order to display the alternate vowels from Praat
		## (this currently gets the pitch as well but currently it isn't really used
		## so it does nothing with the pitch value)
		with open('praatLog', 'r+') as pLog:
			alts = []
			for line in pLog:
				info = line.split('\t')
				alts.append( (float(info[0]), (int(info[1]), int(info[2])) ) )
			pLog.truncate(0)
			return alts

	def MakePraatAlternates(self):
		## opens praat to the vowel position
		## if the path to praat is bad it prompts the user to reset it 
		subprocess.call(['rm', 'praatLog'])
		try:
			subprocess.check_output(['open', self.parent.GetTopLevelParent().Praat])
			subprocess.check_output(['./sendpraat', '0', 'praat',
							 'execute \"'+join(os.getcwd(),'zoomIn.praat')+'\" \"' + \
							  self.wav + '\" \"'+join(os.getcwd(),'praatLog')+ '\" ' + \
							  str(self.timePoint) + ' 1 '+str(self.maxFormant)+'"'])
		except:
			if wx.MessageDialog(self.parent, 'Woah, that wasn\'t Praat...\nFind the real Praat?').ShowModal() == wx.ID_OK:
				self.parent.GetTopLevelParent().OnFindPraat(None)
			self.parent.GetTopLevelParent().toolBarPanel.cancelButton.OnClick(None)

	def TheChosenOne(self):
		## called when an alternate vowel is selected 
		## redraws the vowel at new location, logs the change, etc
		self.SetBitmap(self.circleBitmap)
		originalVowel = self.parent.remeasureOptions[0] #first vowel in the list is the original vowel
		if self is not originalVowel:
			# update relevant lists
			self.parent.allVowels.remove(originalVowel)
			self.parent.allVowels.add(self)
			#log the change and update undo button
			self.LogChange() 
			self.parent.GetTopLevelParent().past.append(('remeasure', originalVowel, self))
			self.parent.GetTopLevelParent().future = [] ## clear future list
			self.parent.GetTopLevelParent().toolBarPanel.undoRedoButtons.CheckState()
			# change bitmap back
			originalVowel.SetBitmap(originalVowel.circleBitmap)
			# remove original value so the vowel is not treated like an alternate
			self.original = None
		# hide remeasure options
		for rb in self.parent.remeasureOptions:
			if rb is not self: 
				self.parent.RemoveStoredVowelValues(rb, rb.f1, rb.f2, rb.word, rb.duration, rb.cmuType, rb.otherType, rb.position)
				rb.Hide()
			else:
				rb.Show()
		## reset to normal mode
		self.parent.remeasureOptions = []
		self.parent.vowelInFocus = None
		self.parent.SetRemeasurePermissions(True)
		self.parent.GetTopLevelParent().toolBarPanel.cancelButton.button.Disable()

	def GetFormants(self):
		## returns formant values for the vowel
		return (self.f1, self.f2)

	def RemoveVowel(self, click = False):
		## Hides the vowel on the plot and removes it from the relevant lists
		good, note = self.parent.GetTopLevelParent().toolBarPanel.removeButton.dialog.GetRemoveInfo()
		self.LogChange(good, note) # log the removal as a change
		self.parent.allVowels.remove(self)
		self.parent.RemoveStoredVowelValues(self, self.f1, self.f2, self.word, self.duration, self.cmuType, self.otherType, self.position)
		if click:  # if called by clicking the vowel point
			self.parent.CalculateFormantMaxMins()
			self.parent.PlaceVowels() ## switch with remove single vowel (redraws plot around vowel point only)
			self.parent.GetTopLevelParent().past.append(('remove', [self], None))
			self.parent.GetTopLevelParent().future = [] ## makes sure you can't redo something you've already modified
			self.parent.GetTopLevelParent().toolBarPanel.undoRedoButtons.CheckState()
		self.Hide()

	def LogChange(self, state = 'changed', note = ''):
		## Logs changes to a dict in plotpanel to save later
		## if state == True OR False, the vowel is marked as removed, not changed
		if state is not 'changed':
			state = 'removed_good' if state else 'removed_bad'  
		change = [self.line] + [str(wr) for wr in [self.timePoint, self.maxFormant ,self.f1, self.f2, state, note]]
		try: 
			self.parent.changes[self.infoFile] += [change]
		except:
			self.parent.changes[self.infoFile] = [change]

class RemoveFromPlotOptions(wx.Frame):
	## popup window that gives options when removing vowels from the plot
	def __init__(self, parent):
		wx.Frame.__init__(self, parent, style = wx.FRAME_FLOAT_ON_PARENT)
		## define sizers and controls
		sizer = wx.BoxSizer(wx.HORIZONTAL)
		vSizer = wx.BoxSizer(wx.VERTICAL)
		rmvText = wx.StaticText(self, label = 'Mark all removed vowels as...')
		self.goodButton = wx.RadioButton(self, label = 'good')
		self.goodButton.SetValue(True)
		self.badButton = wx.RadioButton(self, label = 'bad')
		noteText = wx.StaticText(self, label = 'Add note')
		self.noteOption = wx.TextCtrl(self, size = (200, wx.DefaultSize[1]))
		## arrange controls in the sizers
		sizer.AddSpacer(10)
		sizer.Add(vSizer)
		sizer.AddSpacer(10)
		vSizer.Add(rmvText)
		vSizer.AddSpacer(2)
		vSizer.Add(self.goodButton)
		vSizer.AddSpacer(2)
		vSizer.Add(self.badButton)
		vSizer.AddSpacer(2)
		vSizer.Add(noteText)
		vSizer.AddSpacer(2)
		vSizer.Add(self.noteOption)
		vSizer.AddSpacer(10)
		## set sizer for dialog box
		self.SetSizerAndFit(sizer)
		##Bind events
		self.Bind(wx.EVT_ACTIVATE, self.OnClose) 

	def OnClose(self, e):
		# hides the frame if it loses focus
		if not e.GetActive():
			self.Hide()

	def GetRemoveInfo(self):
		## returns info from dialog (used like GetValue())
		return (self.goodButton.GetValue(), self.noteOption.GetValue())

class FilterPanel(wx.Panel):
	## panel containing controls to filter vowels from the plot
	def __init__(self, parent):
		wx.Panel.__init__(self, parent)
		## define sizers
		sizer = wx.BoxSizer(wx.VERTICAL)
		minSizer = wx.BoxSizer(wx.HORIZONTAL)
		maxSizer = wx.BoxSizer(wx.HORIZONTAL)
		## define title and main button
		self.filterBit = wx.Bitmap('icons/control_buttons/filter.png')
		self.cancelBit = wx.Bitmap('icons/control_buttons/filter_on.png')
		self.button = wx.BitmapButton(self, bitmap = self.filterBit, size = (55,55))
		titleText = wx.StaticText(self, label = "FILTER", style = wx.ALIGN_CENTER)
		## define list of words in the plot
		self.words = []
		wordText = wx.StaticText(self, label = "By word...", style = wx.ALIGN_LEFT)
		self.wordBox = wx.ComboBox(self, value = ' ',  choices = self.words, style = wx.CB_DROPDOWN|wx.TE_PROCESS_ENTER)
		self.wordBox.SetValue('') ## hack to make sure default value is empty but curser starts in left-most position
		## define min and max duration input boxes
		durText = wx.StaticText(self, label = "By duration...", style = wx.ALIGN_LEFT)
		minText = wx.StaticText(self, label = "min:", style = wx.ALIGN_LEFT)
		maxText = wx.StaticText(self, label = "max:", style = wx.ALIGN_LEFT)
		self.minDurBox = wx.TextCtrl(self, value = '', style = wx.TE_PROCESS_ENTER|wx.TE_RICH, size = (40, wx.DefaultSize[1])) 
		self.maxDurBox = wx.TextCtrl(self, value = '', style = wx.TE_PROCESS_ENTER|wx.TE_RICH, size = (40, wx.DefaultSize[1])) 
		## arrange controls in sizer
		sizer.AddSpacer(7)
		sizer.Add(titleText, flag = wx.ALIGN_CENTER)
		sizer.Add(self.button, flag = wx.ALIGN_CENTER)
		sizer.Add(wordText)
		sizer.Add(self.wordBox)
		sizer.Add(durText)
		sizer.Add(minSizer)
		sizer.Add(maxSizer)
		minSizer.Add(minText)
		minSizer.AddSpacer(3)
		minSizer.Add(self.minDurBox, flag = wx.ALIGN_RIGHT)
		minSizer.Add(wx.StaticText(self, label = 'ms'))
		maxSizer.Add(maxText)
		maxSizer.Add(self.maxDurBox, flag = wx.ALIGN_RIGHT)
		maxSizer.Add(wx.StaticText(self, label = 'ms'))
		## display the panel
		self.SetSizer(sizer)
		self.Show(True)
		## bind events to class functions
		self.button.Bind(wx.EVT_BUTTON, self.OnPress)
		self.wordBox.Bind(wx.EVT_TEXT, self.OnType)
		self.wordBox.Bind(wx.EVT_TEXT_ENTER, self.OnEnter)
		self.minDurBox.Bind(wx.EVT_KILL_FOCUS, self.OnMin)
		self.maxDurBox.Bind(wx.EVT_KILL_FOCUS, self.OnMax)
		self.minDurBox.Bind(wx.EVT_TEXT_ENTER, self.OnMin)
		self.maxDurBox.Bind(wx.EVT_TEXT_ENTER, self.OnMax)

	def showVowelStats(self):
		## define list of words in the plot
		self.words = self.FindWords()
		self.wordBox.SetItems(self.words)
		## define min and max duration input boxes
		self.minDurBox.SetValue(self.GetTotalMinDur())
		self.maxDurBox.SetValue(self.GetTotalMaxDur())
		self.Refresh()

	def OnPress(self, e = None, enter = False):
		## call plotpanel.filterVowels() when button or return key is pressed 
		plotpanel = self.GetTopLevelParent().plotPanel
		if self.button.GetBitmapLabel() == self.filterBit or enter:
			## filter the vowels on the plot
			minDur = int(self.minDurBox.GetValue())
			maxDur = int(self.maxDurBox.GetValue())
			if minDur >= maxDur: ## only filters by word if the duration limits are weird
				self.minDurBox.SetBackgroundColour('red')
				self.maxDurBox.SetBackgroundColour('red')
				plotpanel.filterVowels(word = self.wordBox.GetValue())
			else: ## filter by word (if defined) and by duration 
				plotpanel.filterVowels(word = self.wordBox.GetValue(), minDur = minDur, maxDur = maxDur)
			self.button.SetBitmapLabel(self.cancelBit)
		else: ## undo filtering
			plotpanel.showAll()
			self.button.SetBitmapLabel(self.filterBit)
		self.Layout()

	def OnType(self, e):
		## show list of words when typing in the box
		self.wordBox.Popup()

	def OnEnter(self, e):
		## returns word value to default if the typed word isn't found in the plot
		if self.wordBox.GetValue() not in self.words:
			self.wordBox.SetValue('')
		else:
			self.OnPress(enter = True)
		self.wordBox.Dismiss() 

	def OnMin(self, e):
		## only integers allowed in minBox, also processes return key 
		self.minDurBox.SetBackgroundColour('white') # resets background in case previous values were weird
		self.maxDurBox.SetBackgroundColour('white')
		# if mindur is empty or less than 1: reset it to the minimum duration of all vowels on the plot
		try: 
			if int(self.minDurBox.GetValue()) < 1:
				self.minDurBox.SetValue(self.GetTotalMinDur())
		except:
			self.minDurBox.SetValue(self.GetTotalMinDur())
			return 
		# if enter is pressed: filter vowels
		if isinstance(e, wx.CommandEvent):
			self.OnPress(enter = True)

	def OnMax(self, e):
		## only integers allowed in maxBox, also processes return key
		self.minDurBox.SetBackgroundColour('white') # resets background in case previous values were weird
		self.maxDurBox.SetBackgroundColour('white')
		# if maxdur is empty or less than 1: reset it to the maximum duration of all vowels on the plot
		try: 
			if int(self.maxDurBox.GetValue()) < 1:
				self.maxDurBox.SetValue(self.GetTotalMaxDur())	
		except:
			self.maxDurBox.SetValue(self.GetTotalMaxDur())
			return 
		# if enter is pressed: filter vowels
		if isinstance(e, wx.CommandEvent):
			self.OnPress(enter = True)

	def GetTotalMinDur(self):
		## get min duration from all vowels on the plot
		try:
			return str(int(min(self.GetTopLevelParent().plotPanel.durations)*1000))
		except:
			return None

	def GetTotalMaxDur(self):
		## get max duration from all vowels on the plot
		try:
			return str(int(max(self.GetTopLevelParent().plotPanel.durations)*1000))
		except:
			return None

	def FindWords(self):
		## get list of all words from vowels on the plot
		return sorted(list(self.GetTopLevelParent().plotPanel.words))



class CmuButton(wx.BitmapButton):
	## button subclass representing all cmu vowels
	def __init__(self, parent, label):
		# load bitmaps from icons/plot_buttons
		self.onBitmap = wx.Bitmap('icons/plot_buttons/'+label+'/onButton.png')
		self.offBitmap = wx.Bitmap('icons/plot_buttons/'+label+'/offButton.png')
		#init button
		wx.BitmapButton.__init__(self, parent, bitmap = self.offBitmap, size = (35,25))
		self.label = label
		self.value = False
		# bind events
		self.Bind(wx.EVT_BUTTON, self.OnPress)

	def OnPress(self, e):
		## update list of vowels shown on plotpanel when pressed
		plotpanel = self.GetTopLevelParent().plotPanel
		if self.value:
			self.SetBitmapLabel(self.offBitmap)
			self.value = False
			plotpanel.RemoveCmu(self.label)
		else:
			self.SetBitmapLabel(self.onBitmap)
			self.value = True
			plotpanel.AddCmu(self.label)
		plotpanel.Refresh()		

	def SetValue(self, value):
		## allows the master button to toggle the button
		self.value = not value
		self.OnPress(None)

	def GetValue(self):
		## returns current button value
		return self.value

class OtherButton(wx.BitmapButton):
	## button subclass representing all other (alternate phonetic alphabet) vowels
	def __init__(self, parent, label):
		# load bitmaps (draws labels onto generic backgrounds)
		self.onBitmap = DrawCaptionOntoBitmap('icons/other_background.png', label)
		self.offBitmap = DrawCaptionOntoBitmap(None, label)
		# init button
		wx.BitmapButton.__init__(self, parent, bitmap = self.offBitmap, size = (35,25))
		self.label = label
		self.value = False
		# bind events
		self.Bind(wx.EVT_BUTTON, self.OnPress)

	def OnPress(self, e):
		## update list of vowels shown on plotpanel when pressed
		plotpanel = self.GetTopLevelParent().plotPanel
		if self.value:
			self.SetBitmapLabel(self.offBitmap)
			self.value = False
			plotpanel.RemoveOther(self.label)
		else:
			self.SetBitmapLabel(self.onBitmap)
			self.value = True
			plotpanel.AddOther(self.label)
		plotpanel.Refresh()			

	def SetValue(self, value):
		## allows the master button to toggle the button
		self.value = not value
		self.OnPress(None)

	def GetValue(self):
		## returns current button value
		return self.value

class UButton(wx.BitmapButton):
	## pseudo togglebutton that displays either the union or intersect of 
	## the selected cmu and other vowels 
	def __init__(self, parent):
		## load bitmaps
		self.unionBit = wx.Bitmap('icons/control_buttons/union.png')
		self.intersectBit = wx.Bitmap('icons/control_buttons/intersect.png')
		# init button
		wx.BitmapButton.__init__(self, parent = parent, bitmap = self.unionBit)
		self.value = True
		self.parent = parent
		# bind events
		self.Bind(wx.EVT_BUTTON, self.OnPress)

	def OnPress(self, e):
		# toggles the bitmap and sets the value when pressed
		if self.GetBitmapLabel() == self.unionBit:
			self.SetBitmapLabel(self.intersectBit)
			self.value = False
		else:
			self.SetBitmapLabel(self.unionBit)
			self.value = True
		# updates plotpanel and button appearance
		self.parent.Layout()
		self.GetTopLevelParent().plotPanel.OnUnionButtonPress()
		self.GetTopLevelParent().plotPanel.Refresh()

	def GetValue(self):
		## returns current value
		return self.value

class masterButton(wx.ToggleButton):
	## togglebutton subclass that controls the toggle state of other toggle buttons (its "minions") 
	def __init__(self, parent, label):
		wx.ToggleButton.__init__(self, parent = parent, label = label, size = (92, 30))
		self.minions = []
		# bind events
		self.Bind(wx.EVT_TOGGLEBUTTON, self.OnMasterToggle)

	def OnMasterToggle(self, e):
		## toggles all buttons below it (minion buttons)
		for m in self.minions:
			m.SetValue(self.GetValue())

	def AddMinion(self, minionButton):
		## add a minion (togglebuttons accepted only)
		self.minions.append(minionButton)

class VowelInfo(wx.Frame):
	## popup window that displays vowel info on right click
	def __init__(self, parent):
		wx.Frame.__init__(self, parent, style = wx.FRAME_FLOAT_ON_PARENT)

		self.SetBackgroundColour('wheat')

		self.sizer = wx.BoxSizer(wx.VERTICAL)

		horSizer = wx.BoxSizer(wx.HORIZONTAL)
		horSizer.AddSpacer(10)
		horSizer.Add(self.sizer)
		horSizer.AddSpacer(10)

		self.SetSizer(horSizer)

		self.Hide()

		self.Bind(wx.EVT_ACTIVATE, self.OnClose)

	def OnClose(self, e):
		# hides the frame if it loses focus
		if not e.GetActive():
			self.Hide()

	def UpdateMessage(self, message):
		self.sizer.Clear(True)

		self.sizer.AddSpacer(10)
		for m in message.split('\n'):
			self.sizer.Add(wx.StaticText(self, label = m))
		self.sizer.AddSpacer(10)

		self.Fit()
		self.Show()

class PlotPanel(wx.Panel):
	## panel containing all plotted vowels
	def __init__(self, parent):
		## init panel and values
		wx.Panel.__init__(self, parent = parent, style=wx.SUNKEN_BORDER)
		# f1/f2 max mins
		self.f1s = {} ## dictionary of {f1 : int} where int == the number of vowels on the plot with that f1 value
		self.f2s = {} ## dictionary of {f2 : int} where int == the number of vowels on the plot with that f2 value
		self.maxmins = () # (minF1, maxF1, minF2, maxF2) of all vowels on the plot
		self.words = {} ## dictionary of {word : int} where int == the number of vowels on the plot in that word
		self.durations = {} ## dictionary of {dur : int} where int == the number of vowels on the plot with that duration value
		self.cmus = {} ## dictionary of {cmuLabel: [vowels]} where vowels are all vowels with that cmuType
		self.others = {} ## dictionary of {otherLabel: [vowels]} where vowels are all vowels with that otherType
		self.positions = {} ## dictionary of {(x,y):[vowels]} where (x,y) are the coordinates on the plot and vowels are all vowels with those coordinates
		self.positionKeys = set() ## keeps track of all positions of vowels in allVowels for quick retrieval when more than 121 vowels are visible
		self.visibleVowels = set() ## set of all visible vowels on the plot
		self.allVowels = set() # all vowels
		self.cmuLabels = [] # vowels with a cmu value in this list will be shown
		self.otherLabels = [] # vowels with an other value in this list will be shown
		self.remeasureOptions = [] # contains vowel instances of remeasured vowels
		self.allowRemeasurements = True 
		self.vowelInFocus = None # vowel currently being remeasured
		self.zoomCoords = [] # coordinates of beginning of zoombox/remove vowel box
		self.zooming = False # if true: panel is waiting to zoom 
		self.removing = False # if true: waiting to remove vowels
		self.drawing = False # if true: currently drawing a box on the overlay
		self.changes = {} # stores all changes to vowels (saving reads from here)
		self.overlay = wx.Overlay() # draws zoombox to this overlay
		self.filteredWord = '' # stores word when filtering
		self.filteredDurs = () # stores min/max durations when filtering
		## create vowel bitmaps from files to be used for vowel points on the plot
		self.BuildVowelBitmaps()
		## draw labels
		width, height = self.GetAdjustedSize()
		self.f1Label = wx.StaticText(self, label = 'F1', pos = (width/2 , 0) )
		self.f1Label.SetForegroundColour('GREY')
		self.f2Label = wx.StaticText(self, label = 'F2', pos = (width, height/2) )
		self.f2Label.SetForegroundColour('GREY')
		self.f1MinLabel = wx.StaticText(self)
		self.f1MinLabel.SetForegroundColour('GREY')
		self.f1MaxLabel = wx.StaticText(self)
		self.f1MaxLabel.SetForegroundColour('GREY')
		self.f2MinLabel = wx.StaticText(self)
		self.f2MinLabel.SetForegroundColour('GREY')
		self.f2MaxLabel = wx.StaticText(self)
		self.f2MaxLabel.SetForegroundColour('GREY')
		# bind events
		self.Bind(wx.EVT_SIZE, self.OnResize)
		self.GetTopLevelParent().Bind(wx.EVT_ACTIVATE, self.ShowPraatMeasurements) # when frame is reactivated, show remeasured praat vowels 
		self.Bind(wx.EVT_LEFT_UP, self.OnLeftClick)
		self.Bind(wx.EVT_RIGHT_UP, self.OnRightClick)
		self.Bind(wx.EVT_PAINT, self.OnPaint)
		self.Bind(wx.EVT_LEFT_DOWN, self.StartZoomBox)
		self.Bind(wx.EVT_MOTION, self.DrawZoomBox)

		# init vowel info panel
		self.vowelInfoPanel = VowelInfo(self)

	def OnPaint(self, e):
		dc = wx.PaintDC(self)
		dc.Clear()
		for b in self.visibleVowels:
			if (self.filteredWord and b.word != self.filteredWord) or (self.filteredDurs and not (self.filteredDurs[0] <= int(b.duration*1000) <= self.filteredDurs[1])):
				continue
			dc.DrawBitmapPoint(b.currentBitmap, b.GetAdjustedBitmapPosition())
		for b in self.remeasureOptions:
			dc.DrawBitmapPoint(b.currentBitmap, b.GetAdjustedBitmapPosition())


	def OnLeftClick(self, e):
		pos = e.GetPosition()
		## if removing vowels from the plot
		try:
			if self.removing: ## give removing priority over zooming if both are on
				if self.drawing: 
					self.RemoveInBox(pos)
				else:
					self.GetVowelsInClickRange(pos).RemoveVowel(True) 
			elif self.zooming:
				self.DoTheZoom(pos) ## Note that if this fails (ie. actual click instead of end of drawing a box) self.NormalClick will be called
			## if playing or remeasuring vowels
			else:
				self.NormalClick(pos)
		except:
			return


	def OnRightClick(self, e):
		pos = e.GetPosition()
		self.vowelInfoPanel.SetPosition(self.ClientToScreen(pos))
		vowel = self.GetVowelsInClickRange(pos)[0]
		if vowel: self.vowelInfoPanel.UpdateMessage(str(vowel))

	def NormalClick(self, pos):
		## processes a normal click on the plot (not a click and drag)
		clicked = self.GetVowelsInClickRange(pos)[0]
		## if remeasuring and clicked is not a remeasure option
		## Note: this would throw an error later anyway (if the if statement wasn't there) which would be handled in OnLeftClick but it's clearer if I prevent it here
		if self.remeasureOptions and clicked not in self.remeasureOptions:
			print 'here'
			return
		## play if play mode is on 
		if self.GetTopLevelParent().toolBarPanel.playButton.GetPlayState(): 
			clicked.Play()
		## otherwise process remeasurement
		else:
			clicked.OnRemeasure()


	def GetVowelsInClickRange(self, p):
		## gets all vowels within 5 pixels of the point (p) in any direction
		## used to figure out which vowel is clicked on the plot
		xyGrid = {(x,y) for x in range(p[0]-5,p[0]+6) for y in range(p[1]-5,p[1]+6)}
		vowels = [ v for i in xyGrid&self.positionKeys for v in self.positions[i]]
		return [v for v in vowels if v in self.visibleVowels]

	def SetRemeasurePermissions(self, value):
		## sets permission to remeasure vowels on the plot
		self.allowRemeasurements = value

	def GetRemeasurePermissions(self):
		#returns remeasurement permission
		return bool(self.allowRemeasurements)

	def filterVowels(self, word = None, minDur = None, maxDur = None):
		## filter all vowels from the plot by word or duration range
		self.filteredWord = word.upper()
		self.filteredDurs = (minDur,maxDur) if minDur and maxDur else ()
		self.Refresh()

	def showAll(self):
		## remove all filtering and show all vowels
		self.filteredWord = ''
		self.filteredDurs = ()
		self.Refresh()

	def GetAdjustedSize(self):
		## gives slightly smaller plot size in order to place vowels nicely (ie. not right on the edge)
		width, height = self.GetSize()
		return (width-20, height-20)

	def DrawAxisLabels(self):
		## Redraws axis labels (used when resizing)
		width, height = self.GetAdjustedSize()
		self.f1Label.SetPosition((width , height/2))
		self.f2Label.SetPosition((width/2 , 0))
		self.f2MaxLabel.SetPosition((0,0))
		self.f2MinLabel.SetPosition((width-30, 0))
		self.f1MinLabel.SetPosition((width-20,13))
		self.f1MaxLabel.SetPosition((width-20, height))
		self.f1MinLabel.SetLabel(str(self.maxmins[0]) if self.maxmins else '')
		self.f1MaxLabel.SetLabel(str(self.maxmins[1]) if self.maxmins else '')
		self.f2MinLabel.SetLabel(str(self.maxmins[2]) if self.maxmins else '')
		self.f2MaxLabel.SetLabel(str(self.maxmins[3]) if self.maxmins else '')

	def BuildVowelBitmaps(self):
		## creates vowel bitmaps from icon files on startup 
		self.bitmapDict = {basename(dirname(i)): wx.Bitmap(i) for i in glob.glob('icons/plot_buttons/*/circle.png')}
		self.bitmapDict.update({'alt' : wx.Bitmap('icons/plot_buttons/alternate.png'), 'org' : wx.Bitmap('icons/plot_buttons/original.png')})
	
	def GetPreloadedBitmap(self, key):
		## gets the bitmap loaded on startup for a given vowel
		## key = cmuType or otherType (ex: 'AH', 'i', etc.)
		return self.bitmapDict[key]


	###--------------------------------###
	## functions for zooming in and out 
	###--------------------------------###

	
	def RemoveInBox(self, mousePosition):
		## removes vowels which fall into drawn box
		# get all vowels in the drawn box
		currentCoords = mousePosition
		x, x2 = sorted([int(self.zoomCoords.x), int(currentCoords.x)])
		y, y2 = sorted([int(self.zoomCoords.y), int(currentCoords.y)]) 
		removeVowels = self.GetVowelsInBox((x,y), (x2,y2))
		# if there are no vowels in the box, return to normal
		if not removeVowels: 
			if self.HasCapture(): self.ReleaseMouse()
			self.clearOverlay()
			return
		# update redo/undo lists
		self.GetTopLevelParent().past.append(('remove', removeVowels, None))
		self.GetTopLevelParent().future = [] ## clear redo list
		self.GetTopLevelParent().toolBarPanel.undoRedoButtons.CheckState()
		# Hide all remeasure options if the original is in the box
		if self.remeasureOptions and self.remeasureOptions[0].original in removeVowels:
			for v in self.remeasureOptions:
				v.RemoveVowel()
		# remove all vowels in the box
		for v in removeVowels:
			if v not in self.remeasureOptions[1:]: ## don't remove alternates if the original vowel is still there (see previous for loop)
				v.RemoveVowel()
		# reset overlay and redraw the panel
		if self.HasCapture(): self.ReleaseMouse()
		self.clearOverlay()
		self.zoomCoords = []
		self.CalculateFormantMaxMins()
		self.PlaceVowels()
		self.drawing = False
		self.Refresh()

	def ZoomIn(self):
		## allow zooming 
		if self.allVowels:
			self.zooming = True

	def ResetZoom(self):
		## reset zoom to full plot
		if self.zooming:
			self.zooming = False
			self.CalculateFormantMaxMins()
			self.PlaceVowels()
			self.OnUnionButtonPress() ## redraws all vowels
			self.Refresh()

	def doubleClickZoom(self, pos):
		# if zooming and a spot is double clicked
		# zoom into that spot by a fixed amount
		currentCoords = pos
		x,y = currentCoords[0]-50 , currentCoords[1]-50
		x2,y2, = currentCoords[0]+50 , currentCoords[1]+50 
		self.CalculateFormantMaxMins(self.GetVowelsInBox((x,y), (x2,y2)))
		self.PlaceVowels()
		self.zoomCoords = []


	def drawBox(self, rect):
		## draws a box on a dc object and then to the overlay
		dc = wx.ClientDC(self)
		odc = wx.DCOverlay(self.overlay, dc)
		odc.Clear()
		dc.SetPen(wx.Pen('Black', 1))
		dc.SetBrush(wx.Brush(wx.Colour(0, 0, 0), wx.TRANSPARENT))
		dc.DrawRectangleRect(rect)
		del odc

	def clearOverlay(self):
		# clears overlay when finished drawing the box
		dc = wx.ClientDC(self)
		odc = wx.DCOverlay(self.overlay, dc)
		odc.Clear()
		del odc
		self.overlay.Reset()

	def DrawZoomBox(self, e):
		# draw a box when dragging and zooming (or removing vowels)
		if self.zoomCoords and e.Dragging() and e.LeftIsDown():
			self.drawing = True	
			self.currentCoords = e.GetPosition()
			rect = wx.RectPP(self.zoomCoords, self.currentCoords)
			self.drawBox(rect)

	def StartZoomBox(self, e):
		# captures mouse position when starting a zoombox
		if self.zooming or self.removing:
			e.GetPosition()
			self.zoomCoords = e.GetPosition()

	def DoTheZoom(self, pos):
		## zoom in to area defined by the zoom box
		# define new bounds of plot based on max/min f1/f2 values defined in the box
		currentCoords = pos
		x, x2 = sorted([int(self.zoomCoords.x), int(currentCoords.x)])
		y, y2 = sorted([int(self.zoomCoords.y), int(currentCoords.y)]) 
		vowels = self.GetVowelsInBox((x,y), (x2,y2))
		if not vowels:
			self.clearOverlay()
			self.drawing = False
			self.NormalClick(pos)
			return
		self.CalculateFormantMaxMins(vowels)
		self.PlaceVowels()
		# clear zoom box and redraw buttons
		if self.HasCapture(): self.ReleaseMouse()
		self.clearOverlay()
		self.PlaceVowels()
		self.zoomCoords = []
		self.drawing = False
		# redraw zoombutton bitmap
		self.GetTopLevelParent().toolBarPanel.zoomButton.button.SetBitmapLabel(self.GetTopLevelParent().toolBarPanel.zoomButton.zoomoutBM)

	def GetVowelsInBox(self, topLeftPoint, bottomRightPoint):
		## get all vowels that fall inside a drawn box:
		# takes two point arguments that define the top-left and bottom-right of the box
		zoomedVisibleVowels = set()
		for b in self.visibleVowels:
			x,y = b.position
			if bottomRightPoint[0] >= x >= topLeftPoint[0] and bottomRightPoint[1] >= y >= topLeftPoint[1]:
				zoomedVisibleVowels.add(b)
		for b in self.remeasureOptions:
			x,y = b.position
			if bottomRightPoint[0] >= x >= topLeftPoint[0] and bottomRightPoint[1] >= y >= topLeftPoint[1]:
				zoomedVisibleVowels.add(b)
		return zoomedVisibleVowels


	def DrawConfidenceEllipse(self, sdev = None):
		# make a confidence ellipse of the points currently plotted on the screen
		# mathy bits adapted from Jaime at: 
		#stackoverflow.com/questions/20126061/creating-a-confidence-ellipses-in-a-sccatterplot-using-matplotlib
		x = []
		y = []
		xy = []
		# find all vowels to consider when drawing the plot
		for b in self.visibleVowels:
			pos = b.position
			x.append(pos[0])
			y.append(pos[1])
			xy.append(pos)
		xy.sort()
		## mathy things that define the ellipse (thanks Jaime)
		angleAdjust = sum([p[1] for p in xy[:len(xy)/2]])/(len(xy)/2) < sum([p[1] for p in xy[len(xy)/2:]])/(len(xy)) 
		mean = (np.mean(x) , np.mean(y))
		cov = np.cov(x, y)
		lambda_, v = np.linalg.eig(cov)
		lambda_ = np.sqrt(lambda_)
		angle = np.arccos(v[0,0])
		width=lambda_[0]*sdev*2
		height=lambda_[1]*sdev*2
		# draw ellipse first as a bitmap
		ellipBMap = wx.EmptyBitmap(width+4, height+4)
		dc = wx.MemoryDC(ellipBMap)
		dc.SetPen(wx.Pen('Black', 2))
		dc.SetBrush(wx.Brush(wx.Colour(0, 0, 0), wx.TRANSPARENT))
		dc.DrawEllipse(2 , 2 , width , height)
		ellipImg = ellipBMap.ConvertToImage()
		# rotate the ellipse
		ellipImg = ellipImg.Rotate(angle, ((width+4)/2, (height+4)/2))
		if angleAdjust: ellipImg = ellipImg.Mirror(False)
		# clear dc and overlay
		dc.SelectObject( wx.NullBitmap )
		dc = wx.ClientDC(self)
		odc = wx.DCOverlay(self.overlay, dc)
		odc.Clear()
		# draw ellipse to the plot (given the centre point)
		imgWidth, imgHeight = ellipImg.GetSize()
		dc.DrawBitmapPoint(ellipImg.ConvertToBitmap(), (mean[0] - imgWidth/2 , mean[1] - imgHeight/2))
		del odc

	###--------------------------------###
	## functions for reading vowel information on startup
	###--------------------------------###
	
	def GetHeadingLocations(self, headingList, configDict):
		## creates dictionary of headings:column in info file 
		## used to find vowel values 
		locationDict = {}
		delimiter = self.GetTopLevelParent().fileDelim
		for i,head in enumerate(headingList.split(delimiter)):
			head = head.strip()
			if head in configDict and head:
				cat = configDict[head]
				if isinstance(cat, tuple):
					i = (i, cat[1])
					cat = cat[0]
				try: locationDict[cat] += [i]
				except: locationDict[cat] = [i]
		locationDict = {k : v[0] if len(v)==1 else v for k,v in locationDict.iteritems()}
		return locationDict

	def DecodeAlternates(self, row, locations, altType):
		## gets the alternate f1 and f2 values
		## returns (alternate setting, (f1,f2)) ex. an alternate setting might be 20 for formants measured
		## at 20% of the vowel duration...
		alternates = []
		for l in locations:
			alt = self.OptionalArgHandler(row,l[0])
			if re.sub('[ ,]','',alt):
				alternates.append((alt, l[1]))
		alts = [(int(i[1])/100.0 if altType == 'd' else int(i[1]), tuple(int(float(j)) for j in i[0].split(',')) ) for i in alternates]
		return alts

	def CalculateFormantMaxMins(self, vowelSet = None):
		## calculate formant max and min for all vowels
		## not just visible ones (use at startup and when deleting vowels)
		if not vowelSet: 
			if self.zooming: return
			try:
				self.maxmins = (min(self.f1s)-10, max(self.f1s)+10, min(self.f2s)-10, max(self.f2s)+10)
				if self.remeasureOptions:
					f1s, f2s = [], []
					for v in self.remeasureOptions:
						f1,f2 = v.GetFormants()
						f1s.append(f1)
						f2s.append(f2) 
					
					self.maxmins = ( min( min(f1s) - 10, self.maxmins[0]), max(max(f1s) + 10, self.maxmins[1]) , min(min(f2s) - 10, self.maxmins[2]) , max(max(f2s) + 10, self.maxmins[3]) )
			except:
				return
		else:
			allF1 = [] 
			allF2 = []
			for b in vowelSet:
				try:
					f1,f2 = b.GetFormants()
					allF1.append(f1)
					allF2.append(f2)
				except:
					print >> sys.stderr, 'no formants found in vowel:\n\n'+str(b)
			self.maxmins = (min(allF1)-10, max(allF1)+10, min(allF2)-10, max(allF2)+10)
		self.GetTopLevelParent().phonPanel.filterPanel.showVowelStats()

	def OnResize(self, e):
		## handler when resizing the frame
		# self.plotBM = wx.EmptyBitmap(*self.GetSize())
		# self.dc = wx.MemoryDC(self.plotBM)
		self.PlaceVowels()
		self.Refresh()

	def PlaceVowels(self):
		## places vowels on the plot according to there relative distance from formant mins/maxs
		self.DrawAxisLabels()
		self.positions = {}
		self.positionKeys = set()
		for b in self.allVowels:
			b.PlaceBitmap()
		for b in self.remeasureOptions[1:]: ## skips first vowel instance since it is the original vowel and already placed above 
			## this looks redundant (see for loop above) but it is faster to do them seperately since allVowels+remeasureOptions makes a new list
			b.PlaceBitmap()
		self.Refresh()

		## hides stdDev ellipse when remeasuring
		self.clearOverlay()
		sdButton = self.GetTopLevelParent().toolBarPanel.stdDevButtons
		if sdButton.IsOn():
			sdButton.OnClick(None)
		self.Refresh()


	def CreateVowelsFromFiles(self, files):
		## creates vowels from file pairs (wav,txt OR csv)
		## start progress bar
		progress = 0
		progressBar = wx.ProgressDialog("Loading Files...", "", len(files), style=wx.PD_CAN_ABORT | wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME)
		progressBar.SetSize((700,300))
		## get config file settings from the mainframe in order to read the files
		configDict = self.GetTopLevelParent().configDict
		delimiter = self.GetTopLevelParent().fileDelim
		headingRow = self.GetTopLevelParent().fileHRow
		## set up error holder
		errorDict = {}
		# initiate sort lists
		cmus = {}
		others = {}
		## interate through file pairs
		for wavFile , infoFile in files:
			## update progress bar
			progressBar.Update(progress, infoFile)
			progress += 1
			with open(infoFile, 'r') as info: #read file
				for n,i in enumerate(info): # iterate through lines
					if n < headingRow: # do nothing for lines above heading row
						continue
					elif n == headingRow: 
						headingCol = self.GetHeadingLocations(i, configDict) # get column index for each heading
						self.GetTopLevelParent().toolBarPanel.saveButton.columnIndexes[infoFile] = [headingCol['TIME'], headingCol['MAXFORMANT'], headingCol['F1'], headingCol['F2']] # set relevant column headings for saving later
					else: # get vowel info
						try:
							if i.strip(): # makes sure line isn't empty
								# try:
								i = i.strip().split(delimiter) ## split the row into a list
								## make a new button instance according to stuff in the row 
								## (note some settings are optional)
								f1 = int(float(i[headingCol['F1']]))
								f2 = int(float(i[headingCol['F2']]))
								word = i[headingCol['WORD']]
								cmu = i[headingCol['CMU']][:2]
								other = self.OptionalArgHandler(i,headingCol['OTHER']) if 'OTHER' in headingCol else None
								start, stop = float(i[headingCol['START']]) , float(i[headingCol['END']]) 
								# make button instance
								button = VowelButton(	parent = self,
														lineInFile = n,
														cmuType = cmu,
														formants = ( f1 , f2 ),
														word = word,
														stress = i[headingCol['STRESS']],
														timeRange = (start,stop),
														timePoint = float(i[headingCol['TIME']]),
														pronunciation = re.sub("[\[\]\'\ ]", '', i[headingCol['PRONUNCIATION']]).split(',') if 'PITCH' in headingCol else None,
														maxFormant = int(i[headingCol['MAXFORMANT']]),
														index = int(i[headingCol['INDEX']]) if 'INDEX' in headingCol else None,
														wav = wavFile, 
														infoFile = infoFile,
														durationAlternates = self.DecodeAlternates(i, headingCol['DURATION_ALTERNATES'], 'd') if 'DURATION_ALTERNATES' in headingCol else [] ,
														maxFormantAlternates = self.DecodeAlternates(i, headingCol['MAXFORMANT_ALTERNATES'], 'm') if 'MAXFORMANT_ALTERNATES' in headingCol else [],
														otherType = other,
														pitch = self.OptionalArgHandler(i,headingCol['PITCH'], int) if 'PITCH' in headingCol else None)	
								## add the button instance to the appropriate lists
								self.allVowels.add(button)
						except:
							try: errorDict[basename(infoFile)] += [n]
							except: errorDict[basename(infoFile)] = [n]
		## display warning message if a line wasn't processed
		if errorDict:
			message = 'Unable to parse the following vowel instances\n'+'\n'.join(['In file '+str(k)+': rows '+', '.join([str(v) for v in values]) for k,values in errorDict.items()])+'\n\nPlease check the files or reconfigure the info reader\n(File > Configure Info Reader)'
			wx.MessageDialog(self, message).ShowModal()
		# show vowels on the plot
		self.CalculateFormantMaxMins() 
		self.PlaceVowels()
		self.OnUnionButtonPress() ## shows vowels on the plot if buttons have already been pressed
		progressBar.Destroy() # close progress bar

	def RemoveStoredVowelValues(self, vowel, f1, f2, word, duration, cmu, other, position):
		## removes information about vowels from the appropriate dicts and sets
		## this should be done in conjunction with removing a vowel from allVowels and
		## is called from self.RemoveVowel()
		## Note that if the value in a dict is less than 0, the key will be removed
		if self.f1s[f1] > 1: self.f1s[f1] -= 1
		else: del self.f1s[f1]  

		if self.f2s[f2] > 1: self.f2s[f2]  -= 1
		else: del self.f2s[f2]

		if self.words[word] > 1: self.words[word] -= 1
		else: del self.words[word]

		if self.durations[duration] > 1: self.durations[duration] -= 1
		else: del self.durations[duration]

		self.cmus[cmu].remove(vowel)
		try: ## if otherType is not ''
			self.others[other].remove(vowel)
		except:
			pass
		
		if len(self.positions[position]) > 1: 
			self.positions[position].remove(vowel)
		else: 
			del self.positions[position]
			self.positionKeys.remove(position) 

	def AddVowelValues(self, vowel, f1, f2, word, duration, cmu, other):
		## adds information about vowels from the appropriate dicts and sets
		## this should be done when making a new instance of this class AND when 
		## adding a value back into PlotPanel.allVowels
		## Note: this does not add to PlotPanel.positions dict (that is done when 
		## 		 the vowel is first placed using VowelButton.PlaceBitmap )
		try: self.f1s[f1] += 1 
		except: self.f1s[f1] = 1

		try: self.f2s[f2] += 1
		except:	self.f2s[f2] = 1

		try: self.words[word] += 1
		except:	self.words[word] = 1
		
		try: self.durations[duration] += 1
		except:	self.durations[duration] = 1
		
		self.cmus[cmu].add(vowel)
		try: ## if otherType is not ''
			self.others[other].add(vowel)
		except:
			pass

	def OptionalArgHandler(self, lineList, index, returnType = str):
		## allows some vowels to have empty info for certain settings
		try: return returnType(lineList[index])
		except: return None

	###--------------------------------###
	## the following functions deal with input from the phonPanel
	###--------------------------------###
		
	def AddCmu(self, cmu):
		## permits this cmu pronunciation to be displayed on the plot
		if cmu not in self.cmuLabels:
			self.cmuLabels.append(cmu)
		
		if self.GetUnionButtonState():
			for b in self.cmus[cmu]:
				b.Show()  
		else:
			for b in self.cmus[cmu]:
				if b.otherType in self.otherLabels:
					b.Show()


	def RemoveCmu(self, cmu):
		## prevents this cmu pronunciation from being displayed on the plot
		try:
			self.cmuLabels.remove(cmu)
		except:
			pass

		if self.GetUnionButtonState():
			for b in self.cmus[cmu]:
				if b.otherType not in self.otherLabels:
					b.Hide()

	def AddOther(self, other):
		## permits this other pronunciation to be displayed on the plot
		if other not in self.otherLabels:
			self.otherLabels.append(other)

		if self.GetUnionButtonState():
			for b in self.others[other]:
				b.Show() 
		else:
			for b in self.others[other]:
				if b.cmuType in self.cmuLabels:
					b.Show()


	def RemoveOther(self, other):
		## prevents this other pronunciation from being displayed on the plot
		try:
			self.otherLabels.remove(other)
		except:
			pass

		if self.GetUnionButtonState():
			for b in self.others[other]:
				if b.cmuType not in self.cmuLabels:
					b.Hide()

	def GetUnionButtonState(self):
		## gets state of the union/intersect button
		return self.GetTopLevelParent().phonPanel.unionButton.GetValue()

	def OnUnionButtonPress(self): # uses OnX name even though not technicallly bound to an event (sorry, I like the name)
		## updates self.visibleVowels after union button pressed
		cmuVowels = [i for cmu in self.cmuLabels for i in self.cmus[cmu]]
		otherVowels = [i for other in self.otherLabels for i in self.others[other]]
		if self.GetUnionButtonState():
			self.visibleVowels = set(cmuVowels + otherVowels) # using + instead of | because it is slightly faster
		else:
			self.visibleVowels = set(cmuVowels)&set(otherVowels)

	###--------------------------------###
	## the following functions deal with vowel button clicks
	###--------------------------------###

	def ShowPraatMeasurements(self, e):
		## when the frame comes back into focus after remeasuring in praat, show the remeasured vowel
		button = self.vowelInFocus
		if not self.GetRemeasurePermissions() and isfile('praatLog'):
			button.alternates = button.MakeAlternate(button.ReadPraatAlternates(), 'p')  
			self.remeasureOptions.append(button)
			for a in button.alternates:
				a.SetBitmap(self.GetPreloadedBitmap('alt'))
				self.remeasureOptions.append(a)
			self.CalculateFormantMaxMins()
			self.PlaceVowels()
		self.Refresh()



class PhonPanel(wx.Panel):
	## panel containing cmu and other toggle buttons (and union/intersect button)
	def __init__(self, parent):
		wx.Panel.__init__(self, parent = parent, style=wx.SUNKEN_BORDER, size = (600, 200)) 
		## init sizers
		sizer = wx.BoxSizer(wx.HORIZONTAL)
		cmuSizer = wx.BoxSizer(wx.VERTICAL)
		unionSizer = wx.BoxSizer(wx.VERTICAL)
		self.otherSizer = wx.BoxSizer(wx.VERTICAL)
		cmuGridSizer = wx.GridBagSizer(1,1)
		cmuMainButtonSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.otherGridSizer = wx.GridBagSizer(1,1)
		self.otherMainButtonSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.filterPanel = FilterPanel(self) 
		self.parent = parent

		## add stuff to phonSizer
		sizer.AddStretchSpacer(1)
		sizer.Add(cmuSizer)
		sizer.AddSpacer(10)
		sizer.Add(unionSizer, flag = wx.ALIGN_CENTER)
		sizer.AddSpacer(10)
		sizer.Add(self.otherSizer)
		sizer.AddStretchSpacer(1)
		sizer.Add(self.filterPanel)
		sizer.AddStretchSpacer(1)
		

		## add stuff to cmuSizer
		mainCmuButton = masterButton(self, 'CMU')
		cmuSizer.Add(mainCmuButton, flag = wx.ALIGN_CENTER)
		cmuSizer.Add(cmuGridSizer, flag = wx.ALIGN_CENTER)

		## add stuff to unionSizer
		self.unionButton = UButton(self)
		unionSizer.Add(self.unionButton, flag = wx.ALIGN_CENTER)

		## add stuff to otherSizer
		mainOtherButton = masterButton(self, self.parent.otherLabel if self.parent.otherLabel else 'OTHER')
		self.otherSizer.Add(mainOtherButton, flag = wx.ALIGN_CENTER)
		self.otherSizer.Add(self.otherGridSizer, flag = wx.ALIGN_CENTER)


		## add stuff to cmuGridSizer
		for i,col in enumerate(cmu):
			for j,c in enumerate(col):
				if not c: continue
				button = CmuButton(self,c)
				cmuGridSizer.Add(button, (j,i))
				mainCmuButton.AddMinion(button)
				self.parent.plotPanel.cmus[c] = set()

		## add stuff to otherGridSizer
		for i,col in enumerate(self.parent.other):
			for j,c in enumerate(col):
				if not c or c == '-': continue
				c = c.decode('utf8')
				button = OtherButton(self,c)
				self.otherGridSizer.Add(button, (i,j))
				mainOtherButton.AddMinion(button)
				self.parent.plotPanel.others[c] = set()
		print self.parent.plotPanel.others

		self.SetSizer(sizer)

	def RedrawOtherVowels(self):
		## redraws other vowel buttons when selecting a new phonetic alphabet
		self.otherSizer.Clear(True)
		mainOtherButton = masterButton(self, self.parent.otherLabel if self.parent.otherLabel else 'OTHER')
		self.otherSizer.Add(mainOtherButton, flag = wx.ALIGN_CENTER)
		self.otherGridSizer = wx.GridBagSizer(1,1)
		self.otherSizer.Add(self.otherGridSizer)
		otherDict = {}
		for i,col in enumerate(self.parent.other):
			for j,c in enumerate(col):
				if not c or c == '-': continue
				c = c.decode('utf8')
				button = OtherButton(self,c)
				self.otherGridSizer.Add(button, (i,j))
				mainOtherButton.AddMinion(button)
				otherDict[c] = set()
		for b in self.parent.plotPanel.allVowels:
			try: ## if otherType is not ''
				otherDict[b.otherType].add(b)
			except:
				pass
		self.parent.plotPanel.others = otherDict
		print self.parent.plotPanel.others
		self.parent.plotPanel.Refresh()
		self.Fit()
		self.parent.Fit()

class PlayButton(wx.Panel):
	## button plays sound clip from currently selected vowel  
	def __init__(self, parent):
		wx.Panel.__init__(self, parent = parent)
		## define sizers and controls
		sizer = wx.BoxSizer(wx.VERTICAL)
		text = wx.StaticText(self, label = "\nPLAY", style = wx.ALIGN_CENTER)
		self.playBitmap = wx.Bitmap('icons/control_buttons/play.png')
		self.pauseBitmap = wx.Bitmap('icons/control_buttons/pause_on.png')
		self.button = wx.BitmapButton(self, bitmap = self.playBitmap, size = (55,55))
		sizer.Add(text, flag = wx.EXPAND)
		sizer.Add(self.button)
		
		self.SetSizer(sizer)
		# button state
		self.play = False
		# bind events
		self.button.Bind(wx.EVT_BUTTON, self.OnClick) 

	def OnClick(self, e): ## TODO: make these consistent (right now onclick, onpress, etc.)
		## toggles the play state
		if self.play:
			self.play = False
			self.button.SetBitmapLabel(self.playBitmap)

		else:
			self.play = True
			self.button.SetBitmapLabel(self.pauseBitmap)

	def GetPlayState(self):
		## returns the play state
		return self.play 

class StdDevButtons(wx.Panel):
	## panel containing buttons that control the std dev ellipses on the plot
	def __init__(self, parent):
		wx.Panel.__init__(self, parent = parent)
		## define sizers and controls
		sizer = wx.BoxSizer(wx.VERTICAL)
		buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
		radioButtonSizer = wx.BoxSizer(wx.VERTICAL)
		text = wx.StaticText(self, label = "STANDARD\n DEVIATION", style = wx.ALIGN_CENTER)
		self.onBitmap = wx.Bitmap('icons/control_buttons/circles_on.png')
		self.offBitmap = wx.Bitmap('icons/control_buttons/circles.png')
		self.button = wx.BitmapButton(self, bitmap = self.offBitmap, size = (55,55))
		self.oneButton = wx.RadioButton(self, label = '1')
		self.twoButton = wx.RadioButton(self, label = '2')
		self.threeButton = wx.RadioButton(self, label = '3')
		## layout the contols
		sizer.Add(text, flag = wx.EXPAND)
		sizer.Add(buttonSizer, wx.EXPAND)
		buttonSizer.Add(self.button)
		buttonSizer.Add(radioButtonSizer)
		radioButtonSizer.Add(self.oneButton)
		radioButtonSizer.Add(self.twoButton)
		radioButtonSizer.Add(self.threeButton)
		self.SetSizer(sizer)

		self.recentlyPressed = self.oneButton ## placeholder for most recently selected radiobutton
		
		## bind button click to function
		self.button.Bind(wx.EVT_BUTTON, self.OnClick)
		self.oneButton.Bind(wx.EVT_RADIOBUTTON, self.RadioClick)
		self.twoButton.Bind(wx.EVT_RADIOBUTTON, self.RadioClick)
		self.threeButton.Bind(wx.EVT_RADIOBUTTON, self.RadioClick)

	def OnClick(self, e):
		## toggles radiobuttons when main button is clicked and draws the ellipse (if on)
		plotPanel = self.GetTopLevelParent().plotPanel
		if self.oneButton.GetValue(): 
			self.oneButton.SetValue(False)
			plotPanel.clearOverlay()
			self.button.SetBitmapLabel(self.offBitmap)
		elif self.twoButton.GetValue(): 
			self.twoButton.SetValue(False)
			plotPanel.clearOverlay()
			self.button.SetBitmapLabel(self.offBitmap)
		elif self.threeButton.GetValue(): 
			self.threeButton.SetValue(False)
			plotPanel.clearOverlay()
			self.button.SetBitmapLabel(self.offBitmap)
		else: 
			self.button.SetBitmapLabel(self.onBitmap)
			self.recentlyPressed.SetValue(True)
			plotPanel.DrawConfidenceEllipse( int(self.recentlyPressed.GetLabel()) )
			

	def RadioClick(self, e):
		## draws the appropriate ellipse when the radio button is clicked
		self.button.SetBitmapLabel(self.onBitmap)
		plotPanel = self.GetTopLevelParent().plotPanel
		pressed = e.GetEventObject()
		self.recentlyPressed = pressed
		plotPanel.DrawConfidenceEllipse( int(pressed.GetLabel()) )
		
	def IsOn(self):
		## gets the current state of the button
		if self.button.GetBitmapLabel() == self.onBitmap:
			return True
		return False


class ZoomButton(wx.Panel):
	## panel containing button to zoom in on plot
	def __init__(self, parent):
		wx.Panel.__init__(self, parent = parent)
		## define sizers and controls
		sizer = wx.BoxSizer(wx.VERTICAL)
		text = wx.StaticText(self, label = "\nZOOM", style = wx.ALIGN_CENTER)
		self.zoomBM = wx.Bitmap('icons/control_buttons/zoomin.png')
		self.zoomoutBM = wx.Bitmap('icons/control_buttons/zoomout.png')
		self.zoomingBM = wx.Bitmap('icons/control_buttons/zooming.png')
		self.button = wx.BitmapButton(self, bitmap = self.zoomBM, size = (55,55))
		## layout the controls
		sizer.Add(text, flag = wx.EXPAND)
		sizer.Add(self.button)
		self.SetSizer(sizer)
		## bind button click to function
		self.button.Bind(wx.EVT_BUTTON, self.OnPress)

	def OnPress(self, e):
		## toggles the button and sets zoom state in the plot panel
		plotPanel = self.GetTopLevelParent().plotPanel
		if self.button.GetBitmapLabel() == self.zoomBM:
			self.button.SetBitmapLabel(self.zoomingBM)
			plotPanel.ZoomIn()

		else:
			self.button.SetBitmapLabel(self.zoomBM)
			plotPanel.ResetZoom()



class ReMeasureButton(wx.Panel):
	## panel containing radio buttons to select remeasurement style
	def __init__(self, parent):
		wx.Panel.__init__(self, parent = parent)
		## define sizer and controls
		sizer = wx.BoxSizer(wx.VERTICAL)
		text = wx.StaticText(self, label = "\nREMEASURE USING", style = wx.ALIGN_CENTER)
		self.mode = 'P'
		self.praatButton = wx.RadioButton(self, label = 'PRAAT')
		self.praatButton.SetValue(True)
		self.formantButton = wx.RadioButton(self, label = 'FORMANTS')
		self.durationButton = wx.RadioButton(self, label = r'% OF DURATION')
		## layout controls
		sizer.Add(text)
		sizer.Add(self.praatButton)
		sizer.Add(self.formantButton)
		sizer.Add(self.durationButton)
		
		self.SetSizer(sizer)
		# bind button clicks
		self.praatButton.Bind(wx.EVT_RADIOBUTTON, self._SetMode)
		self.formantButton.Bind(wx.EVT_RADIOBUTTON, self._SetMode)
		self.durationButton.Bind(wx.EVT_RADIOBUTTON, self._SetMode)

	def _SetMode(self, e):
		## sets remeasurement mode
		if self.praatButton.GetValue(): self.mode = 'P'
		elif self.formantButton.GetValue(): self.mode = 'F'
		else: self.mode = 'D'

	def GetMode(self):
		## gets remeasurement mode
		return self.mode

class CancelButton(wx.Panel):
	## panel containing button to cancel remeasurement 
	def __init__(self, parent):
		wx.Panel.__init__(self, parent = parent)
		## define sizer and controls
		sizer = wx.BoxSizer(wx.VERTICAL)
		text = wx.StaticText(self, label = "\nCANCEL", style = wx.ALIGN_CENTER)
		self.button = wx.BitmapButton(self, bitmap = wx.Bitmap('icons/control_buttons/cancel.png'), size = (55,55))
		self.button.SetBitmapDisabled( wx.Bitmap('icons/control_buttons/cancel_off.png'))
		self.button.Disable()
		## layout controls
		sizer.Add(text, flag = wx.EXPAND)
		sizer.Add(self.button, flag = wx.ALIGN_CENTER)
		
		self.SetSizer(sizer)
		# bind button click event to function
		self.button.Bind(wx.EVT_BUTTON, self.OnClick)


	def OnClick(self, e):
		## resets the plot when the button is clicked
		## (only active when a remeasurement is taking place)
		plotPanel = self.GetTopLevelParent().plotPanel
		self.button.Disable()
		if not plotPanel.GetRemeasurePermissions():
			for rb in plotPanel.remeasureOptions:
				if rb is not plotPanel.vowelInFocus:
					plotPanel.RemoveStoredVowelValues(rb, rb.f1, rb.f2, rb.word, rb.duration, rb.cmuType, rb.otherType, rb.position)
					rb.Hide()
			plotPanel.remeasureOptions = []
			
			plotPanel.vowelInFocus.SetBitmap(plotPanel.vowelInFocus.circleBitmap)
			plotPanel.vowelInFocus = None

			plotPanel.SetRemeasurePermissions(True)
			plotPanel.CalculateFormantMaxMins()
			plotPanel.PlaceVowels()


class OverwriteWarningDialog(wx.Dialog):
	## custom dialog that warns user when a save will overwrite a pre-existing file
	def __init__(self, parent):
		wx.Dialog.__init__(self, parent)
		##init sizers and controls
		self.parent = parent
		sizer = wx.BoxSizer(wx.HORIZONTAL)
		vertSizer = wx.BoxSizer(wx.VERTICAL)
		self.text = wx.StaticText(self, label = 'WARNING: Saving will overwrite the original Info Files\nContinue?')
		buttonSizer = self.CreateSeparatedButtonSizer(wx.OK|wx.CANCEL)
		saveToButton = wx.Button(self, label = 'Change Save Location')
		buttonSizer.Add(saveToButton, flag = wx.ALIGN_CENTER)
		## add buttons to sizers
		vertSizer.AddSpacer(10)
		vertSizer.Add(self.text)
		vertSizer.Add(buttonSizer)
		vertSizer.AddSpacer(10)

		sizer.AddSpacer(10)
		sizer.Add(vertSizer)
		sizer.AddSpacer(10)

		self.SetSizer(sizer)
		# bind functions to button click
		saveToButton.Bind(wx.EVT_BUTTON, self.OnSaveTo)

		self.Fit()
		self.Centre()

	def OnSaveTo(self, e):
		## select a new save location and warn again if a file will be ovewritten
		self.parent.GetTopLevelParent().OnSaveTo(None)
		newLabel = 'Save file changed to:\n'+self.parent.GetTopLevelParent().saveDir+'\n\nContinue with save?'
		if self.parent.GetTopLevelParent().saveDir == self.parent.GetTopLevelParent().infoDir:
			newLabel = 'Save location not changed\nWARNING: Saving will overwrite the original Info Files\nContinue?'
		self.text.SetLabel(newLabel)
		self.Fit()

class SaveButton(wx.Panel):
	## panel containg button to save current progress to log files
	def __init__(self, parent):
		wx.Panel.__init__(self, parent = parent)
		## define sizer and controls
		sizer = wx.BoxSizer(wx.VERTICAL)
		text = wx.StaticText(self, label = "\nSAVE", style = wx.ALIGN_CENTER)
		self.button = wx.BitmapButton(self, bitmap = wx.Bitmap('icons/control_buttons/save.png'), size = (55,55))
		self.button.SetBitmapDisabled(wx.Bitmap('icons/control_buttons/save_off.png'))
		self.button.Disable()
		## layout controls
		sizer.Add(text, flag = wx.EXPAND)
		sizer.Add(self.button)

		self.SetSizer(sizer)
		## bind events
		self.button.Bind(wx.EVT_BUTTON, self.OnClick)

		self.columnIndexes = {} ## this is set when loading files (set from plotPanel)

	def OnClick(self, e):
		## warns if about to overwrite old files and then saves 
		try: 
			self.saveDir = self.GetTopLevelParent().saveDir 
			self.infoDir = self.GetTopLevelParent().infoDir 
		except:
			return
		if self.saveDir == self.infoDir:
			if OverwriteWarningDialog(self).ShowModal() == wx.ID_OK:
				self.SaveFiles()
		else:
			self.SaveFiles()

	def SaveFiles(self):
		## saves the data from plotPanel.changes to the new file 
		## by reading the old input file and making changes to it			
		plotPanel = self.GetTopLevelParent().plotPanel
		delimiter = self.GetTopLevelParent().fileDelim
		## iterate over plotPanel.changes
		for infoFile,ch in plotPanel.changes.items():
			logFile = join(self.saveDir , basename(infoFile))
			lines = []
			with open(infoFile, 'r') as infoF: ## read old (input) file 
				lines = [line for line in infoF]
			for c in ch: ## make changes to the line read from the old file according to plotPanel.changes
				lines[c[0]] = lines[c[0]].strip('\n').split(delimiter)
				for i, columnIndex in enumerate(self.columnIndexes[infoFile]):
					lines[c[0]][columnIndex] = c[i+1]
				lines[c[0]] = str(delimiter).join(lines[c[0]]+c[5:])+'\n' 
			with open(logFile, 'w') as logF: ## write new lines (with changes) to the new file
				for l in lines:
					logF.write(l)
		plotPanel.changes = {}

	def CheckState(self):
		## enables/disables the button if there is nothing to save
		if self.GetTopLevelParent().past: 
			self.button.Enable()
			self.GetTopLevelParent().saveItem.Enable()
		else: 
			self.button.Disable()
			self.GetTopLevelParent().saveItem.Enable(False)

class UndoRedoButtons(wx.Panel):
	## panel containing buttons to undo/redo actions on the plot 
	def __init__(self, parent):
		wx.Panel.__init__(self, parent = parent)
		## define sizer and controls
		sizer = wx.BoxSizer(wx.HORIZONTAL)
		undoText = wx.StaticText(self, label = "\nUNDO", style = wx.ALIGN_CENTER)
		self.undoButton = wx.BitmapButton(self, bitmap = wx.Bitmap('icons/control_buttons/undo.png'), size = (55,55))
		self.undoButton.SetBitmapDisabled(wx.Bitmap('icons/control_buttons/undo_off.png'))
		self.undoButton.Disable()
		redoText = wx.StaticText(self, label = "\nREDO", style = wx.ALIGN_CENTER)
		self.redoButton = wx.BitmapButton(self, bitmap = wx.Bitmap('icons/control_buttons/redo.png'), size = (55,55))
		self.redoButton.SetBitmapDisabled(wx.Bitmap('icons/control_buttons/redo_off.png'))
		self.redoButton.Disable()
		undoSizer = wx.BoxSizer(wx.VERTICAL)
		redoSizer = wx.BoxSizer(wx.VERTICAL)
		## layout controls
		sizer.Add(undoSizer)
		sizer.AddSpacer(3)
		sizer.Add(redoSizer)
		undoSizer.Add(undoText, flag = wx.EXPAND)
		undoSizer.Add(self.undoButton)
		redoSizer.Add(redoText, flag = wx.EXPAND)
		redoSizer.Add(self.redoButton)
		self.SetSizer(sizer)
		
		self.topParent = self.GetTopLevelParent()
		## bind click events
		self.undoButton.Bind(wx.EVT_BUTTON, self.Undo)
		self.redoButton.Bind(wx.EVT_BUTTON, self.Redo)

	def CheckState(self):
		## enables/disables the buttons if there is something to un/redo or not
		if self.topParent.past: 
			self.undoButton.Enable()
			self.GetTopLevelParent().undoItem.Enable()
		else: 
			self.undoButton.Disable()
			self.GetTopLevelParent().undoItem.Enable(False)
		if self.topParent.future: 
			self.redoButton.Enable()
			self.GetTopLevelParent().redoItem.Enable()
		else: 
			self.redoButton.Disable()
			self.GetTopLevelParent().redoItem.Enable(False)
		self.GetTopLevelParent().toolBarPanel.saveButton.CheckState() 

	def Undo(self, e):
		## undoes last remeasurement
		command = self.topParent.past.pop()
		self.ExecuteCommand(*command)
		self.topParent.future.append((command[0], command[2], command[1]))
		self.CheckState()

	def Redo(self, e):
		## redoes last undid remeasurement
		command = self.topParent.future.pop()
		self.ExecuteCommand(*command)
		self.topParent.past.append((command[0], command[2], command[1]))
		self.CheckState()

	def ExecuteCommand(self, commandType, oldState, newState):
		## remeasures (or adds back) or removes a vowel according to the command
		if commandType == 'remeasure': 
			self.topParent.plotPanel.allVowels.remove(newState)
			self.topParent.plotPanel.RemoveStoredVowelValues(newState, newState.f1, newState.f2, newState.word, newState.duration, newState.cmuType, newState.otherType, newState.position)
			newState.Hide()
			self.topParent.plotPanel.allVowels.add(oldState)
			self.topParent.plotPanel.AddVowelValues(oldState, oldState.f1, oldState.f2, oldState.word, oldState.duration, oldState.cmuType, oldState.otherType)
			oldState.Show()
			newState.LogChange()
		elif commandType == 'remove':
			if newState:
				for v in newState:
					v.RemoveVowel()
			elif oldState:
				for v in oldState:
					self.topParent.plotPanel.allVowels.add(v)
					self.topParent.plotPanel.AddVowelValues(v, v.f1, v.f2, v.word, v.duration, v.cmuType, v.otherType)
					v.Show()
					good, note = self.GetTopLevelParent().toolBarPanel.removeButton.dialog.GetRemoveInfo()
					v.LogChange()
		else:
			print >> sys.stderr, 'bad undo/redo execution command,  shouldn\'t get here'
		## reset plot
		self.topParent.plotPanel.CalculateFormantMaxMins()
		self.topParent.plotPanel.PlaceVowels()

class RemoveButton(wx.Panel):
	## panel containing a button to remove vowels that have already been evaluated 
	def __init__(self, parent):
		wx.Panel.__init__(self, parent = parent)
		## define sizer and controls
		self.parent = parent
		sizer = wx.BoxSizer(wx.VERTICAL)
		text = wx.StaticText(self, label = "REMOVE\n FROM PLOT", style = wx.ALIGN_CENTER)
		self.onBitmap = wx.Bitmap('icons/control_buttons/remove_on.png')
		self.offBitmap = wx.Bitmap('icons/control_buttons/remove.png')
		self.button = wx.BitmapButton(self, bitmap = self.offBitmap, size = (55,45))
		self.optionButton = wx.BitmapButton(self, bitmap = wx.Bitmap('icons/control_buttons/dropdown.png'), size = (55,20))
		self.removeMode = False
		## layout controls
		sizer.Add(text, flag = wx.EXPAND)
		sizer.Add(self.button, flag = wx.ALIGN_CENTER)
		sizer.Add(self.optionButton, flag = wx.ALIGN_CENTER)
		self.SetSizer(sizer)
		## set up dialog with note options to add when removing a vowel
		self.dialog = RemoveFromPlotOptions(self)
		self.dialog.Hide()
		## bind button click to function
		self.button.Bind(wx.EVT_BUTTON, self.OnRemove)
		self.optionButton.Bind(wx.EVT_BUTTON, self.OnPress)
		self.GetTopLevelParent().Bind(wx.EVT_MOVE, self.PlaceDialog)

	def OnRemove(self, e):
		## toggles remove button and tells plot panel to go into remove mode
		if self.removeMode:
			self.removeMode = False
			self.GetTopLevelParent().plotPanel.removing = False
			self.button.SetBitmapLabel(self.offBitmap)
		else:
			self.removeMode = True
			self.GetTopLevelParent().plotPanel.removing = True
			self.button.SetBitmapLabel(self.onBitmap)
			## kills play mode 
			if self.parent.playButton.GetPlayState():
				self.parent.playButton.OnClick(None)
			## kills remeasurement
			if not self.GetTopLevelParent().plotPanel.GetRemeasurePermissions():
				self.parent.cancelButton.OnClick(None)

	def OnPress(self, e):
		## initiates a dialog box for adding notes to removed vowels
		if not self.dialog.IsShown():
			self.PlaceDialog()
			self.dialog.Show()

	def PlaceDialog(self, e = None):
		## when the frame is moved, this makes sure the dialog stays in position
		x,y = self.optionButton.GetPosition()
		y += self.optionButton.GetSize()[1]
		self.dialog.Move(self.ClientToScreen((x,y)))

class ToolBar(wx.Panel):
	## panel containing toolbar buttons (at top of window)
	def __init__(self, parent):
		wx.Panel.__init__(self, parent = parent, style=wx.SUNKEN_BORDER, size = (800,100)) 
		## define sizer and panels
		sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.playButton = PlayButton(self)
		self.stdDevButtons = StdDevButtons(self)
		self.zoomButton = ZoomButton(self)
		self.reMeasureButton = ReMeasureButton(self)
		self.cancelButton = CancelButton(self)
		self.saveButton = SaveButton(self)
		self.undoRedoButtons = UndoRedoButtons(self)
		self.removeButton = RemoveButton(self)
		## layout panels
		sizer.AddStretchSpacer(1)
		sizer.Add(self.playButton, flag = wx.EXPAND)
		sizer.AddSpacer(3)
		sizer.Add(self.stdDevButtons, flag = wx.EXPAND)
		sizer.AddSpacer(3)
		sizer.Add(self.zoomButton, flag = wx.EXPAND)
		sizer.AddSpacer(3)
		sizer.Add(self.reMeasureButton, flag = wx.EXPAND)
		sizer.AddSpacer(3)
		sizer.Add(self.cancelButton, flag = wx.EXPAND)
		sizer.AddSpacer(3)
		sizer.Add(self.saveButton, flag = wx.EXPAND)
		sizer.AddSpacer(3)
		sizer.Add(self.undoRedoButtons, flag = wx.EXPAND)
		sizer.AddSpacer(3)
		sizer.Add(self.removeButton, flag = wx.EXPAND)
		sizer.AddStretchSpacer(1)

		self.SetSizer(sizer)


class OtherVowelDialog(wx.Dialog):
	## dialog for setting up a new alternate phonetic alphabet or loading a saved one
	def __init__(self, parent):
		wx.Dialog.__init__(self, parent, title = 'Select Alternate Phonetic Alphabet')
		self.Centre()
		## init sizers
		sizer = wx.BoxSizer(wx.VERTICAL)
		midSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.grid = wx.GridBagSizer()
		optionsSizer = wx.BoxSizer(wx.VERTICAL)
		titleSizer = wx.BoxSizer(wx.HORIZONTAL)
		## name of the phon alphabet
		self.titleTitle = wx.StaticText(self, label = 'Name: ')
		self.title = wx.TextCtrl(self, style = wx.TE_PROCESS_TAB|wx.TE_RICH)
		## button to add a new column
		self.addColumnButton = wx.Button(self, label = '+', size = (30,wx.DefaultSize[1]))
		## add title to sizer
		titleSizer.AddSpacer(4)
		titleSizer.Add(self.titleTitle)
		titleSizer.AddSpacer(2)
		titleSizer.Add(self.title)
		## init buttons
		openButton = wx.Button(self, -1, 'Open')
		saveButton = wx.Button(self, wx.ID_SAVE)
		cancelButton = wx.Button(self, wx.ID_CANCEL)
		okButton = wx.Button(self, wx.ID_OK)
		## add buttons to sizer
		optionsSizer.Add(openButton, flag = wx.ALIGN_RIGHT)
		optionsSizer.AddSpacer(4)
		optionsSizer.Add(saveButton, flag = wx.ALIGN_RIGHT)
		optionsSizer.AddSpacer(24)
		optionsSizer.Add(cancelButton, flag = wx.ALIGN_RIGHT)		
		optionsSizer.AddSpacer(4)
		optionsSizer.Add(okButton, flag = wx.ALIGN_RIGHT)
		## add grid (with text input boxes) to the sizer
		midSizer.AddSpacer(4)
		midSizer.Add(self.grid)
		midSizer.Add(self.addColumnButton)
		midSizer.AddSpacer(20)
		midSizer.Add(optionsSizer)
		midSizer.AddSpacer(4)
		## tetris in dem sizers
		sizer.AddSpacer(4)
		sizer.Add(titleSizer)
		sizer.Add(midSizer)
		sizer.AddSpacer(4)

		self.SetSizer(sizer)
		## get previousy created alphabets
		self.default = 'CELEX' 
		self.alphabets = self.GetChoices()
		self.SetGridValues(self.default, self.alphabets[self.default])
		# bind events
		self.addColumnButton.Bind(wx.EVT_BUTTON, self.AddColumn)
		openButton.Bind(wx.EVT_BUTTON, self.GetSavedAlphabets)
		saveButton.Bind(wx.EVT_BUTTON, self.SaveAlphabet)

		self.Fit()

	def GetAlphabet(self):
		# returns the current alphabet displayed on the grid
		return (self.title.GetValue().strip().upper(), self.ReadGrid())

	def SaveAlphabet(self, e):
		## save current alphabet on the grid so it can be used later
		name, alphabet = self.GetAlphabet()
		self.alphabets[name] = alphabet
		if not name: wx.MessageDialog(self, 'Please name the new alphabet before saving', style=wx.OK|wx.CENTRE).ShowModal()
		elif name in self.alphabets.keys(): wx.MessageDialog(self, 'Alphabet named '+name+' already exists', style=wx.OK|wx.CENTRE).ShowModal()
		else:
			self.AddAlphabet(name, alphabet)

	def ReadGrid(self):
		## reads the grid into a list of tuples (to be read by everything else)
		newAlphabet = []
		for row in range(6):
			column = []
			for col in range(self.gridColumns):	
				vowel = self.grid.FindItemAtPosition((row,col)).Window.GetValue().strip()
				if vowel == '-': 
					wx.MessageDialog(self, 'Forbidden vowel name found\nnamed: -', style=wx.OK|wx.CENTRE).ShowModal()
					return
				if not vowel: vowel = '-'
				column.append(vowel)
			newAlphabet.append(tuple(column))
		return newAlphabet


	def AddColumn(self, e = None):
		## adds another column to the grid
		for i in range(6):
			self.grid.Add(wx.TextCtrl(self, size = (30,wx.DefaultSize[1]),style = wx.TE_PROCESS_TAB|wx.TE_RICH|wx.TE_CENTRE), (i, self.gridColumns) )		
		self.gridColumns += 1
		self.Fit()

	def GetChoices(self):
		## reads currently saved alphabets from 'other_phon_alphabet.txt'
		other = {}
		with open('other_phon_alphabet.txt', 'r') as otherVowels:
			for line in otherVowels:
				if line[0] == ' ':  
					otherLabel = line.strip().upper()
					if line[:2] == '  ': self.default = otherLabel
					other[otherLabel] = []
					continue
				other[otherLabel].append(tuple(line.strip().split()))
		return other

	def SetGridValues(self, name, values):
		## loads a saved alphabet onto the grid 
		self.grid.Clear(True)
		self.gridColumns = 0
		self.title.SetValue(name.strip())
		for i,col in enumerate(values):
			for j,c in enumerate(col):
				if not c or c == '-': 
					c = ''
				try:
					self.grid.FindItemAtPosition((i,j)).Window.SetValue(c.decode('utf8'))
				except:
					self.AddColumn()
					self.grid.FindItemAtPosition((i,j)).Window.SetValue(c.decode('utf8'))

	def GetSavedAlphabets(self, e):
		## Displays a dialog which lets the user select a previously saved alphabet
		options = SingleChoiceDialogImproved(self, message ='Saved Alphabets:', caption = '', choices = self.alphabets.keys(), defaultOpt = True, permanentChoices = ['CELEX', 'IPA'])
		if options.ShowModal()== wx.ID_OK:
			choice = options.GetStringSelection()
			self.SetGridValues(choice, self.alphabets[choice])

	def SetDefault(self, newDefault):
		## sets an alphabet as the default one (will open as this on startup)
		## must be named SetDefault in order to work with singlechoicedialogimproved()
		self.default = newDefault
		lines = []
		with open('other_phon_alphabet.txt', 'r') as otherVowels:
			for line in otherVowels:
				if line[:2] == '  ':
					line = ' '+line.strip()+'\n'
				if line.strip().upper() == newDefault:
					line = '  '+line.strip()+'\n'
				lines.append(line)
		with open('other_phon_alphabet.txt', 'w') as otherVowels:
			for l in lines:
				otherVowels.write(l)

	def GetDefault(self):
		## returns the current default 
		return self.default

	def RemoveOption(self, alphabetName):
		## deletes an alphabet from other_phon_alphabet.txt
		## must be named removeoption in order to work with singlechoicedialogimproved
		lines = []
		if alphabetName == self.default:
			self.SetDefault('CELEX')
		with open('other_phon_alphabet.txt', 'r') as otherVowels:
			start = False
			for line in otherVowels:
				if line.strip().upper() == alphabetName: 
					start = True
					continue
				if start:
					if line[0] == ' ': 
						start = False
				else:
					lines.append(line)
		with open('other_phon_alphabet.txt', 'w') as otherVowels:
			for l in lines:
				otherVowels.write(l)

	def AddAlphabet(self, name, alphList):
		## writes an alphabet to other_phon_alphabet.txt
		with open('other_phon_alphabet.txt', 'a') as otherVowels:
			otherVowels.write('\n '+name+'\n')
			for l in alphList:
				otherVowels.write(' '.join(list(l))+'\n' )

class SingleChoiceDialogImproved(wx.SingleChoiceDialog):
	## dialog used to display some saved settings options 
	## (hacks a SingleChoiceDialog class to add a few new options) 
	def __init__(self, parent, message, caption, choices=[], style=wx.CHOICEDLG_STYLE, pos=wx.DefaultPosition, permanentChoices = [], defaultOpt = False):
		wx.SingleChoiceDialog.__init__(self, parent, message, caption, choices, style, pos)
		## this is the hacky bit to add some new controls to wx.SingleChoiceDialog
		children = self.GetChildren()
		self.parent = parent
		self.permChoices = permanentChoices
		for c in children:
			if isinstance(c, wx.ListBox):self.listbox = c 
		self.sizer = self.GetSizer()
		defaultRemoveSizer = wx.BoxSizer(wx.HORIZONTAL)
		removeButton = wx.Button(self, -1, 'Remove')
		if defaultOpt: ## adds a button to set the default if defaultOpt == True
			defaultButton = wx.Button(self, -1, 'Set Default')
			defaultRemoveSizer.Add(defaultButton, flag = wx.ALIGN_CENTER)
			defaultButton.Bind(wx.EVT_BUTTON, self.OnDefault) ## binds click event
			defaultRemoveSizer.AddSpacer(10)
		
		## adds new stuff into the sizer
		defaultRemoveSizer.Add(removeButton, flag = wx.ALIGN_CENTER)
		self.sizer.Insert(2, defaultRemoveSizer, flag = wx.ALIGN_CENTER)

		self.Fit()
		## bind buttton events
		removeButton.Bind(wx.EVT_BUTTON, self.OnRemove)

	def OnDefault(self, e):
		## sets default in the parent window (parent window must have SetDefault() function) <-- this I don't like TODO: make better
		self.parent.SetDefault(self.GetStringSelection())

	def OnRemove(self, e):
		## removes option from list in parent window (parent window must have RemoveOption() function) <-- this I don't like TODO: make better
		name = self.GetStringSelection()
		if name not in self.permChoices:
			if wx.MessageDialog(self, 'Permanently Delete '+name+'?\nThis cannot be undone', style=wx.OK|wx.CENTRE|wx.CANCEL).ShowModal() == wx.ID_OK:
				self.parent.RemoveOption(name)
				self.listbox.Delete(self.listbox.GetSelection())
				self.listbox.SetSelection(0)
		else:
			wx.MessageDialog(self, 'Cannot delete '+name, style=wx.OK|wx.CENTRE).ShowModal()

	def GetStringSelection(self):
		return self.listbox.GetString(self.listbox.GetSelection())

class ConfigInputDialog(wx.Dialog):
	## dialog that lets the user change how the input files are read
	## the way this whole class is set up is really ugly... TODO: simplify
	def __init__(self, parent):
		wx.Dialog.__init__(self, parent, title = 'Input file configuration')
		self.Centre()
		## init class variables
		self.colNames = {}
		self.options = []
		self.default = None 
		## init sizers
		horSizer = wx.BoxSizer(wx.HORIZONTAL)
		vertSizer = wx.BoxSizer(wx.VERTICAL)
		self.sizer = wx.GridBagSizer(3,1)
		self.altSizer = wx.GridBagSizer(3,1)
		self.altSizer.SetEmptyCellSize((42,0))
		buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
		nameSizer = wx.BoxSizer(wx.HORIZONTAL)

		## name of the current configuration
		nameSizer.Add(wx.StaticText(self, label = 'Configuration ID:'))
		self.name = wx.TextCtrl(self)
		self.name.SetToolTip(wx.ToolTip('Name (identifier) of this file configuration'))
		nameSizer.AddSpacer(3)
		nameSizer.Add(self.name)		
		## add all input boxes for the column headings (not including remeasurement options)
		self.sizer.Add(wx.StaticText(self, label = 'Vowel info file specs :'), (0,0), (1,2))
		
		self.sizer.Add(wx.StaticText(self, label = 'Column delimiter*:'), (1,0))
		self.delimiter = wx.TextCtrl(self, style = wx.TE_PROCESS_TAB)
		self.delimiter.SetToolTip(wx.ToolTip('columns are delimited by this value (ex. \'\\t\' for a single tab)'))
		self.colNames['delimiter'] = self.delimiter
		self.sizer.Add(self.delimiter, (1,1))
		
		self.sizer.Add(wx.StaticText(self, label = 'Heading row number*:'), (1,3))
		heading_row = wx.TextCtrl(self)
		heading_row.SetToolTip(wx.ToolTip('the row number that containing the column headings (must be an integer)'))
		self.sizer.Add(heading_row, (1,4))
		self.colNames['heading_row'] = heading_row
		self.sizer.Add(wx.StaticText(self, label = 'Column heading for :'), (3,0), (1,2))

		self.sizer.Add(wx.StaticText(self, label = 'CMU label*:'), (4,0))
		cmu = wx.TextCtrl(self)
		cmu.SetToolTip(wx.ToolTip('Column name for:\nCMU vowel token (with or without stress) (ex. AH or AH2)'))
		self.sizer.Add(cmu, (4,1))
		self.colNames['CMU'] = cmu

		self.sizer.Add(wx.StaticText(self, label = 'Stress*:'), (5,0))
		stress = wx.TextCtrl(self)
		stress.SetToolTip(wx.ToolTip('Column name for:\nvowel stress (1 = primary, 2 = secondary, 0 = no stress)'))
		self.sizer.Add(stress, (5,1))
		self.colNames['STRESS'] = stress

		self.sizer.Add(wx.StaticText(self, label = 'Index:'), (6,0))
		index = wx.TextCtrl(self)
		index.SetToolTip(wx.ToolTip("Column name for:\nindex of the vowel in the word (ex. in ['W','ER1','D'] the vowel has an index of 1)"))
		self.sizer.Add(index, (6,1))
		self.colNames['INDEX'] = index

		self.sizer.Add(wx.StaticText(self, label = 'F1*:'), (7,0))
		f1 = wx.TextCtrl(self)
		f1.SetToolTip(wx.ToolTip("Column name for:\nfirst formant"))
		self.sizer.Add(f1, (7,1))
		self.colNames['F1'] = f1

		self.sizer.Add(wx.StaticText(self, label = 'F2*:'), (8,0))
		f2 = wx.TextCtrl(self)
		f2.SetToolTip(wx.ToolTip("Column name for:\nsecond formant"))
		self.sizer.Add(f2, (8,1))	
		self.colNames['F2'] = f2

		self.sizer.Add(wx.StaticText(self, label = 'Pronunciation:'), (4,3))
		pronunciation = wx.TextCtrl(self)
		pronunciation.SetToolTip(wx.ToolTip("Column name for:\ncmu pronunciation of the whole word (as a python list ex. ['W','ER1','D']"))
		self.sizer.Add(pronunciation, (4,4))
		self.colNames['PRONUNCIATION'] = pronunciation

		self.sizer.Add(wx.StaticText(self, label = 'Maximum formant*:'), (5,3))
		maximumFormant = wx.TextCtrl(self)
		maximumFormant.SetToolTip(wx.ToolTip('Column name for:\nthe maximum number of formants setting when the F1 and F2 were measured'))
		self.sizer.Add(maximumFormant, (5,4))
		self.colNames['MAXFORMANT'] = maximumFormant

		self.sizer.Add(wx.StaticText(self, label = 'Start*:'), (6,3))
		start = wx.TextCtrl(self)
		start.SetToolTip(wx.ToolTip('Column name for:\ntime in the sound file when the vowel begins'))
		self.sizer.Add(start, (6,4))
		self.colNames['START'] = start

		self.sizer.Add(wx.StaticText(self, label = 'End*:'), (7,3))
		end = wx.TextCtrl(self)
		end.SetToolTip(wx.ToolTip('Column name for:\ntime in the sound file when the vowel ends'))
		self.sizer.Add(end, (7,4))
		self.colNames['END'] = end

		self.sizer.Add(wx.StaticText(self, label = 'Time*:'), (8,3))
		time = wx.TextCtrl(self)
		time.SetToolTip(wx.ToolTip("Column name for:\ntime in the sound file at which the formants were measured (seconds)"))
		self.sizer.Add(time, (8,4))
		self.colNames['TIME'] = time

		self.sizer.Add(wx.StaticText(self, label = 'Word*:'), (9,0))
		word = wx.TextCtrl(self)
		word.SetToolTip(wx.ToolTip("Column name for:\nword in which the vowel occurs (orthography not pronunciation"))
		self.sizer.Add(word, (9,1))
		self.colNames['WORD'] = word 

		self.sizer.Add(wx.StaticText(self, label = 'Other label:'), (9,3))
		other = wx.TextCtrl(self)
		other.SetToolTip(wx.ToolTip('Column name for:\nother vowel token (ex. vowel in celex, ipa, etc)'))
		self.sizer.Add(other, (9,4))
		self.colNames['OTHER'] = other

		self.sizer.Add(wx.StaticText(self, label = 'Pitch:'), (10,0))
		pitch = wx.TextCtrl(self)
		pitch.SetToolTip(wx.ToolTip('Column name for:\npitch value (f0)'))
		self.sizer.Add(pitch, (10,1))
		self.colNames['PITCH'] = pitch
		## add the labels for the remeasurement option headings (but not the input boxes themselves)
		self.sizer.Add(wx.StaticText(self, label = 'Alternate F1,F2 measured...'), (11,0), (1,4))
		self.sizer.Add(wx.StaticText(self, label = 'at X% of vowel duration :'), (12,0), (1,2))
		self.durAddButton = wx.Button(self, label = '+', size = (30,wx.DefaultSize[1]))
		self.sizer.Add(self.durAddButton, (13,0))
		self.sizer.Add(wx.StaticText(self, label = 'with max formant value of :'), (12,3), (1,2))
		self.maxFormAddButton = wx.Button(self, label = '+', size = (30,wx.DefaultSize[1]))
		self.sizer.Add(self.maxFormAddButton, (13,3))
		
		self.rowNum = [0,0] ## used when redrawing everything in altSizer to determine how many rows have been drawn
		## init buttons and place them in the sizer
		saveButton = wx.Button(self, id = wx.ID_SAVE)
		saveButton.SetDefault()
		cancelButton = wx.Button(self, id = wx.ID_CANCEL)
		openButton = wx.Button(self, id = wx.ID_OPEN)
		buttonSizer.Add(openButton, flag = wx.ALIGN_LEFT)
		buttonSizer.AddSpacer(50)
		buttonSizer.Add(saveButton, flag = wx.ALIGN_RIGHT)
		buttonSizer.AddSpacer(10)
		buttonSizer.Add(cancelButton, flag = wx.ALIGN_RIGHT)
		## tetris all the sizers together
		vertSizer.AddSpacer(10)
		vertSizer.Add(nameSizer)
		vertSizer.AddSpacer(10)
		vertSizer.Add(self.sizer)
		vertSizer.Add(wx.StaticText(self, label = 'mandatory fields are marked with a *'))
		vertSizer.AddSpacer(3)
		vertSizer.Add(self.altSizer)
		vertSizer.AddSpacer(10)
		vertSizer.Add(buttonSizer, flag = wx.ALIGN_RIGHT)
		vertSizer.AddSpacer(10)

		horSizer.AddSpacer(10)
		horSizer.Add(vertSizer)
		horSizer.AddSpacer(10)
		
		self.ReadInSettings()
		self.SetSizer(horSizer)		
		self.Fit()
		## bind events to the buttons
		self.durAddButton.Bind(wx.EVT_BUTTON, self.AddAltVowelRow)
		self.maxFormAddButton.Bind(wx.EVT_BUTTON, self.AddAltVowelRow)
		saveButton.Bind(wx.EVT_BUTTON, self.OnOK)
		self.delimiter.Bind(wx.EVT_TEXT, self.DisplayWhiteSpace)
		openButton.Bind(wx.EVT_BUTTON, self.OnOpen)

	def WriteSettings(self):
		## write settings to config.txt
		with open('config.txt', 'a') as config:
			config.write('\n '+self.name.GetValue().strip()+'\n')
			for key,value in self.colNames.items():
				if key in ['DURATION_ALTERNATES', 'MAXFORMANT_ALTERNATES']:
					value = '||'.join([v[0].GetValue()+'|'+v[1].GetValue() for v in value if v[0].GetValue().strip()])
				else:
					value = value.GetValue().strip()
				config.write(key+'\t'+value+'\n')

	def RemoveOption(self, name):
		## removes setting from config.txt
		## must be named removeoption in order to work with singlechoicedialogimproved
		start = False
		lines = []
		self.options.remove(name)
		if name == self.default:
			self.SetDefault('FAVE')
		with open('config.txt') as config:
			for line in config:
				if start:
					if not line.strip():
						start = False
						continue
				else:
					if line[0] == ' ' and name in line:
						start = True
					else:
						lines.append(line)
		with open('config.txt', 'w') as config:
			for l in lines:
				config.write(l)

	def SetDefault(self, newDefault):
		## sets the current setting as the default setting (to be used on start up)
		## called automatically when saving a new setting configuration 
		## must be named SetDefault in order to work with singlechoicedialogimproved()
		self.default = newDefault
		lines = []
		with open('config.txt') as config:
			for line in config:
				if line[:2] == '  ':
					line = ' '+line.strip()+'\n'
				if line.strip().upper() == newDefault:
					line = '  '+line.strip()+'\n'
				lines.append(line)
		with open('config.txt', 'w') as config:
			for l in lines:
				config.write(l)

	def ClearAlternateValues(self):
		## clears altSizer when redrawing (when loading a saved configuration)
		self.options = []
		self.altSizer.Clear(True)
		self.rowNum = [0,0]
		self.colNames['DURATION_ALTERNATES'] = []
		self.colNames['MAXFORMANT_ALTERNATES'] = []

	def ReadInSettings(self, name = None):
		## reads settings from file and displays them on the window
		self.ClearAlternateValues()
		start = False
		with open('config.txt') as config:
			for line in config:
				if line[0] == ' ' and line.strip():
					self.options.append(line.strip())
					if line[:2] == '  ': 
						self.default = line.strip()
						if name == None:
							name = self.default
				if start:
					if not line.strip():
						start = False
						continue
					key, value = line.split('\t')
					if key in ['DURATION_ALTERNATES', 'MAXFORMANT_ALTERNATES']:
						values = value.split('||')
						for v in values:
							button = self.durAddButton if key == 'DURATION_ALTERNATES' else self.maxFormAddButton
							self.AddAltVowelRow(button = button)
							v = v.split('|')
							self.colNames[key][-1][0].SetValue(v[0].strip())
							self.colNames[key][-1][1].SetValue(v[1].strip())
					else:
						self.colNames[key].SetValue('') ## makes sure backslashes stay the same in delimiter textctrl when rewriting
						self.colNames[key].SetValue(value.strip())
				elif name != None and line[0] == ' ' and name in line:
					start = True
					self.name.SetValue(line.strip())
	

	def OnOpen(self, e):
		## opens SingleChoiceDialogImproved to let user choose a saved configuration
		options = SingleChoiceDialogImproved(self, message ='Saved File Configurations:', caption = '', choices = self.options, permanentChoices = ['FAVE'])
		if options.ShowModal() == wx.ID_OK:
			choice = options.GetStringSelection()
			self.ReadInSettings(choice)

	def DisplayWhiteSpace(self, e):
		## used to show whitespace as a visible string in delimiter input box
		## ex: '	' --> '\t' or ' ' --> '\s'
		textCtrl = e.GetEventObject()
		value = textCtrl.GetValue()
		point = textCtrl.GetInsertionPoint()
		newAddition = value[point-1:point].replace(' ',r'\s').encode('unicode-escape').decode()
		if newAddition == r'\\s': newAddition = newAddition[1:]
		value = textCtrl.GetValue()[:point-1]+newAddition+textCtrl.GetValue()[point:]
		try: 
			length = len(self.oldValue)
		except: 
			length = 0 
		if length < len(value): 
			textCtrl.ChangeValue(value)
			textCtrl.SetInsertionPoint(point+1)
		self.oldValue = value 
		

	def OnOK(self, e):
		## checks that all required fields are filled with appropriate values before saving the configuration
		## and setting it as the default (warns if an input field is bad and marks it with a red background)
		good = True
		for k,v in self.colNames.items():
			if k == 'heading_row':
				good = self.CheckInput(v, required = True, needsInt = True)
			elif k == 'DURATION_ALTERNATES':
				for i in v:
					values = (i[0].GetValue(), i[1].GetValue())
					if not values[0].strip() and values[1].strip():
						i[0].SetBackgroundColour('red')
						good = False
					elif values[0].strip() and not values[1].strip():
						i[1].SetBackgroundColour('red')
						good = False
					elif values[0].strip() and values[1].strip():
						good = self.CheckInput(i[0], minMaxInt = (0,100))
						good = self.CheckInput(i[1])

			elif k == 'MAXFORMANT_ALTERNATES':
				for i in v:
					values = (i[0].GetValue(), i[1].GetValue())
					if not values[0].strip() and values[1].strip():
						i[0].SetBackgroundColour('red')
						good = False
					elif values[0].strip() and not values[1].strip():
						i[1].SetBackgroundColour('red')
						good = False
					elif values[0].strip() and values[1].strip():
						good = self.CheckInput(i[0], needsInt = True)
						good = self.CheckInput(i[1])
			elif k in ['OTHER', 'PITCH', 'PRONUNCIATION', 'INDEX']: continue
			else:
				good = self.CheckInput(v, required = True)
		if good:
			if self.name.GetValue().strip() in self.options:
				wx.MessageDialog(self, 'A configuration setting with this name already exists').ShowModal()
				return
			self.WriteSettings()
			self.SetDefault(self.name.GetValue().strip())
			self.EndModal(wx.ID_OK)
		else:
			wx.MessageDialog(self, 'Invalid input\n(hover over an input box for help)').ShowModal()



	def AddAltVowelRow(self, e = None, button = None):
		## adds a new alt vowel row either when the '+' button is pressed or when loading a new configuration
		button = e.GetEventObject() if e else button
		if button == self.durAddButton:
			label = '%                 '  ## hacky spacer (grooooosssss)
			colName = 'DURATION_ALTERNATES'
			column = 0
			add = 0
			tooltipLabel = '% of the vowel duration at which the alternate F1/F2 values were measured'
		else:
			label = 'max formants    '
			colName = 'MAXFORMANT_ALTERNATES'
			column = 3
			add = 1
			tooltipLabel = 'the maximum number of formants setting when the alternate F1/F2 were measured'
		miniSizer = wx.BoxSizer(wx.HORIZONTAL)
		amount = wx.TextCtrl(self, size = (40,wx.DefaultSize[1]))
		amount.SetToolTip(wx.ToolTip(tooltipLabel))
		miniSizer.Add(amount)
		miniSizer.Add(wx.StaticText(self, label = label))
		tempTextCtrl = wx.TextCtrl(self)
		tempTextCtrl.SetToolTip(wx.ToolTip('Column name for:\nalternate F1/F2 values (as F1,F2)'))

		self.altSizer.Add(miniSizer, (self.rowNum[add],column)) 
		self.altSizer.Add(tempTextCtrl, (self.rowNum[add], column+1))

		self.rowNum[add] += 1	
		try:
			self.colNames[colName].append((amount , tempTextCtrl))
		except:
			self.colNames[colName] = [(amount , tempTextCtrl)]
		self.Layout()
		self.Fit()

	def CheckInput(self, textCtrl, required = True, needsInt = False, minMaxInt = None):
		## helper function when checking if the input of a field is good
		## returns True if good and False if bad 
		## also sets the background colour of the box to red if its bad 
		value = textCtrl.GetValue().strip()
		if not value:
			if required:
				textCtrl.SetBackgroundColour('red')
				return False
			else:
				textCtrl.SetBackgroundColour('white')
				return True
		if needsInt:
			try:
				test = int(value)
				textCtrl.SetBackgroundColour('white')
				return True
			except:
				textCtrl.SetBackgroundColour('red')
				return False
		if minMaxInt:
			try:
				test = int(value)
				if minMaxInt[0] <= test <= minMaxInt[1]:
					textCtrl.SetBackgroundColour('white')
					return True
				else:
					textCtrl.SetBackgroundColour('red')
					return False
			except:
				textCtrl.SetBackgroundColour('red')
				return False
		textCtrl.SetBackgroundColour('white')
		return True

class mainFrame(wx.Frame):
	## main window frame
	def __init__(self):
		wx.Frame.__init__(self, None, title = 'FVR (Formant Visualization and Remeasurement)')
		## lists to hold previous states for undo/redo buttons
		self.past = []
		self.future = []
		## read default alternate phonetic alphabet
		self.ReadAlternateVowelsFromFile()
		## define sizer and panels
		self.mainSizer = wx.BoxSizer(wx.VERTICAL)
		self.toolBarPanel = ToolBar(self)
		self.plotPanel = PlotPanel(self)
		self.phonPanel = PhonPanel(self)
		## layout panels
		self.mainSizer.Add(self.toolBarPanel, flag = wx.EXPAND)
		self.mainSizer.Add(self.plotPanel, 1, flag = wx.EXPAND)
		self.mainSizer.Add(self.phonPanel, flag = wx.EXPAND)

		self.SetSizer(self.mainSizer)
		## default Location of praat 
		self.Praat = '/Applications/Praat.app'

		## setup menu bar
		menubar = wx.MenuBar()
		fileMenu = wx.Menu()
		editMenu = wx.Menu()
		viewMenu = wx.Menu()
		helpMenu = wx.Menu()

		## init menu items 
		openItem = fileMenu.Append(wx.ID_OPEN)
		openRecentItem = fileMenu.Append(wx.ID_ANY, 'Open Most Recent')
		self.saveItem = fileMenu.Append(wx.ID_SAVE)
		saveAsItem = fileMenu.Append(wx.ID_ANY, 'Change Save Directory')
		findPraatItem = fileMenu.Append(wx.ID_ANY, 'Find Praat')
		configInputItem = fileMenu.Append(wx.ID_ANY, 'Configure Info Reader')
		configFave = fileMenu.Append(wx.ID_ANY, 'Configure FAVE output')
		closeItem = fileMenu.Append(wx.ID_EXIT, text = "&Exit")
		self.saveItem.Enable(False)

		self.undoItem = editMenu.Append(wx.ID_UNDO)
		self.redoItem = editMenu.Append(wx.ID_REDO)
		self.undoItem.Enable(False)
		self.redoItem.Enable(False)

		altPAItem = viewMenu.Append(wx.ID_ANY, 'Change Alternate Phonetic Alphabet')
		## add menus to the menubar
		menubar.Append(fileMenu, '&File')
		menubar.Append(editMenu, '&Edit')
		menubar.Append(viewMenu, '&View')
		menubar.Append(helpMenu, '&Help')
		self.SetMenuBar(menubar)
		## set min size of frame
		self.SetMinSize((self.GetEffectiveMinSize()[0], 400))
		self.SetSize((self.GetEffectiveMinSize()[0], 800))
		self.Layout()
		# bind menu events
		self.Bind(wx.EVT_MENU, self.OnOpen, openItem)
		self.Bind(wx.EVT_MENU, self.OnOpenRecent, openRecentItem)
		self.Bind(wx.EVT_MENU, self.OnFindPraat, findPraatItem)
		self.Bind(wx.EVT_MENU, self.toolBarPanel.saveButton.OnClick, self.saveItem)
		self.Bind(wx.EVT_MENU, self.OnClose, closeItem)
		self.Bind(wx.EVT_CLOSE, self.OnClose)
		self.Bind(wx.EVT_MENU, self.OnSaveTo, saveAsItem)
		self.Bind(wx.EVT_MENU, self.OnConfigInput, configInputItem)
		self.Bind(wx.EVT_MENU, self.OnFAVE, configFave)

		self.Bind(wx.EVT_MENU, self.toolBarPanel.undoRedoButtons.Undo, self.undoItem)
		self.Bind(wx.EVT_MENU, self.toolBarPanel.undoRedoButtons.Redo, self.redoItem)

		self.Bind(wx.EVT_MENU, self.OnNewPA, altPAItem)

		#create list for storing open files
		self.openFiles = []	

		# read default config file
		self.ReadConfig()
		self.Centre()
		self.Show(True)

	def ReadConfig(self):
		# read from the config file to get the info file headings
		start = False
		configDict = {}
		lines = []
		with open('config.txt','rU') as configF:
			for line in configF:
				if start:
					if line.strip():
						lines.append(line.split('\t'))
				elif line[:2] == '  ':
					start = True
		for cat, head in lines:
			for h in head.split('||'):
				try:
					configDict.update({h.strip().split('|')[1] : (cat, h.strip().split('|')[0])})
				except:
					if cat == 'delimiter':
						self.fileDelim = h.strip().decode('unicode-escape')
					elif cat == 'heading_row':
						self.fileHRow = int(h.strip())
					else:						
						configDict.update({h.strip() : cat})
		self.configDict = configDict ## returns {heading : category}

	def GetOtherLabel(self):
		## returns name of alternate phonetic alphabet
		return self.otherLabel


	def OnNewPA(self, e):
		## opens dialog to set a new phonetic alphabet
		otherPADialog = OtherVowelDialog(self)
		if otherPADialog.ShowModal() == wx.ID_OK:
			self.otherLabel, self.other = otherPADialog.GetAlphabet()
			self.phonPanel.RedrawOtherVowels()

	def ReadAlternateVowelsFromFile(self):
		## reads other_phon_alphabet.txt to set up alternate vowel buttons
		self.other = []
		self.otherLabel = ''
		with open('other_phon_alphabet.txt', 'r') as otherVowels:
			start = False
			for line in otherVowels:
				if line[:2] == '  ': 
					self.otherLabel = line.upper().strip()
					start = True
					continue
				if start:
					if line[0] == ' ': break
					self.other.append(tuple(line.strip().split()))

	def OnFAVE(self, e):
		## allows user to convert the *formant.txt files (output from FAVE-extract)
		## so that they are readable by FVR
		messageD = wx.MessageDialog(self, 'This will rewrite formant.txt output files from the FAVE-extract program\n(http://fave.ling.upenn.edu/index.html)\nso they can be processed using FVR\nContinue?')
		openD = wx.DirDialog(self, 'Select the folder containing the FAVE formant.txt files')
		saveD = wx.DirDialog(self, 'Select the folder to write the formatted formant.txt files')
		warningD = wx.MessageDialog(self, 'This will overwrite the FAVE formant.txt files\nContinue?')
		changeConfigD = wx.MessageDialog(self, 'Update Info Reader to read the newly rewritten FAVE formant.txt files', style = wx.YES_DEFAULT|wx.YES_NO|wx.CENTRE)
		if messageD.ShowModal() == wx.ID_OK:
			if openD.ShowModal() == wx.ID_OK:
				if saveD.ShowModal() == wx.ID_OK:
					openPath = openD.GetPath()
					savePath = saveD.GetPath()
					if openPath == savePath:
						if warningD.ShowModal() == wx.ID_OK:
							UpdateFAVE(openPath, savePath)
							if changeConfigD.ShowModal() == wx.YES:
								pass
					else:
						UpdateFAVE(openPath, savePath)
						if changeConfigD.ShowModal() == wx.YES:
								pass
	def OnConfigInput(self, e):
		## opens dialog so user can set new config settings (for reading in files)
		if ConfigInputDialog(self).ShowModal() == wx.ID_SAVE:
			self.ReadConfig()


	def OnClose(self, e):
		## asks to save progress before closing
		if self.plotPanel.changes and self.GetTopLevelParent().past:
			caption = 'Save changes before closing?'
			closeDialog = wx.MessageDialog(self,caption, style=wx.YES_NO|wx.CANCEL)
			answer = closeDialog.ShowModal()
			if answer == wx.ID_YES:
				self.toolBarPanel.saveButton.OnClick(None)
			elif answer == wx.ID_CANCEL:
				return
		self.Destroy()

	def OnSaveTo(self, e):
		## allows user to change the directory the files will be saved in 
		saveDialog = wx.DirDialog(self, 'Save files to this directory...\nWARNING:\nIf the original file is in the selected\ndirectory, the original will be overwritten') ## save the previous saveDir in a file 
		if saveDialog.ShowModal() == wx.ID_OK:
			self.saveDir = saveDialog.GetPath()

	def OnFindPraat(self, e):
		## lets user change the path to Praat
		praatDialog = wx.FileDialog(self, message = 'Find location of Praat', style = wx.FD_OPEN, wildcard = ".app")
		if praatDialog.ShowModal() == wx.ID_OK:
			self.Praat = praatDialog.GetPath()
			
	def OnOpenRecent(self, e):
		## opens most recenlty opened files 
		wavFiles = []
		infoFiles = []
		with open('recent_files.txt', 'r') as recentF:
			for line in recentF:
				files = line.strip('\n').split('\t')
				wavFiles.append(files[0])
				infoFiles.append(files[1])
		self.saveDir = dirname(infoFiles[0])
		self.infoDir = dirname(infoFiles[0])
		newFiles = [(w,i) for w,i in self.GetFiles(wavFiles, infoFiles) if (w,i) not in self.openFiles]
		self.openFiles = newFiles+self.openFiles
		self.plotPanel.CreateVowelsFromFiles(newFiles)		


	def OnOpen(self, e):
		## open wav and .csv/.txt files to read vowels from
		wavDialog = wx.FileDialog(self, message = 'Select .wav files or directory', style = wx.FD_OPEN|wx.FD_MULTIPLE,
									wildcard = "WAV files (*.wav)|*.wav")
		if wavDialog.ShowModal() == wx.ID_OK:
			infoDialog = wx.FileDialog(self, message = 'Select vowel info files', style = wx.FD_OPEN|wx.FD_MULTIPLE,
									wildcard = "Text and CSV files (*.txt,*.csv)|*.txt;*.csv")
			if infoDialog.ShowModal() == wx.ID_OK:
				wavFiles = wavDialog.GetPaths()
				infoFiles = infoDialog.GetPaths()
				self.saveDir = dirname(infoFiles[0])
				self.infoDir = dirname(infoFiles[0])
				newFiles = [(w,i) for w,i in self.GetFiles(wavFiles, infoFiles) if (w,i) not in self.openFiles]
				self.openFiles = newFiles+self.openFiles
				self.LogRecentlyOpenedFiles()
				self.plotPanel.CreateVowelsFromFiles(newFiles)

	def LogRecentlyOpenedFiles(self):
		## write recently opened files (paths) to recent_files.txt 
		with open('recent_files.txt', 'w') as recentF:
			for wavFile, infoFile in self.openFiles:
				recentF.write(wavFile+'\t'+infoFile+'\n')


	def GetFiles(self, wavFiles, infoFiles):
		# get all relevant files and pair them together
		# as (wav file, formant.txt file)
		files = []
		# if looking in directories
		for w in wavFiles:
			for i in infoFiles:
				if basename(w.replace('.wav','')) in basename(i):
					files += [(w,i)]
		if not files:
			message = 'FVR was unable to pair .wav and vowel info files\nPlease ensure that the name of the .wav file is contained in the vowel info file:\n\nEx:\tspeaker_300.wav pairs with speaker_300.txt or old_speaker_300_A.csv but not with 300.txt'
			
			errorDialog = wx.MessageDialog(self, style=wx.OK, message = message)
			errorDialog.ShowModal()

		return files

if __name__ == "__main__":
	## Where it all begins
	app = wx.App(False)
	frame = mainFrame()
	app.MainLoop()
