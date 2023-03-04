

# FT8Commander

> This is an experimental piece of code. Don't forget to run `git pull` often.
> This code only works with the version of WSJT-X 2.5 and above

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
  3. Copy the `ft8ctrl.yaml.sample` into ft8ctrl.yaml`
  4. Edit to the configuration file and enter your information
  5, Start the python program `./ft8ctrl.py`
  6. Watch WSJT-X making contacts.

> This program runs on MacOS and Linux.

## Misc

This following AppleScrip will automatically click on the Logging window.

```
tell application "wsjtx" to activate

tell application "System Events"
	repeat
		tell application process "WSJT-X"
			set winNameList to name of every window
		end tell
		repeat with winName in winNameList
			if winName contains "Log QSO" then
				tell application "wsjtx" to activate
				keystroke return
				say "New Contact Logged"
				delay 15
			end if
		end repeat
		delay 2
	end repeat
end tell
```


[^1]: Signal To Noize Ratio
