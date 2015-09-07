![icon](icons/fvr.icns) FVR  
===========================
***Formant Visualization and Remeasurement***

(pronounced [\[fivɹ̩\]](http://www.imdb.com/title/tt0076666/))

## **Description**
Plotmish is a python-based formant remeasurement tool. It can be used to correct errors made by automatic formant measurements programs and to annotate the changes.

Plotmish graphically displays vowels based on the first two formant values for easy identification of outliers. Outliers can then be remeasured automatically based on either time or maximum formant values or remeasured manually in Praat.

Plotmish also offers several filtering and vowel identification options that are outlined below.

## **Author and Acknowledgments**

**Author** Misha Schwartz

Thanks to Morgan Sonderegger and everyone at [MLML](http://mlmlab.org/)

Code for `zoomIn.Praat` was adapted from `PlotnikButton.praat` by Ingrid Rosenfelder
(available with the [Plotnik 10.3](http://www.ling.upenn.edu/~wlabov/Plotnik.html) release)

The [sendpraat](http://www.fon.hum.uva.nl/praat/sendpraat.html) binaries are from Paul Boersma

The first version of this software was (somewhat narcissistically) called [Plotmish](http://github.com/mlml/plotmish) (though this one is much better).

Plotmish is inspired by [Plotnik](http://www.ling.upenn.edu/~wlabov/Plotnik.html)

## **Requirements**

[Python](https://www.python.org/download/releases/2.7) (preferably version 2.7)

[wxPython](http://www.wxpython.org/download.php) (for best results use [version 3.0 for cocoa](http://downloads.sourceforge.net/wxpython/wxPython3.0-osx-3.0.2.0-cocoa-py2.7.dmg))

[Praat](http://www.fon.hum.uva.nl/praat/) 

[numpy](http://www.numpy.org/)

Currently for OSX only 

# **Getting started**

###On the command line:

    cd to FVR/
	python FVR.py

###Open files:

FVR requires a csv or txt file containing the vowel information AND a wav file that corresponds with the info file (corresponding txt/csv files should contain the name of the wav file ie. ABC_info.txt and ABC.wav)

* Open files: `File > Open...` You will be prompted to choose a directory containing the csv/txt files and another containing the wav files (FVR will match them automatically)
* Open recent files: File > Open Most Recent

####Troubleshooting file opening:

If FVR isn't opening your files...

* check your corresponding wav files and txt/csv files are named properly (see above)
* check the info reader is configured for your txt/csv files `File > Configure Info Reader` This will open up a window where you can describe your txt/csv files (hover over each input box for hints on what values they take)
* **IF YOUR FILE IS A FORMANT.TXT FILE FROM FAVE-EXTRACT:**
    * FVR cannot read these files directly but can convert them easily
    * Go to `File > Configure FAVE output`
    * Follow the prompts

####Recommended FAVE-extract settings:

If you are using [FAVE-extract](http://fave.ling.upenn.edu/extractFormants.html) to measure your vowels the following settings are recommended:

    speechSoftware=praat
    outputFormat=text
    formantPredictionMethod=mahalanobis
    candidates=T

A description of these settings can be found on the [FAVE site](http://fave.ling.upenn.edu/downloads/EFoptions.html) or in the FAVE-extract ReadMe.

###Displaying Vowels      

The bottom of the main FVR window displays two phonetic alphabets (CMU and another one)
as buttons:

* Click any of the buttons to show the vowels with the corresponding label on the plot (you can toggle them off and on)
* The larger buttons on top will toggle all of the smaller buttons below them
* The middle button has two settings union (U) and intersect (∩): this 
* Will either display the union or intersect of the set of pressed vowel buttons on either side

###Filtering Vowels

At the bottom right of the main FVR window you can set filter options:

* Filter by word: select a word from the dropdown list
* Filter by duration: set a minimum and maximum duration (in ms) to display
* When you have finished setting filter values press the **FILTER** button to filter out the vowels which do not correspond to the filter values
* You can toggle the filter by pressing the **FILTER** button again.


###Remeasuring

To remeasure a vowel, select the remeasurement mode (see below) and click the vowel
on the plot.  Each mode does the following

* PRAAT: 	
    * Opens up Praat.app when a vowel is clicked
	* To remeasure the vowel place the red line at the desired position in the vowel and select `Query > Log 1` (or `F12`)
	* This will draw a white box to the plot corresponding to the new measurement

* FORMANTS: 
    * displays alternate measurements for the selected vowel depending on the maximum formant setting when the vowel was measured

* % OF DURATION: 	
    * displays alternate measurements for the selected vowel taken at a different point in the vowel's duration (ex. at 20%, 50% etc.)

The original vowel measurement will appear on the plot at a black box and the alternate measurements will appear as a white box.  Select one by clicking or keep the original measurement by hitting the CANCEL button.


###ToolBar buttons

The toolbar buttons are located at the top of the main FVR window:

**PLAY** 	

* When on (green), you can left click a vowel on the plot to hear it

**STANDARD DEVIATION:**

* Show or hide an ellipse which shows 1,2 or 3 standard deviations from the mean for all vowels on the plot

**ZOOM**
	
* Clicking the zoom (+) will allow you to zoom into an area on the plot either by double clicking or drawing a box (describing the area to zoom into)
* Cancel the zoom by clicking the button again 
* If the button is showing (-) the plot will zoom out to its full dimensions

**REMEASURE USING**
	
* Set the type of remeasurement you want to do (see Remeasuring above)

**CANCEL**
	
* Cancel a remeasurement (only is on when a remeasurement is taking place)

**SAVE**
	
* Save all remeasurement and whether a vowel was removed from the plot this will either overwrite the old files or you can specify a new location to write the files to using File > Change Save Directory

**UNDO**
	
* This will undo the most recent vowel remeasurement or removal

**REDO**
	
* This will redo the last undid action

**REMOVE FROM PLOT**
	
* Clicking this will let you remove vowel from the plot either by clicking them or by drawing a box to select multiple at once
* The smaller button lets you add a note when removing vowels:
    * good = "this vowel is measured properly"
    * bad = "this vowel is measured improperly (and it was removed instead of remeasuring it)
    * note = add a note about the removed vowels
		 	

###Other Things

* Right click a vowel on the plot to display information about it

* The CMU phonetic alphabet at the bottom of the panel is permanent but you can select a new alternate phonetic alphabet with `View > Change Alternate Phonetic Alphabet`

* This will open a window which will allow you to either define your own phonetic alphabet (by entering the vowel labels in the grid) or load a preset one.

* To load a preset alphabet click *Open*.  
    * Current Presets are CELEX and IPA

##License


The MIT License (MIT)

Copyright (c) 2015 Montreal Language Modeling Lab (McGill University) 

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
