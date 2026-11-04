# Games still to test (363 of 651)

These are the Steam games that still need testing on Playden. The list includes only Windows games with full or partial controller support, and it's in the order the tester will run them.

**Not on this list**

- Games that someone has already tested, either in a test report on [Playden's issue tracker](https://github.com/leolobato/playden-ps5/issues) or on its [compatibility list](https://github.com/leolobato/playden-ps5/blob/main/COMPATIBILITY.md).
- Multiplayer games with anti-cheat (Easy Anti-Cheat, BattlEye, VAC and similar). Their online play doesn't work under Playden. Games with a single-player mode stay on the list when their anti-cheat only applies online (VAC, FairFight, PunkBuster).

**Order**

Games are sorted by how much disk space they need, smallest first, so the most games get tested in the least time. The size is what the game's Steam store page asks for; games whose page doesn't say come last. Games of the same size are sorted by the rest of this section.

Games with full controller support come before games with partial support, whose menus or some parts may need a mouse or keyboard. Each of those two groups is sorted first by its games' [ProtonDB](https://www.protondb.com) rating, which says how well they run on Linux through Proton. Platinum games come first, then Gold, Silver, Bronze and Borked. Games with too few reports for a rating (Pending) or no reports at all come last.

Within each rating:

1. Games that never came out on a console come first.
2. Next come games that were also released on Xbox or Nintendo consoles, but not on a PlayStation.
3. Then games released on older PlayStations (PS1 to PS3, PSP, Vita).
4. Games with a PS4 or PS5 version come last, since they already play on the PS5 without Playden.

Within each of those groups, games that support the DualSense controller come first, then games that support the DualShock, then the rest.

**Columns**

- **Size** is the disk space the game's Steam store page asks for.
- **Year** is the first release on any platform.
- **Steam app** is the game's ID on the Steam store: `https://store.steampowered.com/app/<ID>`.
- **DualSense** says whether Steam lists DualSense support.
- **Console versions** comes from Wikidata. A dash means none were found.
- **ProtonDB** is the game's rating on ProtonDB. A dash means ProtonDB has no reports for it.
- **Note** gives the controller support level, plus anything to watch for when retesting.

| # | Game | Size | Year | Steam app | DualSense | Console versions | ProtonDB | Note |
|---|---|---|---|---|---|---|---|---|
| 1 | Retro City Rampage™ DX | 40 MB | 2012 | 204630 | – | PlayStation 4, PlayStation 3, PlayStation Vita, Nintendo Switch, Wii | Gold | Full controller support |
| 2 | Home | 50 MB | 2012 | 215670 | DualShock only | PlayStation 4, PlayStation Vita, Nintendo Switch | Platinum | Full controller support; retest: Home: no download folder 215670 within 120 s of Install |
| 3 | Shotgun King: The Final Checkmate | 80 MB | 2022 | 1972440 | Yes | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S, Nintendo Switch | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 4 | Windowkill | 80 MB | 2024 | 2726450 | Yes | – | Gold | Full controller support |
| 5 | Offspring Fling! | 95 MB | 2012 | 211360 | – | – | Gold | Partial controller support |
| 6 | PAC-MAN 256 | 100 MB | 2015 | 455400 | – | PlayStation 4 | Platinum | Full controller support |
| 7 | BIT.TRIP RUNNER | 100 MB | 2010 | 63710 | – | – | Gold | Full controller support |
| 8 | Bongo Cat | 100 MB | 2025 | 3419430 | Yes | – | Bronze | Partial controller support |
| 9 | Risk of Rain (2013) | 130 MB | 2013 | 248820 | – | PlayStation 4, PlayStation Vita, Nintendo Switch | Gold | Partial controller support |
| 10 | Race The Sun | 150 MB | 2013 | 253030 | – | PlayStation 4, PlayStation Vita, Wii U | Platinum | Full controller support |
| 11 | Tiny Barbarian DX | 150 MB | 2013 | 253350 | – | Nintendo Switch | Pending | Full controller support |
| 12 | STAR WARS™: Rogue Squadron 3D | 168 MB | 1998 | 455910 | – | Nintendo 64 | Silver | Partial controller support |
| 13 | Bridge Constructor Portal | 200 MB | 2017 | 684410 | – | PlayStation 4, Xbox One, Nintendo Switch | Platinum | Full controller support |
| 14 | Spelunky | 200 MB | 2008 | 239350 | – | PlayStation 4, PlayStation 3, PlayStation Vita, Xbox 360, Nintendo Switch | Platinum | Full controller support |
| 15 | Iron Lung | 200 MB | 2022 | 1846170 | – | Nintendo Switch | Platinum | Partial controller support |
| 16 | Mutant Mudds Deluxe | 200 MB | 2012 | 247370 | – | PlayStation 4, PlayStation 3, PlayStation Vita, Nintendo 3DS | Platinum | Partial controller support |
| 17 | The Rainsdowne Players | 200 MB | 2018 | 802930 | – | Nintendo Switch | – | Partial controller support |
| 18 | STAR WARS™ - X-Wing Special Edition | 216 MB | 1993 | 354430 | – | – | Gold | Partial controller support |
| 19 | Before the Echo | 250 MB | 2011 | 200910 | – | Xbox 360 | Pending | Full controller support |
| 20 | Beat Hazard | 256 MB | 2010 | 49600 | – | – | Gold | Full controller support |
| 21 | Savant - Ascent REMIX | 300 MB | 2023 | 2279330 | – | Nintendo Switch | Gold | Full controller support |
| 22 | Retro/Grade | 300 MB | 2012 | 222660 | – | PlayStation 3 | Gold | Full controller support |
| 23 | Full Bore | 300 MB | 2014 | 264060 | – | – | Pending | Full controller support |
| 24 | Turbo Dismount™ | 300 MB | 2014 | 263760 | – | – | Platinum | Partial controller support |
| 25 | Hammerwatch | 300 MB | 2013 | 239070 | – | Nintendo Switch | Platinum | Partial controller support |
| 26 | Heavy Bullets | 300 MB | 2014 | 297120 | – | – | Gold | Partial controller support |
| 27 | Paranautical Activity: Deluxe Atonement Edition | 300 MB | 2014 | 250580 | – | PlayStation 4, Nintendo Switch | Pending | Partial controller support |
| 28 | SteamWorld Dig 2 | 350 MB | 2017 | 571310 | – | PlayStation 4, Nintendo Switch, Nintendo 3DS | Platinum | Full controller support |
| 29 | Crawl | 400 MB | 2014 | 293780 | Yes | PlayStation 4, Xbox One, Nintendo Switch | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 30 | The Bridge | 400 MB | 2013 | 204240 | – | PlayStation 4, Nintendo Switch, Wii U | Silver | Full controller support |
| 31 | Dustforce DX | 400 MB | 2012 | 65300 | – | PlayStation 3, PlayStation Vita, Xbox 360 | Platinum | Partial controller support |
| 32 | STAR WARS™ Jedi Knight - Mysteries of the Sith™ | 400 MB | 1998 | 32390 | – | – | Gold | Partial controller support |
| 33 | STAR WARS™: TIE Fighter Special Edition | 406 MB | 1994 | 355250 | – | – | Gold | Partial controller support |
| 34 | STAR WARS™ X-Wing vs TIE Fighter - Balance of Power Campaigns™ | 487 MB | 1997 | 361690 | – | – | Gold | Partial controller support |
| 35 | Frog Detective 2: The Case of the Invisible Wizard | 500 MB | 2019 | 1047220 | Yes | PlayStation 4, PlayStation, Xbox One, Xbox Series X/S, Nintendo Switch | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 36 | Frog Detective 3: Corruption at Cowboy County | 500 MB | 2022 | 1171320 | Yes | PlayStation 4, PlayStation, Xbox One, Xbox Series X/S, Nintendo Switch | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 37 | Don't Starve | 500 MB | 2013 | 219740 | – | PlayStation 4, PlayStation 3, PlayStation Vita, Xbox One, Nintendo Switch, Wii U | Platinum | Full controller support |
| 38 | Exit the Gungeon | 500 MB | 2019 | 1209490 | – | PlayStation 4, Nintendo Switch | Platinum | Full controller support |
| 39 | Iconoclasts | 500 MB | 2018 | 393520 | – | PlayStation 4, PlayStation Vita, Nintendo Switch | Platinum | Full controller support |
| 40 | Type:Rider | 500 MB | 2013 | 258890 | – | PlayStation 4, PlayStation Vita, Nintendo Switch | Gold | Full controller support |
| 41 | Airscape: The Fall of Gravity | 500 MB | 2015 | 317250 | – | – | Pending | Full controller support; retest: could not select the library tab |
| 42 | Cybergeist | 500 MB | 2020 | 1457820 | – | – | – | Full controller support |
| 43 | Ghostly Matter | 500 MB | 2018 | 800240 | – | – | Pending | Full controller support |
| 44 | Snakenpon | 500 MB | 2020 | 1452300 | – | – | – | Full controller support |
| 45 | Buckshot Roulette | 500 MB | 2023 | 2835570 | Yes | Xbox One, Xbox Series X/S | Platinum | Partial controller support |
| 46 | Plague Inc: Evolved | 500 MB | 2014 | 246620 | – | PlayStation 4, Xbox One, Nintendo Switch | Platinum | Partial controller support |
| 47 | Element4l | 500 MB | 2013 | 235820 | – | PlayStation Vita | Pending | Partial controller support |
| 48 | Rocketbirds: Hardboiled Chicken | 501 MB | 2011 | 215510 | – | PlayStation 3, PlayStation Vita | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 49 | Castle Crashers | 512 MB | 2008 | 204360 | Yes | PlayStation 4, PlayStation 3, PlayStation Portable, Xbox One, Xbox 360, Nintendo Switch | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 50 | CloverPit | 512 MB | 2025 | 3314790 | DualShock only | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S, Nintendo Switch, Nintendo Switch 2 | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 51 | Haos | 512 MB | 2021 | 1681380 | – | – | – | Full controller support |
| 52 | Tangle Tower | 550 MB | 2019 | 359510 | Yes | PlayStation 4, Nintendo Switch | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 53 | Hotline Miami 2: Wrong Number | 600 MB | 2015 | 274170 | – | PlayStation 4, PlayStation 3, PlayStation Vita | Platinum | Full controller support |
| 54 | OTXO | 600 MB | 2023 | 1608640 | – | PlayStation 4, PlayStation 5, Nintendo Switch | Platinum | Full controller support |
| 55 | Talisman: Digital Classic Edition | 600 MB | 2014 | 247000 | – | PlayStation 4, Xbox One, Xbox Series X/S, Nintendo Switch | Platinum | Full controller support |
| 56 | Orborun | 600 MB | 2014 | 308580 | – | – | Pending | Full controller support |
| 57 | Lost in Vivo | 600 MB | 2018 | 963710 | – | – | Gold | Partial controller support |
| 58 | STAR WARS™ Starfighter™ | 620 MB | 2001 | 32350 | – | PlayStation 2, Xbox | Gold | Partial controller support |
| 59 | STARWHAL | 700 MB | 2014 | 263020 | – | PlayStation 4, PlayStation 3, Xbox One, Wii U | Pending | Full controller support |
| 60 | STAR WARS™ Jedi Knight: Dark Forces II | 700 MB | 1997 | 32380 | – | – | Gold | Partial controller support |
| 61 | Dungeon of the ENDLESS™ | 700 MB | 2014 | 249050 | – | PlayStation 4, Nintendo Switch | Gold | Partial controller support |
| 62 | Grow Big (or Go Home) | 750 MB | 2020 | 1476080 | – | – | – | Full controller support |
| 63 | FAITH | 800 MB | 2022 | 1179080 | – | PlayStation 5, Xbox Series X/S, Nintendo Switch | Platinum | Full controller support |
| 64 | Guacamelee! Super Turbo Championship Edition | 800 MB | 2013 | 275390 | – | PlayStation 4, PlayStation 3, PlayStation Vita, Xbox One, Xbox 360, Nintendo Switch, Wii U | Platinum | Full controller support |
| 65 | STAR WARS™ Jedi Knight II - Jedi Outcast™ | 800 MB | 2002 | 6030 | – | PlayStation 4, Xbox, GameCube | Gold | Partial controller support |
| 66 | Ghosts of Hollow Creek | 800 MB | 2022 | 1910180 | – | – | – | Partial controller support |
| 67 | Noctropolis | 800 MB | 1994 | 377070 | – | – | Pending | Partial controller support |
| 68 | Untitled Goose Game | 830 MB | 2019 | 837470 | DualShock only | PlayStation 4, PlayStation 3, Xbox One, Nintendo Switch | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 69 | STAR WARS™ - X-Wing Alliance™ | 927 MB | 1999 | 361670 | – | – | Gold | Partial controller support |
| 70 | Wizard of Legend | 1 GB | 2018 | 445980 | Yes | PlayStation 4, Nintendo Switch | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 71 | Atomicrops | 1 GB | 2019 | 757320 | – | PlayStation 4, Xbox One, Xbox Series X/S, Nintendo Switch | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 72 | Dead Island Retro Revenge | 1 GB | 2016 | 337360 | – | PlayStation 4 | Platinum | Full controller support |
| 73 | Keep Talking and Nobody Explodes | 1 GB | 2015 | 341800 | – | PlayStation 4, Xbox One, Nintendo Switch | Platinum | Full controller support |
| 74 | The Jackbox Party Pack 4 | 1 GB | 2017 | 610180 | – | PlayStation 4, Nintendo Switch | Platinum | Full controller support |
| 75 | Pummel Party | 1 GB | 2018 | 880940 | – | – | Gold | Full controller support |
| 76 | METAL GEAR SOLID: MASTER COLLECTION Vol.1 BONUS CONTENT | 1 GB | 2023 | 2306740 | Yes | PlayStation 4, PlayStation 5 | Gold | Full controller support |
| 77 | The Swapper | 1 GB | 2013 | 231160 | – | PlayStation 4, PlayStation 3, PlayStation Vita, Wii U | Gold | Full controller support |
| 78 | Beatbuddy: Tale of the Guardians | 1 GB | 2013 | 231040 | – | – | Pending | Full controller support |
| 79 | Maximum Action | 1 GB | 2018 | 853770 | Yes | – | Platinum | Partial controller support |
| 80 | FINAL FANTASY | 1 GB | 2021 | 1173770 | – | – | Platinum | Partial controller support |
| 81 | FINAL FANTASY II | 1 GB | 2021 | 1173780 | – | – | Platinum | Partial controller support |
| 82 | FINAL FANTASY V | 1 GB | 2021 | 1173810 | – | – | Platinum | Partial controller support |
| 83 | Gear Up | 1 GB | 2015 | 214420 | – | – | Platinum | Partial controller support |
| 84 | The Bard's Tale Trilogy | 1 GB | 2018 | 843260 | – | – | Platinum | Partial controller support |
| 85 | Tokyo School Life | 1 GB | 2015 | 320760 | – | Nintendo Switch | Platinum | Partial controller support |
| 86 | FINAL FANTASY III | 1 GB | 2021 | 1173790 | – | PlayStation 4, Nintendo Switch | Platinum | Partial controller support |
| 87 | FINAL FANTASY VI | 1 GB | 2022 | 1173820 | – | PlayStation 4, Xbox Series X/S, Nintendo Switch | Platinum | Partial controller support |
| 88 | Now you can't see me | 1 GB | 2021 | 1644200 | – | – | – | Partial controller support |
| 89 | Q.U.B.E: Director's Cut | 1.07 GB | 2011 | 239430 | – | PlayStation 4, PlayStation 3, PlayStation Vita, Xbox One, Wii U | Platinum | Partial controller support |
| 90 | Murder House | 1.24 GB | 2020 | 1064460 | – | PlayStation 4, Xbox One, Nintendo Switch | Platinum | Full controller support |
| 91 | STAR WARS™ Jedi Knight - Jedi Academy™ | 1.3 GB | 2003 | 6020 | – | PlayStation 4, Xbox, Nintendo Switch | Gold | Partial controller support |
| 92 | STAR WARS™: Rebel Assault I + II | 1.33 GB | 1996 | 456540 | – | – | Silver | Partial controller support |
| 93 | Noita | 1.56 GB | 2019 | 881100 | – | – | Platinum | Partial controller support |
| 94 | Screencheat | 2 GB | 2014 | 301970 | DualShock only | PlayStation 4, Xbox One | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 95 | Goat Simulator | 2 GB | 2014 | 265930 | – | PlayStation 4, Xbox One, Nintendo Switch | Platinum | Full controller support |
| 96 | Kill It With Fire | 2 GB | 2020 | 1179210 | – | PlayStation 4, Xbox One, Xbox Series X/S, Nintendo Switch | Platinum | Full controller support |
| 97 | The Case of the Golden Idol | 2 GB | 2022 | 1677770 | – | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S, Nintendo Switch | Platinum | Full controller support |
| 98 | The Walking Dead: Season Two | 2 GB | 2013 | 261030 | – | PlayStation 4, PlayStation 3, PlayStation Vita, Xbox One, Xbox 360, Nintendo Switch | Platinum | Full controller support |
| 99 | Shashingo: Learn Japanese with Photography | 2 GB | 2024 | 1632490 | – | Nintendo Switch | Gold | Full controller support |
| 100 | Half Minute Hero: Super Mega Neo Climax Ultimate Boy | 2 GB | 2009 | 214830 | – | PlayStation Portable | Gold | Full controller support |
| 101 | Jazzpunk: Director's Cut | 2 GB | 2014 | 250260 | – | PlayStation 4 | Gold | Full controller support |
| 102 | KickBeat Steam Edition | 2 GB | 2013 | 255370 | – | PlayStation 4, PlayStation 3, PlayStation Vita, Xbox One, Wii U | Gold | Full controller support |
| 103 | Midnight Ramen | 2 GB | 2024 | 2543030 | – | – | Pending | Full controller support |
| 104 | Room of Depression | 2 GB | 2023 | 2056340 | – | – | Pending | Full controller support |
| 105 | Rune Break | 2 GB | 2023 | 2100040 | – | – | – | Full controller support |
| 106 | Euro Truck Simulator | 2 GB | 2008 | 232010 | – | – | Platinum | Partial controller support |
| 107 | Getting Over It with Bennett Foddy | 2 GB | 2017 | 240720 | – | – | Platinum | Partial controller support |
| 108 | Sven Co-op | 2 GB | 1999 | 225840 | – | – | Platinum | Partial controller support |
| 109 | Space Warlord Organ Trading Simulator | 2 GB | 2021 | 1507780 | – | Xbox One, Xbox Series X/S, Nintendo Switch | Platinum | Partial controller support |
| 110 | DeathSpank: Thongs of Virtue | 2 GB | 2010 | 18050 | – | – | Gold | Partial controller support |
| 111 | HOLE | 2 GB | 2024 | 2971610 | – | – | Gold | Partial controller support |
| 112 | DeathSpank | 2 GB | 2010 | 18040 | – | – | Silver | Partial controller support |
| 113 | Serious Sam Classics: Revolution | 2 GB | 2014 | 227780 | – | – | Silver | Partial controller support |
| 114 | FINAL FANTASY VII (2013) | 3 GB | 1997 | 39140 | DualShock only | PlayStation 4, PlayStation, Nintendo Switch | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 115 | INSIDE | 3 GB | 2016 | 304430 | – | PlayStation 4, Xbox One, Nintendo Switch | Platinum | Full controller support |
| 116 | Overcooked! 2 | 3 GB | 2018 | 728880 | – | PlayStation 4, Xbox One, Nintendo Switch, Nintendo Switch 2 | Platinum | Full controller support |
| 117 | The Jackbox Party Pack 6 | 3 GB | 2019 | 1005300 | – | PlayStation 4, Nintendo Switch | Platinum | Full controller support |
| 118 | State of Decay | 3 GB | 2013 | 241540 | – | Xbox One, Xbox 360 | Gold | Full controller support |
| 119 | The Jackbox Party Pack 5 | 3 GB | 2018 | 774461 | – | PlayStation 4, Xbox One, Nintendo Switch | Gold | Full controller support |
| 120 | UNO | 3 GB | 2006 | 470220 | – | PlayStation 4, PlayStation 3, Nintendo Switch, Wii | Silver | Full controller support |
| 121 | Trackmania | 3 GB | 2020 | 2225070 | – | – | Platinum | Partial controller support |
| 122 | Serious Sam II | 3 GB | 2005 | 204340 | – | Xbox | Platinum | Partial controller support |
| 123 | Kerbal Space Program | 3 GB | 2015 | 220200 | – | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S | Platinum | Partial controller support |
| 124 | Phoenix Wright: Ace Attorney Trilogy | 3 GB | 2012 | 787480 | – | PlayStation 4, Xbox One, Nintendo Switch, Nintendo 3DS | Platinum | Partial controller support |
| 125 | Nexuiz | 3 GB | 2012 | 96800 | – | – | Silver | Partial controller support |
| 126 | Sneaky Kitten | 3 GB | 2021 | 1408480 | – | – | – | Partial controller support |
| 127 | Giana Sisters: Twisted Dreams | 3.3 GB | 2012 | 223220 | – | PlayStation 4, PlayStation 3, Xbox One, Xbox 360, Nintendo Switch, Wii U | Silver | Full controller support |
| 128 | Awesomenauts | 3.5 GB | 2012 | 204300 | – | PlayStation 4, PlayStation 3, Xbox One, Xbox 360 | Platinum | Full controller support |
| 129 | Sanctum 2 | 4 GB | 2013 | 210770 | – | PlayStation 3 | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 130 | Cult of the Lamb | 4 GB | 2022 | 1313140 | DualShock only | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S, Nintendo Switch | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 131 | SUPERHOT | 4 GB | 2016 | 322500 | DualShock only | PlayStation 4, Xbox One, Nintendo Switch | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 132 | Firewatch | 4 GB | 2016 | 383870 | – | PlayStation 4, Xbox One, Nintendo Switch | Platinum | Full controller support |
| 133 | Spirit of the North | 4 GB | 2019 | 1213700 | – | PlayStation 4, Nintendo Switch | Platinum | Full controller support |
| 134 | The Escapists 2 | 4 GB | 2017 | 641990 | – | PlayStation 4, Xbox One, Nintendo Switch | Platinum | Full controller support |
| 135 | The Banner Saga 2 | 4 GB | 2016 | 281640 | – | Nintendo Switch | Gold | Full controller support |
| 136 | LEGOⓇ Indiana Jones™: The Original Adventures | 4 GB | 2008 | 32330 | – | PlayStation 3, PlayStation 2, PlayStation Portable, Xbox 360, Xbox, Wii, Nintendo DS | Gold | Full controller support |
| 137 | Serious Sam 3: BFE | 4 GB | 2011 | 41070 | – | PlayStation 3, Xbox 360 | Gold | Full controller support |
| 138 | The Banner Saga | 4 GB | 2014 | 237990 | – | PlayStation 4, Nintendo Switch | Gold | Full controller support |
| 139 | Ms. Splosion Man | 4 GB | 2011 | 105420 | – | Xbox 360, Nintendo Switch | Silver | Full controller support |
| 140 | Resident Evil 3 Nemesis (1999) | 4 GB | 1999 | 4249120 | Yes | PlayStation 3, PlayStation, GameCube, Dreamcast | Platinum | Partial controller support |
| 141 | Golf With Your Friends | 4 GB | 2016 | 431240 | – | PlayStation 4, Xbox One, Xbox Series X/S, Nintendo Switch | Platinum | Partial controller support |
| 142 | Hard Reset Extended Edition | 4 GB | 2011 | 98400 | – | PlayStation 4, Xbox One | Platinum | Partial controller support |
| 143 | Totally Accurate Battle Simulator | 4 GB | 2018 | 508440 | – | PlayStation 4, Nintendo Switch | Gold | Partial controller support |
| 144 | Resident Evil (1996) | 4 GB | 1996 | 4249100 | Yes | PlayStation, Nintendo DS, Sega Saturn | Silver | Partial controller support |
| 145 | Resident Evil 2 (1998) | 4 GB | 1998 | 4249110 | Yes | PlayStation, GameCube, Nintendo 64, Dreamcast | Silver | Partial controller support |
| 146 | F.E.A.R. 3 | 4.4 GB | 2011 | 21100 | – | PlayStation 3, Xbox 360 | Silver | Partial controller support |
| 147 | Tomb Raider I-III Remastered Starring Lara Croft | 5 GB | 2024 | 2478970 | Yes | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S, Nintendo Switch, Nintendo Switch 2 | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 148 | FINAL FANTASY VII | 5 GB | 1997 | 3837340 | DualShock only | PlayStation 4, PlayStation, Nintendo Switch | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 149 | Grand Theft Auto III - The Definitive Edition | 5 GB | 2021 | 1546970 | – | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S, Nintendo Switch | Platinum | Full controller support |
| 150 | Life is Strange™ | 5 GB | 2015 | 319630 | – | PlayStation 4, PlayStation 3, Xbox One, Xbox 360 | Platinum | Full controller support |
| 151 | OCTOPATH TRAVELER | 5 GB | 2018 | 921570 | – | PlayStation 4, PlayStation 5, Xbox One, Nintendo Switch, Nintendo Switch 2 | Platinum | Full controller support |
| 152 | Outlast | 5 GB | 2013 | 238320 | – | PlayStation 4, Xbox One | Platinum | Full controller support |
| 153 | The Stanley Parable: Ultra Deluxe | 5 GB | 2022 | 1703340 | – | PlayStation 4, Xbox One, Xbox Series X/S, Nintendo Switch | Platinum | Full controller support |
| 154 | Vox Machinae | 5 GB | 2022 | 334540 | – | – | Gold | Full controller support |
| 155 | The Assembly | 5 GB | 2016 | 373650 | – | PlayStation 4 | Pending | Full controller support |
| 156 | Blade Symphony | 5 GB | 2013 | 225600 | – | – | Gold | Partial controller support |
| 157 | Turbo Overkill | 5 GB | 2022 | 1328350 | Yes | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S, Nintendo Switch | Gold | Partial controller support |
| 158 | Anarchy Arcade | 5 GB | 2014 | 266430 | – | – | Bronze | Partial controller support |
| 159 | Risen 2: Dark Waters | 5.5 GB | 2012 | 40390 | – | PlayStation 3, Xbox 360 | Gold | Partial controller support |
| 160 | ASKA | 6 GB | 2024 | 1898300 | Yes | – | Gold | Full controller support |
| 161 | Minion Masters | 6 GB | 2019 | 489520 | – | – | Gold | Full controller support |
| 162 | Oddsparks: An Automation Adventure | 6 GB | 2024 | 1817800 | – | PlayStation 5, Xbox Series X/S | Gold | Full controller support |
| 163 | We Happy Few | 6 GB | 2018 | 320240 | – | PlayStation 4, Xbox One | Gold | Full controller support |
| 164 | Guts and Glory | 6 GB | 2018 | 537340 | – | Nintendo Switch | Platinum | Partial controller support |
| 165 | The Elder Scrolls V: Skyrim | 6 GB | 2011 | 72850 | – | PlayStation 4, PlayStation 5, PlayStation 3, Xbox One, Xbox Series X/S, Xbox 360, Nintendo Switch | Gold | Partial controller support |
| 166 | The Long Dark | 7 GB | 2017 | 305620 | Yes | PlayStation 4, PlayStation 5, Xbox One, Nintendo Switch | Gold | Full controller support |
| 167 | Lara Croft and the Guardian of Light | 7 GB | 2010 | 35130 | – | PlayStation 3, PlayStation Portable, Xbox 360 | Silver | Full controller support |
| 168 | Saints Row: Gat out of Hell | 7 GB | 2015 | 301910 | – | PlayStation 4, PlayStation 3, Xbox One, Xbox 360 | Silver | Full controller support |
| 169 | Cuisineer | 7 GB | 2023 | 1963570 | Yes | PlayStation 5, Xbox Series X/S, Nintendo Switch | Platinum | Partial controller support |
| 170 | HELLDIVERS™ Dive Harder Edition | 7 GB | 2015 | 394510 | DualShock only | PlayStation 4 | Platinum | Partial controller support |
| 171 | Unfortunate Spacemen | 7 GB | 2016 | 408900 | – | – | Gold | Partial controller support |
| 172 | Fallout 3 | 7 GB | 2008 | 22300 | – | PlayStation 3, Xbox One, Xbox 360 | Gold | Partial controller support |
| 173 | Red Faction®: Armageddon™ | 7.5 GB | 2011 | 55110 | – | PlayStation 3, Xbox 360 | Gold | Partial controller support |
| 174 | Coral Island | 8 GB | 2022 | 1158160 | Yes | PlayStation 5, Xbox Series X/S, Nintendo Switch 2 | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 175 | The Walking Dead: A New Frontier | 8 GB | 2016 | 536220 | – | PlayStation 4, Xbox One, Nintendo Switch | Platinum | Full controller support |
| 176 | S.T.A.L.K.E.R.: Clear Sky - Enhanced Edition | 8 GB | 2025 | 2427420 | Yes | – | Gold | Full controller support |
| 177 | Grounded | 8 GB | 2020 | 962130 | – | Xbox One, Xbox Series X/S | Gold | Full controller support |
| 178 | LEGO® Star Wars™ III: The Clone Wars™ | 8 GB | 2011 | 32510 | – | PlayStation 3, PlayStation Portable, Xbox 360, Wii, Nintendo 3DS, Nintendo DS | Gold | Full controller support |
| 179 | LEGO® The Lord of the Rings™ | 8 GB | 2012 | 214510 | – | PlayStation 3, PlayStation Vita, Xbox 360, Wii, Nintendo 3DS, Nintendo DS | Gold | Full controller support |
| 180 | Tomb Raider: Underworld | 8 GB | 2008 | 8140 | – | PlayStation 3, PlayStation 2, Xbox 360, Wii, Nintendo DS | Gold | Full controller support |
| 181 | Dead Rising | 8 GB | 2006 | 427190 | – | PlayStation 4, Xbox One, Xbox 360, Wii | Gold | Full controller support |
| 182 | Resident Evil Revelations | 8 GB | 2012 | 222480 | – | PlayStation 4, PlayStation 3, Xbox 360, Nintendo Switch, Wii U, Nintendo 3DS | Gold | Full controller support |
| 183 | The Banner Saga 3 | 8 GB | 2018 | 485460 | – | PlayStation 4, Nintendo Switch | Gold | Full controller support |
| 184 | Puppet Master: The Game | 8 GB | 2023 | 1757610 | – | – | Platinum | Partial controller support |
| 185 | Need For Speed: Hot Pursuit | 8 GB | 2010 | 47870 | – | PlayStation 3, Xbox 360, Wii | Platinum | Partial controller support |
| 186 | Chained Together | 8 GB | 2024 | 2567870 | – | – | Gold | Partial controller support |
| 187 | Assassin's Creed™: Director's Cut Edition | 8 GB | 2007 | 15100 | – | PlayStation 3, Xbox 360 | Gold | Partial controller support |
| 188 | Borderlands Game of the Year | 8 GB | 2009 | 8980 | – | PlayStation 3, Xbox 360 | Gold | Partial controller support |
| 189 | Mafia II (Classic) | 8 GB | 2010 | 50130 | – | PlayStation 3, Xbox 360 | Gold | Partial controller support |
| 190 | Assassin’s Creed® Brotherhood | 8 GB | 2010 | 48190 | – | PlayStation 4, PlayStation 3, Xbox 360 | Gold | Partial controller support |
| 191 | Alice: Madness Returns | 8.5 GB | 2011 | 19680 | – | PlayStation 3, Xbox 360 | Platinum | Partial controller support |
| 192 | Dead Rising 2: Off the Record | 8.5 GB | 2011 | 45770 | – | PlayStation 4, PlayStation 3, Xbox One, Xbox 360 | Gold | Partial controller support |
| 193 | Dead Rising® 2 | 8.5 GB | 2010 | 45740 | – | PlayStation 4, PlayStation 3, Xbox 360 | Gold | Partial controller support |
| 194 | XING: The Land Beyond | 9 GB | 2017 | 299400 | – | PlayStation 4 | Platinum | Full controller support |
| 195 | Codename CURE | 9 GB | 2017 | 355180 | – | – | Platinum | Partial controller support |
| 196 | Dishonored | 9 GB | 2012 | 205100 | – | PlayStation 4, PlayStation 3, Xbox One, Xbox 360 | Platinum | Partial controller support |
| 197 | Crysis 2 - Maximum Edition | 9 GB | 2011 | 108800 | – | PlayStation 3, Xbox 360 | Gold | Partial controller support |
| 198 | Divinity: Original Sin Enhanced Edition | 9.77 GB | 2015 | 373420 | – | PlayStation 4 | Platinum | Full controller support |
| 199 | Dead Island Definitive Edition | 10 GB | 2016 | 383150 | – | PlayStation 4, Xbox One | Platinum | Full controller support |
| 200 | Dead Island Riptide Definitive Edition | 10 GB | 2016 | 383180 | – | PlayStation 4, Xbox One | Platinum | Full controller support |
| 201 | LEGO® Jurassic World | 10 GB | 2015 | 352400 | – | PlayStation 4, PlayStation 3, PlayStation Vita, Xbox One, Xbox 360, Nintendo Switch, Wii U, Nintendo 3DS | Platinum | Full controller support |
| 202 | LEGO® The Hobbit™ | 10 GB | 2014 | 285160 | – | PlayStation 4, PlayStation 3, PlayStation Vita, Xbox One, Xbox 360, Wii U, Nintendo 3DS | Platinum | Full controller support |
| 203 | PAC-MAN WORLD Re-PAC | 10 GB | 2022 | 1859470 | – | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S | Platinum | Full controller support |
| 204 | S.T.A.L.K.E.R.: Call of Prypiat - Enhanced Edition | 10 GB | 2025 | 2427430 | Yes | – | Gold | Full controller support |
| 205 | Serious Sam Fusion 2017 (beta) | 10 GB | 2017 | 564310 | – | – | Gold | Full controller support |
| 206 | LEGO® Batman™ 2: DC Super Heroes | 10 GB | 2012 | 213330 | – | PlayStation 3, PlayStation Vita, PlayStation Portable, Xbox 360, Wii U, Wii, Nintendo DS | Gold | Full controller support |
| 207 | LEGO® Batman™ 3: Beyond Gotham | 10 GB | 2014 | 313690 | – | PlayStation 4, PlayStation 3, PlayStation Vita, Xbox One, Xbox 360, Wii U, Nintendo 3DS | Gold | Full controller support |
| 208 | Saints Row IV | 10 GB | 2013 | 206420 | – | PlayStation 4, PlayStation 5, PlayStation 3, Xbox One, Xbox 360, Nintendo Switch | Gold | Full controller support |
| 209 | Duke Nukem Forever | 10 GB | 2011 | 57900 | – | PlayStation 3, Xbox 360 | Silver | Full controller support |
| 210 | Dead Space™ 2 | 10 GB | 2011 | 47780 | – | PlayStation 3, Xbox 360 | Platinum | Partial controller support |
| 211 | DEEMO -Reborn- | 10 GB | 2020 | 1282210 | – | PlayStation 4 | Platinum | Partial controller support |
| 212 | System Shock | 10 GB | 2023 | 482400 | – | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S | Platinum | Partial controller support |
| 213 | REKA | 10 GB | 2024 | 1737870 | Yes | – | Gold | Partial controller support |
| 214 | ARMA 2 | 10 GB | 2009 | 33910 | – | – | Silver | Partial controller support |
| 215 | Contagion | 10 GB | 2013 | 238430 | – | – | Silver | Partial controller support |
| 216 | Tom Clancy's Splinter Cell Conviction™ | 10 GB | 2010 | 33220 | – | Xbox One, Xbox 360 | Silver | Partial controller support |
| 217 | Homefront | 10 GB | 2011 | 55100 | – | PlayStation 3, Xbox 360 | Silver | Partial controller support |
| 218 | DOOM 3 | 11 GB | 2012 | 208200 | – | PlayStation 3, Xbox 360 | Gold | Partial controller support |
| 219 | MURDERED: SOUL SUSPECT™ | 12 GB | 2014 | 233290 | – | PlayStation 4, PlayStation 3, Xbox One, Xbox 360 | Platinum | Full controller support |
| 220 | Superliminal | 12 GB | 2019 | 1049410 | – | PlayStation 4, Xbox One, Nintendo Switch | Platinum | Full controller support |
| 221 | Exo One: Prologue | 12 GB | 2020 | 1375530 | – | – | Bronze | Full controller support |
| 222 | Atari 50: The Anniversary Celebration | 12 GB | 2022 | 1919470 | – | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S, Nintendo Switch | Platinum | Partial controller support |
| 223 | Rocksmith® 2014 Edition REMASTERED LEARN & PLAY | 12 GB | 2013 | 221680 | – | PlayStation 4, PlayStation 3, Xbox One, Xbox 360 | Gold | Partial controller support |
| 224 | Borderlands 2 | 13 GB | 2012 | 49520 | – | PlayStation 4, PlayStation 3, PlayStation Vita, Xbox 360 | Platinum | Full controller support |
| 225 | Borderlands: The Pre-Sequel | 13 GB | 2014 | 261640 | – | PlayStation 4, PlayStation 3, Xbox One, Xbox 360 | Gold | Full controller support |
| 226 | Resident Evil 0 | 13 GB | 2002 | 339340 | – | PlayStation 4, PlayStation 3, Xbox One, Xbox 360, Nintendo Switch, Wii, GameCube | Gold | Full controller support |
| 227 | LEGO® MARVEL's Avengers | 14 GB | 2015 | 405310 | – | PlayStation 4, PlayStation 3, PlayStation Vita, Xbox One, Xbox 360, Wii U, Nintendo 3DS | Platinum | Full controller support |
| 228 | LEGO® STAR WARS™: The Force Awakens | 14 GB | 2016 | 438640 | – | PlayStation 4, PlayStation 3, PlayStation Vita, Xbox One, Xbox 360, Wii U, Nintendo 3DS | Gold | Full controller support |
| 229 | Red Faction: Guerrilla Steam Edition | 15 GB | 2009 | 20500 | – | PlayStation 3, Xbox 360 | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 230 | Wanderstop | 15 GB | 2025 | 1299460 | Yes | PlayStation 5, Xbox Series X/S, Nintendo Switch, Nintendo Switch 2 | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 231 | MXGP 2020 - The Official Motocross Videogame | 15 GB | 2020 | 1259800 | – | PlayStation 4, PlayStation 5 | Platinum | Full controller support |
| 232 | Sniper Elite V2 Remastered | 15 GB | 2019 | 728740 | – | PlayStation 4, Xbox One, Nintendo Switch | Platinum | Full controller support |
| 233 | The Walking Dead: The Final Season | 15 GB | 2018 | 866800 | – | PlayStation 4, Xbox One, Nintendo Switch | Platinum | Full controller support |
| 234 | LocoCycle | 15 GB | 2013 | 224040 | – | Xbox One, Xbox 360 | Gold | Full controller support |
| 235 | No Man's Sky | 15 GB | 2016 | 275850 | Yes | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S, Nintendo Switch, Nintendo Switch 2 | Gold | Full controller support |
| 236 | Gravel | 15 GB | 2018 | 558260 | – | PlayStation 4, Xbox One | Gold | Full controller support |
| 237 | POSTAL: Brain Damaged | 15 GB | 2022 | 1359980 | – | PlayStation 4, PlayStation 5 | Gold | Full controller support |
| 238 | GRID 2 | 15 GB | 2013 | 44350 | – | PlayStation 3, Xbox 360 | Silver | Full controller support |
| 239 | GTFO | 15 GB | 2021 | 493520 | – | – | Gold | Partial controller support |
| 240 | The Last Remnant™ | 15 GB | 2008 | 23310 | – | Xbox 360 | Gold | Partial controller support |
| 241 | Far Cry 3 | 15 GB | 2012 | 220240 | – | PlayStation 3, Xbox 360 | Gold | Partial controller support |
| 242 | Assetto Corsa | 15 GB | 2013 | 244210 | – | PlayStation 4 | Gold | Partial controller support |
| 243 | LEGO® MARVEL Super Heroes 2 | 16 GB | 2017 | 647830 | – | PlayStation 4, Xbox One, Nintendo Switch | Platinum | Full controller support |
| 244 | L.A. Noire | 16 GB | 2011 | 110800 | – | PlayStation 4, PlayStation 3, Xbox One, Xbox 360, Nintendo Switch | Gold | Partial controller support |
| 245 | Resident Evil 6 | 16 GB | 2012 | 221040 | – | PlayStation 4, PlayStation 3, Xbox One, Xbox 360, Nintendo Switch | Gold | Partial controller support |
| 246 | METAL GEAR SOLID 2: Sons of Liberty - Master Collection Version | 17 GB | 2023 | 2131640 | DualShock only | – | Gold | Full controller support |
| 247 | Deus Ex: Human Revolution - Director's Cut | 17 GB | 2013 | 238010 | Yes | Wii U | Gold | Full controller support |
| 248 | Assassin’s Creed® III | 17 GB | 2012 | 208480 | – | PlayStation 4, PlayStation 3, Xbox One, Xbox 360, Nintendo Switch, Wii U | Gold | Partial controller support |
| 249 | LEGO® City Undercover | 18 GB | 2013 | 578330 | – | PlayStation 4, Xbox One, Nintendo Switch, Wii U | Gold | Full controller support |
| 250 | Grand Theft Auto: San Andreas - The Definitive Edition | 19 GB | 2021 | 1547000 | – | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S, Nintendo Switch | Gold | Full controller support |
| 251 | Prey | 20 GB | 2017 | 480490 | – | PlayStation 4, Xbox One, Xbox 360 | Platinum | Full controller support |
| 252 | Disco Elysium | 20 GB | 2019 | 632470 | Yes | Nintendo Switch | Gold | Full controller support |
| 253 | Battlefield 3™ | 20 GB | 2011 | 1238820 | – | PlayStation 3, Xbox 360 | Gold | Full controller support |
| 254 | XCOM: Enemy Unknown | 20 GB | 2012 | 200510 | – | PlayStation 3, Xbox 360 | Gold | Full controller support |
| 255 | Thief | 20 GB | 2014 | 239160 | Yes | PlayStation 4, PlayStation 3, Xbox One, Xbox 360 | Gold | Full controller support |
| 256 | BioShock Infinite | 20 GB | 2013 | 8870 | – | PlayStation 4, PlayStation 3, Xbox One, Xbox 360, Nintendo Switch | Gold | Full controller support |
| 257 | Sleeping Dogs: Definitive Edition | 20 GB | 2014 | 307690 | – | PlayStation 4, Xbox One | Gold | Full controller support |
| 258 | Arma: Cold War Assault Remastered | 20 GB | 2001 | 65790 | Yes | Xbox | Silver | Full controller support |
| 259 | Monster Energy Supercross - The Official Videogame 6 | 20 GB | 2023 | 2058750 | Yes | PlayStation 5, Xbox One, Xbox Series X/S | Pending | Full controller support |
| 260 | Car Mechanic Simulator 2018 | 20 GB | 2017 | 645630 | – | PlayStation 4, Nintendo Switch | Gold | Partial controller support |
| 261 | Obduction | 20 GB | 2016 | 306760 | – | PlayStation 4, Xbox One | Gold | Partial controller support |
| 262 | South Park™: The Fractured But Whole™ | 20 GB | 2017 | 488790 | – | PlayStation 4, Xbox One, Nintendo Switch | Gold | Partial controller support |
| 263 | Injustice: Gods Among Us Ultimate Edition | 21 GB | 2013 | 242700 | – | PlayStation 4, PlayStation 3, PlayStation Vita, Xbox 360, Wii U | Gold | Full controller support |
| 264 | Ghostrunner | 22 GB | 2020 | 1139900 | – | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S, Nintendo Switch | Gold | Partial controller support |
| 265 | Resident Evil Revelations 2 | 23 GB | 2015 | 287290 | – | PlayStation 4, PlayStation Vita, Xbox One, Nintendo Switch | Gold | Full controller support |
| 266 | Resident Evil 7 Biohazard | 24 GB | 2017 | 418370 | – | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S, Nintendo Switch, Nintendo Switch 2 | Gold | Full controller support |
| 267 | Hitman: Absolution™ | 24 GB | 2012 | 203140 | – | PlayStation 4, PlayStation 3, Xbox One, Xbox 360, Nintendo Switch | Gold | Partial controller support |
| 268 | Rise of the Tomb Raider | 25 GB | 2015 | 391220 | DualShock only | PlayStation 4, Xbox One, Xbox 360 | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 269 | BioShock 2 Remastered | 25 GB | 2016 | 409720 | – | PlayStation 4, Nintendo Switch | Gold | Full controller support |
| 270 | POSTAL 4: No Regerts | 25 GB | 2022 | 707030 | – | PlayStation 4 | Gold | Full controller support |
| 271 | Saints Row The Third Remastered | 25 GB | 2020 | 978300 | – | PlayStation 4, PlayStation 5, Xbox One | Gold | Full controller support |
| 272 | The Witcher 2: Assassins of Kings Enhanced Edition | 25 GB | 2011 | 20920 | – | Xbox One, Xbox 360 | Gold | Partial controller support |
| 273 | Borderlands Game of the Year Enhanced | 25 GB | 2019 | 729040 | – | PlayStation 4, Xbox One | Gold | Partial controller support |
| 274 | Elite Dangerous | 25 GB | 2014 | 359320 | – | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S | Gold | Partial controller support |
| 275 | Watch_Dogs™ | 25 GB | 2014 | 243470 | – | PlayStation 4, PlayStation 3, Xbox One, Xbox 360, Wii U | Gold | Partial controller support |
| 276 | The Bard's Tale IV: Director's Cut | 29 GB | 2019 | 1091980 | – | – | Gold | Partial controller support |
| 277 | Nobody Wants to Die | 30 GB | 2024 | 1939970 | – | PlayStation 5, Xbox Series X/S | Platinum | Full controller support |
| 278 | Outlast 2 | 30 GB | 2017 | 414700 | – | PlayStation 4, Xbox One, Nintendo Switch | Platinum | Full controller support |
| 279 | Battlefield 4™ | 30 GB | 2013 | 1238860 | – | PlayStation 4, PlayStation 3, Xbox One, Xbox 360 | Gold | Full controller support |
| 280 | Dead Rising 3 | 30 GB | 2013 | 265550 | – | Xbox One | Silver | Full controller support |
| 281 | Sébastien Loeb Rally EVO | 30 GB | 2016 | 355060 | – | PlayStation 4, Xbox One | Platinum | Partial controller support |
| 282 | Far Cry® 4 | 30 GB | 2014 | 298110 | – | PlayStation 4, PlayStation 3, Xbox One, Xbox 360 | Gold | Partial controller support |
| 283 | Far Cry® New Dawn | 30 GB | 2019 | 939960 | – | PlayStation 4, Xbox One | Gold | Partial controller support |
| 284 | Microsoft Flight Simulator X: Steam Edition | 30 GB | 2006 | 314160 | – | – | Silver | Partial controller support |
| 285 | PAYDAY 2 | 32 GB | 2013 | 218620 | DualShock only | PlayStation 4, PlayStation 3, Xbox One, Xbox 360, Nintendo Switch | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 286 | Red Faction Guerrilla Re-Mars-tered | 32 GB | 2018 | 667720 | – | PlayStation 4, Xbox One, Nintendo Switch | Gold | Full controller support |
| 287 | Trepang2 | 35 GB | 2023 | 1164940 | Yes | PlayStation 5, Xbox Series X/S | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 288 | X4: Foundations | 35 GB | 2018 | 392160 | Yes | – | Gold | Full controller support |
| 289 | KINGDOM HEARTS HD 2.8 Final Chapter Prologue | 35 GB | 2017 | 2552440 | Yes | PlayStation 4 | Gold | Full controller support |
| 290 | Heavy Rain | 35 GB | 2010 | 960910 | – | PlayStation 4, PlayStation 3 | Gold | Full controller support |
| 291 | Space Engineers | 35 GB | 2019 | 244850 | – | PlayStation 4, Xbox One | Gold | Partial controller support |
| 292 | Mortal Kombat X | 36 GB | 2015 | 307780 | – | PlayStation 4, Xbox One | Gold | Full controller support |
| 293 | Wolfenstein: The Old Blood | 38 GB | 2015 | 350080 | – | PlayStation 4, Xbox One | Platinum | Partial controller support |
| 294 | LEGO® Star Wars™: The Skywalker Saga | 40 GB | 2022 | 920210 | – | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S, Nintendo Switch | Platinum | Full controller support |
| 295 | Shadow of the Tomb Raider | 40 GB | 2018 | 750920 | Yes | PlayStation 4, Xbox One | Gold | Full controller support |
| 296 | STAR WARS™ Battlefront™ | 40 GB | 2015 | 1237980 | – | PlayStation 4, Xbox One | Gold | Full controller support |
| 297 | The Outer Worlds | 40 GB | 2019 | 578650 | – | PlayStation 4, Xbox One, Nintendo Switch | Gold | Full controller support |
| 298 | Tom Clancy's The Division | 40 GB | 2016 | 365590 | – | PlayStation 4, Xbox One | Gold | Full controller support |
| 299 | Wolfenstein: Youngblood | 40 GB | 2019 | 1056960 | – | PlayStation 4, Xbox One, Nintendo Switch | Gold | Partial controller support |
| 300 | Control Ultimate Edition | 42 GB | 2019 | 870780 | – | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S, Nintendo Switch | Platinum | Full controller support |
| 301 | RIDE 4 | 43 GB | 2020 | 1259980 | – | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S | Platinum | Full controller support |
| 302 | Middle-earth™: Shadow of Mordor™ | 44 GB | 2014 | 241930 | – | PlayStation 4, PlayStation 3, Xbox One, Xbox 360 | Platinum | Full controller support |
| 303 | The Walking Dead: The Telltale Definitive Series | 45 GB | 2019 | 1449690 | – | PlayStation 4, Xbox One, Nintendo Switch | Platinum | Full controller support |
| 304 | Deus Ex: Mankind Divided™ | 45 GB | 2016 | 337000 | Yes | PlayStation 4, Xbox One | Gold | Full controller support |
| 305 | Titanfall® 2 | 45 GB | 2016 | 1237970 | – | PlayStation 4, Xbox One | Gold | Full controller support |
| 306 | Beyond: Two Souls | 49 GB | 2013 | 960990 | – | PlayStation 4, PlayStation 3 | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 307 | Scorn | 50 GB | 2022 | 698670 | – | PlayStation 5, Xbox Series X/S | Platinum | Full controller support |
| 308 | It Takes Two | 50 GB | 2021 | 1426210 | Yes | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S, Nintendo Switch, Nintendo Switch 2 | Gold | Full controller support |
| 309 | Mafia II: Definitive Edition | 50 GB | 2020 | 1030830 | – | PlayStation 4, Xbox One | Gold | Full controller support |
| 310 | Mafia III: Definitive Edition | 50 GB | 2016 | 360430 | – | PlayStation 4, Xbox One | Gold | Full controller support |
| 311 | Mafia: Definitive Edition | 50 GB | 2020 | 1030840 | – | PlayStation 4, Xbox One | Gold | Full controller support |
| 312 | Wolfenstein: The New Order | 50 GB | 2014 | 201810 | – | PlayStation 4, PlayStation 3, Xbox One, Xbox 360 | Platinum | Partial controller support |
| 313 | Tom Clancy's Ghost Recon® Wildlands | 50 GB | 2017 | 460930 | – | PlayStation 4, Xbox One | Gold | Partial controller support |
| 314 | Injustice™ 2 | 52 GB | 2017 | 627270 | – | PlayStation 4, Xbox One | Gold | Full controller support |
| 315 | Just Cause 3 | 54 GB | 2015 | 225540 | – | PlayStation 4, Xbox One | Gold | Full controller support |
| 316 | Wolfenstein II: The New Colossus | 55 GB | 2017 | 612880 | – | PlayStation 4, Xbox One, Nintendo Switch | Platinum | Full controller support |
| 317 | STAR WARS Jedi: Fallen Order™ | 55 GB | 2019 | 1172380 | Yes | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S | Gold | Full controller support |
| 318 | Detroit: Become Human | 55 GB | 2018 | 1222140 | – | PlayStation 4 | Gold | Full controller support |
| 319 | Mass Effect™: Andromeda Deluxe Edition | 55 GB | 2017 | 1238000 | – | PlayStation 4, Xbox One | Gold | Full controller support |
| 320 | DOOM | 55 GB | 2016 | 379720 | – | PlayStation 4, Xbox One, Nintendo Switch | Platinum | Partial controller support |
| 321 | Metro Exodus | 59 GB | 2019 | 412020 | – | PlayStation 4, PlayStation 5, Xbox One | Gold | Full controller support |
| 322 | Metro Exodus Enhanced Edition | 59 GB | 2020 | 1449560 | – | – | Silver | Full controller support |
| 323 | South of Midnight | 60 GB | 2025 | 1934570 | – | PlayStation 5, Xbox Series X/S, Nintendo Switch 2 | Platinum | Full controller support |
| 324 | Enshrouded | 60 GB | 2024 | 1203620 | Yes | PlayStation 5, Xbox Series X/S | Gold | Full controller support |
| 325 | HITMAN World of Assassination | 60 GB | 2021 | 1659040 | Yes | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S, Nintendo Switch, Nintendo Switch 2 | Gold | Full controller support |
| 326 | Battlefield™ Hardline | 60 GB | 2015 | 1238880 | – | PlayStation 4, PlayStation 3, Xbox One, Xbox 360 | Silver | Full controller support |
| 327 | The Outer Worlds: Spacer's Choice Edition | 62 GB | 2023 | 1920490 | – | PlayStation 5, Xbox Series X/S | Gold | Full controller support |
| 328 | God of War | 70 GB | 2018 | 1593500 | Yes | PlayStation 4, PlayStation 5 | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 329 | Call of Duty: Infinite Warfare | 70 GB | 2016 | 292730 | – | PlayStation 4, Xbox One | Gold | Full controller support |
| 330 | Middle-earth™: Shadow of War™ | 70 GB | 2017 | 356190 | – | PlayStation 4, Xbox One | Gold | Full controller support |
| 331 | KINGDOM HEARTS III + Re Mind (DLC) | 75 GB | 2019 | 2552450 | Yes | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S, Nintendo Switch, Nintendo Switch 2 | Gold | Full controller support |
| 332 | Avowed | 75 GB | 2025 | 2457220 | – | PlayStation 5, Xbox Series X/S | Gold | Full controller support |
| 333 | Borderlands 3 | 75 GB | 2019 | 397540 | – | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S | Gold | Full controller support |
| 334 | F1 2020 | 80 GB | 2020 | 1080110 | – | PlayStation 4, Xbox One | Gold | Full controller support |
| 335 | Killing Floor 2 | 80 GB | 2016 | 232090 | – | PlayStation 4, Xbox One | Gold | Full controller support |
| 336 | MechWarrior 5: Mercenaries | 80 GB | 2019 | 784080 | – | PlayStation 4, PlayStation 5 | Platinum | Partial controller support |
| 337 | Mass Effect™ Legendary Edition | 120 GB | 2021 | 1328670 | – | PlayStation 4, Xbox One | Gold | Full controller support |
| 338 | UNCHARTED™: Legacy of Thieves Collection | 126 GB | 2022 | 1659420 | Yes | PlayStation 5 | Gold | Full controller support |
| 339 | Baldur's Gate 3 | 150 GB | 2023 | 1086940 | Yes | PlayStation 5, Xbox Series X/S | Gold | Full controller support |
| 340 | Red Dead Redemption 2 | 150 GB | 2018 | 1174180 | – | PlayStation 4, Xbox One | Gold | Partial controller support |
| 341 | DCS World Steam Edition | 200 GB | 2008 | 223750 | – | – | Gold | Partial controller support |
| 342 | Tomb Raider: Anniversary | – | 2007 | 8000 | – | PlayStation 3, PlayStation 2, PlayStation Portable, Xbox 360, Wii | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 343 | Tomb Raider IV-VI Remastered | – | 2025 | 2525380 | Yes | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S, Nintendo Switch | Platinum | Full controller support; retest: search broken by the tester (Library filter); retest |
| 344 | Metro 2033 | – | 2010 | 43110 | – | PlayStation 4, Xbox One, Xbox 360 | Platinum | Full controller support |
| 345 | PAC-MAN MUSEUM+ | – | 2022 | 1665130 | – | PlayStation 4, Xbox One, Xbox Series X/S, Nintendo Switch | Platinum | Full controller support |
| 346 | Quake | – | 1996 | 2310 | – | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S, Nintendo Switch, Nintendo 64, Dreamcast, Sega Saturn | Platinum | Full controller support |
| 347 | Tomb Raider: Legend | – | 2006 | 7000 | – | PlayStation 4, PlayStation 5, PlayStation 3, PlayStation 2, PlayStation Portable, Xbox 360, Xbox, GameCube | Platinum | Full controller support |
| 348 | Audiosurf | – | 2008 | 12900 | – | – | Gold | Full controller support |
| 349 | No Time To Explain Remastered | – | 2015 | 368730 | – | – | Gold | Full controller support |
| 350 | Team Indie | – | 2014 | 302850 | – | – | Gold | Full controller support |
| 351 | DOOM II | – | 1994 | 2300 | – | PlayStation 3, Xbox 360, Nintendo Switch, Game Boy Advance | Gold | Full controller support |
| 352 | Quake II | – | 1997 | 2320 | – | PlayStation, Xbox 360, Nintendo Switch, Nintendo 64, Dreamcast | Gold | Full controller support |
| 353 | SUPERHOT: MIND CONTROL DELETE | – | 2020 | 690040 | DualShock only | PlayStation 4 | Gold | Full controller support |
| 354 | Mortal Kombat 11 | – | 2019 | 976310 | – | PlayStation 4, PlayStation 5, Xbox One, Xbox Series X/S, Nintendo Switch | Gold | Full controller support |
| 355 | Worms W.M.D | – | 2016 | 327030 | – | PlayStation 4, Xbox One, Nintendo Switch | Gold | Full controller support |
| 356 | Cthulhu Saves the World | – | 2010 | 107310 | – | Xbox 360 | Silver | Full controller support |
| 357 | Call of Duty®: Modern Warfare® III | – | 2023 | 3595270 | – | – | Bronze | Full controller support |
| 358 | Xploquest 3 | – | 2023 | 2267770 | – | – | – | Full controller support |
| 359 | Prey: Typhon Hunter | – | 2018 | 741820 | – | – | Gold | Partial controller support |
| 360 | GWENT: The Witcher Card Game | – | 2018 | 1284410 | – | PlayStation 4, Xbox One | Gold | Partial controller support |
| 361 | This War of Mine | – | 2014 | 282070 | – | PlayStation 4 | Gold | Partial controller support |
| 362 | Serious Sam HD: The First Encounter | – | 2009 | 41000 | – | – | Silver | Partial controller support |
| 363 | Planet Stronghold | – | 2011 | 291050 | – | – | – | Partial controller support |
