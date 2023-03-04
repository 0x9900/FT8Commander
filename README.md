
# FT8Commander

> This is an experimental piece of code. Don't forget to run `git pull` often.
> This code only works with version of WSJT-X 2.5 and above

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
  4. Edit to configuration file and enter your information
  5, Start the python program `./ft8ctrl.py`
  6. Watch WSJT-X making contacts.

> As is, this program runs on MacOS and Linux.

[^1]: Signal To Noize Ratio
