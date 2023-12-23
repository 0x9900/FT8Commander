
# FT8Commander

> This is an experimental piece of code. Don't forget to run `git pull` often.
> This code only works with the version of WSJT-X 2.5 and above.

### WSJT-X FT8 Automation

FT8Commander is an experimental project for ham radio operators who
want automatic control of their FT8 contacts. This program controls
WSJT-X to optimize contacts' chances during a contest or DX (make as
many QSO as possible). After a receive sequence, the program uses
information such as the SNR[^1] and the distance of the calling
stations to calculate which one has the most chances of completing the
QSO.

## Usage:
  1. Install the **DXEntity** package `pip install DXEntity`
  2. Start WSJT-X
  3. Go to the directory FT8Commander
  4. Copy the `ft8ctrl.yaml.sample` into `ft8ctrl.yaml`
  5. Edit to the configuration file and enter your information
  6, Start the python program `./ft8ctrl.py`
  7. Watch WSJT-X making contacts.

> This program runs on MacOS and Linux.

## Misc

### Logging

The following AppleScript example will automatically click on the Logging window.
** Note: Another application might steal the focus from the logging window, and the OK button might not be pressed on time. **

```applescript
tell application "wsjtx" to activate
say "w s j t x is active"

tell application "System Events"
	repeat
		try
			tell application process "WSJT-X"
				set winList to every window
			end tell
			repeat with win in winList
				tell application "System Events"
					get entire contents of win
				end tell
				set theTitle to name of win
				if theTitle contains "Log QSO" then
					tell application process "WSJT-X"
						click button "Ok" of group 1 of win
						say "Logged"
					end tell
				end if
			end repeat
		on error errMsg number errorNumber
			log errMsg
			say "Error"
		end try
		delay 3
	end repeat
end tell
```

### Calling CQ

The following AppleScript calls CQ and logs any contact.<br>
_Courtesy of my friend JC (W6IPA)_

The original version can be found on [gist][1].

```applescript
set bundleId to "org.k1jt.wsjtx"
tell application id bundleId to activate

tell application "System Events"
	repeat
		tell application process "WSJT-X"
			set winList to every window
			set frontmost to true
		end tell
		repeat with win in winList
			set theTitle to name of win
			if theTitle contains "Log QSO" then
				tell application process "WSJT-X"
					click button "Ok" of group 1 of win
				end tell
				say "Contact Logged"
			else if theTitle starts with "WSJT-X" and theTitle does not contain "Wide Graph" then
				tell application process "WSJT-X"
					set chkBox to value of checkbox "Enable Tx" of win as boolean
				end tell

				if not chkBox then
					delay 30
					perform action "AXRaise" of win

					tell application process "WSJT-X"
						click button "Set Rx frequency to Tx Frequency" of group 1 of win
					end tell

					say "Calling CQ"
					tell application "System Events" to key code 122
				end if
			end if
			delay 1
		end repeat
		delay 5
	end repeat
end tell
```

[^1]: Signal To Noise Ratio

[1]: https://gist.github.com/jc-m/f4ae181cdbac7adc8621e93a0c26c8e5
