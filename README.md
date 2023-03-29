
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

  1. Start WSJT-X
  2. Go to the directory FT8Commander
  3. Copy the `ft8ctrl.yaml.sample` into `ft8ctrl.yaml`
  4. Edit to the configuration file and enter your information
  5, Start the python program `./ft8ctrl.py`
  6. Watch WSJT-X making contacts.

> This program runs on MacOS and Linux.

## Misc

The following AppleScript example will automatically click on the Logging window.
** Note: Another application might steal the focus from the logging window, and the OK button might not be pressed on time. **

```
set bundleId to "org.k1jt.wsjtx"

tell application id bundleId to activate

tell application "System Events"
	repeat
		tell application process "WSJT-X"
			set winList to every window
		end tell
		repeat with win in winList
			set theTitle to name of win
			if theTitle contains "Log QSO" then
				tell application process "WSJT-X"
					click button "Ok" of group 1 of win
				end tell
				say "Contact Logged"
			end if
		end repeat
		delay 2
	end repeat
end tell
```

```
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

[^1]: Signal To Noize Ratio
