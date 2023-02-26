BIG cty.dat was released on 13 July 2022.

   This is a special version of CTY.DAT which is more tailored to everyday
   logging. For more information on what CTY.DAT is, go HERE

   Version History

   This version of CTY.DAT has callsign data starting with 1 January 2000.
   This is useful for people who are using contest logging software to log
   their everyday QSOs, and want somewhat accurate country tracking. Here
   are the features of this file:
    1. Exception callsigns go back to the starting date shown above. If a
       callsign was used multiple times, then only the most recent entity
       is used. For example, TO5M was used from Martinique (FM) in 1993,
       St. Pierre & Miquelon (FP) in 1995, and Reunion (FR) in 2004. Thus,
       if you log TO5M using this file, you will get Reunion (FR)
    2. Prefixes do not go back, they are current as of the day the file
       was released. For example, Montenegro (4O) was added to the DXCC
       list effective 28 June 2006. If you try to log a QSO with 4O1T in
       Yugoslavia from 2003, it will come up as Montenegro, because that’s
       the current entity associated with the 4O prefix. Here is a list of
       known problems.
    3. This is a complete file, meaning all prefixes that require CQ
       and/or ITU zone overrides are listed. This is primarily for BY, K,
       UA9, VE and VK – these entities all span multiple CQ zones.
       Remember that the normal CTY.DAT has only a subset of these
       prefixes; many have been implemented in software and therefore
       don’t need to be listed.
    4. Some software like CT by K1EA doesn’t save the country information
       in the log with the QSOs. Instead, the country for each QSO is
       determined when the program is started, based on whatever country
       file is in use. Thus, it may not be possible to “fix” a QSO that is
       associated with the wrong country. You could use the override
       method, like “FO8XYZ=FO0” to assign it to Clipperton Island.
       However, if/when you over-write your country file with a new one,
       those customizations will be lost. One known case of this problem
       is a certain well-known IARU HQ station that uses the same callsign
       from different DXCC countries, on different bands, at the same
       time. It’s very hard to get these cases right.
    5. This file comes in only one format: using ‘=’ to distinguish full
       callsigns from prefixes.
     __________________________________________________________________

Installation Instructions

   The instructions for installing the CTY.DAT file are specific to each
   logging program. However, the instructions for installing this file are
   the same as the normal contest country files, so start HERE. Follow the
   written instructions on that page, but don’t download the file from
   those links.

   Here are some logging experiments to try to see if the larger file is
   installed in the right place, and is working:
    1. VERSION – should match the VERSION entity in the revision history
    2. OR4TN – should be Antarctica (not Belgium)
    3. MR6TMS – should be Scotland (not England)
    4. LW7DQQ/Y – should be Argentina in ITU Zone 16
    5. UI9XA – should be European Russia (not Asiatic)
    6. ZS85SARL – should be South Africa (not Marion Island)
     __________________________________________________________________

Compatibility

   Because of its size, this file may cause problems with your logging
   software. Here are some programs that are known to work:

   CT
          CT 9.92 (DOS) and CT 10.04 (Windows) both work. Once can
          therefore assume that CT 9.92 (Windows) and CT 10.x (DOS) also
          work. It’s unknown how old a CT9 version can be and still work.

   fldigi
          version 3.2.38 (Linux)

   KLog
          version 0.9.0 and later (Linux, Windows and macOS)

   LM
          DL8WAA reports no problems.

   MixW
          version 3.1.1h and later

   Xlog
          version 2.0.5 (Linux)
     __________________________________________________________________

Areas for Improvement

   Here are some changes that may be coming – stay tuned for details!
    1. The file contains all possible prefix mappings to determine the
       correct CQ and ITU zones. If people are only tracking countries,
       this may not be necessary, and would substantially reduce the
       number of prefixes in the file.

